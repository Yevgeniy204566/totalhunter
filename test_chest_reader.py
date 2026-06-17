import os
import cv2
import numpy as np
import chest_reader as cr


def _load_fixture():
    return cv2.imdecode(np.fromfile("Сундуки_1.png", dtype=np.uint8), cv2.IMREAD_COLOR)


def test_detect_dialog_bbox():
    frame = _load_fixture()
    bbox = cr.detect_dialog_bbox(frame)
    assert bbox == (671, 340, 764, 475)


def test_detect_dialog_bbox_returns_none_when_no_match():
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    assert cr.detect_dialog_bbox(blank) is None


def test_crop_dialog():
    frame = _load_fixture()
    bbox = cr.detect_dialog_bbox(frame)
    dialog = cr.crop_dialog(frame, bbox)
    assert dialog.shape[:2] == (475, 764)


def test_get_top_row():
    frame = _load_fixture()
    dialog = cr.crop_dialog(frame, cr.detect_dialog_bbox(frame))
    row = cr.get_top_row(dialog)
    assert row.shape[:2] == (100, 764)


def test_parse_chest_type_strips_leading_ocr_artifact():
    assert cr.parse_chest_type("| Сундук Эпического Монстра") == "Сундук Эпического Монстра"


def test_parse_chest_type_empty_text():
    assert cr.parse_chest_type("") == ""


def test_parse_sender_extracts_name_after_prefix():
    assert cr.parse_sender("р От: Gray Cardinal") == "Gray Cardinal"


def test_parse_sender_strips_trailing_ocr_artifact():
    assert cr.parse_sender("От: Золотой|") == "Золотой"


def test_parse_sender_no_prefix_match_falls_back_to_raw_line():
    assert cr.parse_sender("SomeGarbledText") == "SomeGarbledText"


def test_read_top_row_on_fixture():
    frame = _load_fixture()
    dialog = cr.crop_dialog(frame, cr.detect_dialog_bbox(frame))
    chest_type, sender = cr.read_top_row(dialog)
    assert chest_type == "Сундук Эпического Монстра"
    assert sender == "Gray Cardinal"


def test_init_db_creates_table(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='local_chests'")
    assert cur.fetchone() is not None
    conn.close()


def test_insert_and_get_unsynced(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Alice", "2026-06-17T10:00:00")
    cr.insert_chest(conn, "Сундук Легендарного Монстра", "Bob", "2026-06-17T10:01:00")
    rows = cr.get_unsynced(conn)
    assert len(rows) == 2
    assert rows[0][1] == "Alice"
    assert rows[0][2] == "Сундук Эпического Монстра"
    conn.close()


def test_mark_synced_excludes_from_unsynced(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Alice", "2026-06-17T10:00:00")
    cr.insert_chest(conn, "Сундук Легендарного Монстра", "Bob", "2026-06-17T10:01:00")
    rows = cr.get_unsynced(conn)
    ids = [r[0] for r in rows]
    cr.mark_synced(conn, ids)
    assert cr.get_unsynced(conn) == []
    conn.close()
