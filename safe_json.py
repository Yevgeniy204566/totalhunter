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


def read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def atomic_write_json(path: str, data: dict) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            # ensure_ascii=True — прежний формат файлов (кириллица как Ф…). С False
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


def repair_mojibake(text: str) -> str:
    """Откатывает порчу «UTF-8 прочитан как cp1251» (сколько бы кругов ни было):
    'Р¤РµРЅРёРєСЃ' → 'Феникс'. Нормальный текст не трогает: его cp1251-байты не
    являются валидным UTF-8, и цикл сразу останавливается."""
    for _ in range(6):
        try:
            fixed = text.encode("cp1251").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if fixed == text:
            break
        text = fixed
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
