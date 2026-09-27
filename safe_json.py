"""
safe_json.py — запись настроек игрока без риска их потерять (владелец 2026-09-27).

Калибровка (точки, масштаб, тюнинг) и настройки склепов/бирж настраиваются часами —
они не имеют права пропасть ни от сбоя, ни от обновления, ни от частичного сохранения.

- atomic_write_json: пишет во временный файл рядом и подменяет os.replace — обрыв
  посреди записи (краш, выключение ПК) оставляет СТАРЫЙ файл целым, а не пустым.
- update_json: меняет только переданные ключи, остальные ключи файла сохраняет —
  сохранение калибровки не стирает настройки склепов/бирж в том же профиле и наоборот.
"""
import json
import os
import tempfile


def read_json_strict(path: str) -> dict:
    """Читает JSON-объект: UTF-8, затем cp1251 (файлы, записанные v2.1.1). Нечитаемый или
    не-объект — исключение: вызывающий НЕ должен после этого перезаписывать файл."""
    with open(path, "rb") as f:
        raw = f.read()
    last_err = None
    for enc in ("utf-8", "cp1251"):
        try:
            data = json.loads(raw.decode(enc))
        except (UnicodeDecodeError, ValueError) as e:
            last_err = e
            continue
        if isinstance(data, dict):
            return data
        raise ValueError(f"{path}: ожидался JSON-объект")
    raise ValueError(f"{path}: не читается как JSON ({last_err})")


def read_json(path: str) -> dict:
    """Мягкое чтение: при любой ошибке — {} (для слияния в профиле калибровки)."""
    try:
        return read_json_strict(path)
    except Exception:
        return {}


def atomic_write_json(path: str, data: dict) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            # ensure_ascii=True — прежний формат файлов (кириллица кодами \uXXXX). С False
            # в v2.1.1 кириллица писалась UTF-8, а часть мест читает файл без encoding
            # (cp1251) — каждый круг чтение/запись портил название клана «Феникс».
            json.dump(data, f, indent=2, ensure_ascii=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# Символы, которые появляются ТОЛЬКО как мусор при прочтении UTF-8 в cp1251 и не бывают
# в нормальных названиях: латиница-1 (NBSP, ¤, «, °…), типографика (…, †, ‰, ‘ ’…) и
# редкие сербско-македонские буквы Ђ Ѓ Ѕ Ј Љ Њ Ћ Ќ Џ (украинские Є І Ї Ґ разрешены).
_MOJIBAKE_MARKERS = set(
    [chr(c) for c in range(0x80, 0xC0)] +
    [chr(c) for c in range(0x2010, 0x2040)] + ["™", "№"] +
    [chr(c) for c in (0x402, 0x403, 0x405, 0x408, 0x409, 0x40A, 0x40B, 0x40C, 0x40E, 0x40F,
                      0x452, 0x453, 0x455, 0x458, 0x459, 0x45A, 0x45B, 0x45C, 0x45E, 0x45F)]
)


def _looks_clean(text: str) -> bool:
    """Нормальное название: есть обычные кириллические буквы А-я и нет мусорных символов."""
    return (any("А" <= ch <= "я" for ch in text)
            and not any(ch in _MOJIBAKE_MARKERS for ch in text))


def repair_mojibake(text: str) -> str:
    """Откатывает порчу «UTF-8 прочитан как cp1251» любой глубины:
    'Р¤РµРЅРёРєСЃ' → 'Феникс'. Результат принимается, ТОЛЬКО если исходник выглядит как
    мусор, а итог — как нормальное название; иначе строка возвращается как есть
    (короткие нормальные слова вроде «Лі» случайно декодируются — их трогать нельзя)."""
    if _looks_clean(text) or text.isascii():
        return text
    candidate = text
    for _ in range(6):
        try:
            nxt = candidate.encode("cp1251").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if nxt == candidate:
            break
        candidate = nxt
        if _looks_clean(candidate):
            return candidate
    return text


def _repair_tree(value):
    if isinstance(value, str):
        return repair_mojibake(value)
    if isinstance(value, list):
        return [_repair_tree(v) for v in value]
    if isinstance(value, dict):
        return {k: _repair_tree(v) for k, v in value.items()}
    return value


def repair_file(path: str) -> bool:
    """Чинит испорченные v2.1.1 строки в JSON-файле настроек и переписывает его в
    прежнем ASCII-формате. Читает как UTF-8, при ошибке — как cp1251. True — чинил."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return False
    for enc in ("utf-8", "cp1251"):
        try:
            data = json.loads(raw.decode(enc))
            break
        except (UnicodeDecodeError, ValueError):
            data = None
    if not isinstance(data, dict):
        return False
    fixed = _repair_tree(data)
    if fixed == data and raw.isascii():
        return False
    atomic_write_json(path, fixed)
    return True


def update_json(path: str, updates: dict, remove_keys=()) -> dict:
    """Слить updates в существующий файл (остальные ключи не трогать) и записать атомарно."""
    data = read_json(path)
    data.update(updates)
    for k in remove_keys:
        data.pop(k, None)
    atomic_write_json(path, data)
    return data
