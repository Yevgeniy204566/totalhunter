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
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def update_json(path: str, updates: dict, remove_keys=()) -> dict:
    """Слить updates в существующий файл (остальные ключи не трогать) и записать атомарно."""
    data = read_json(path)
    data.update(updates)
    for k in remove_keys:
        data.pop(k, None)
    atomic_write_json(path, data)
    return data
