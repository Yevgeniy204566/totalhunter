"""
TDD: сундуки уходят в клан, под которым их СОБРАЛИ (владелец 2026-09-26). Раньше пара
бралась из полей ввода в момент отправки — переключение пары посреди сбора уводило весь
батч в новый клан.
"""
from unittest.mock import MagicMock

import chest_reader as cr
import main as _main_module

App = _main_module.TotalHunterApp


def _setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    real_init = cr.init_db
    monkeypatch.setattr(cr, "init_db", lambda path=db_path: real_init(path))
    return db_path


def test_each_pair_goes_to_its_own_clan(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    conn = cr.init_db()
    cr.insert_chest(conn, "Т", "A", "t1", "229", "ELDORADO")
    cr.insert_chest(conn, "Т", "B", "t2", "229", "Феникс")
    cr.insert_chest(conn, "Т", "C", "t3", "229", "ELDORADO")
    conn.close()
    calls = []
    monkeypatch.setattr(cr, "export_to_api",
                        lambda k, c, items: calls.append((k, c, [i["sender"] for i in items]))
                        or {"success": True, "count": len(items)})

    result = App._send_chest_batch(MagicMock(), "229", "Феникс")

    assert result["success"] is True
    assert sorted(calls) == [("229", "ELDORADO", ["A", "C"]), ("229", "Феникс", ["B"])]
    conn = cr.init_db()
    assert cr.get_unsynced(conn) == []
    conn.close()


def test_failed_pair_keeps_its_rows_sent_pair_is_deleted(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    conn = cr.init_db()
    cr.insert_chest(conn, "Т", "A", "t1", "229", "ELDORADO")
    cr.insert_chest(conn, "Т", "B", "t2", "229", "Феникс")
    conn.close()

    def fake_export(k, c, items):
        if c == "Феникс":
            return {"success": False, "reason": "net"}
        return {"success": True, "count": len(items)}
    monkeypatch.setattr(cr, "export_to_api", fake_export)

    result = App._send_chest_batch(MagicMock(), "229", "ELDORADO")

    assert result["success"] is False
    conn = cr.init_db()
    assert [r[1] for r in cr.get_unsynced(conn)] == ["B"]
    conn.close()


def test_old_rows_without_pair_use_fields_and_need_them(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    conn = cr.init_db()
    cr.insert_chest(conn, "Т", "Old", "t1")
    conn.close()
    calls = []
    monkeypatch.setattr(cr, "export_to_api",
                        lambda k, c, items: calls.append((k, c)) or {"success": True, "count": 1})

    missing = App._send_chest_batch(MagicMock(), "", "")
    assert missing.get("missing_fields") is True
    assert calls == []

    ok = App._send_chest_batch(MagicMock(), "229", "ELDORADO")
    assert ok["success"] is True
    assert calls == [("229", "ELDORADO")]


def test_empty_queue_is_empty_success(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    assert App._send_chest_batch(MagicMock(), "229", "X") == {"success": True, "empty": True}
