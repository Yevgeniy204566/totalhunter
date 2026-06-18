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


def test_read_chest_type_uses_fixed_calibrated_region(monkeypatch):
    captured = {}

    def fake_to_region_dialog(x, y, w, h):
        captured['ref_rect'] = (x, y, w, h)
        return (50, 60, 70, 80)

    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", fake_to_region_dialog)

    def fake_ocr_text(roi, **kwargs):
        captured['roi_shape'] = roi.shape
        return "Эпический отряд нежити"

    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    result = cr.read_chest_type(frame)

    assert captured['ref_rect'] == cr.SOURCE_REF_RECT
    assert captured['roi_shape'] == (80, 70, 3)
    assert result == "Эпический отряд нежити"


def test_read_sender_name_uses_fixed_calibrated_region(monkeypatch):
    captured = {}

    def fake_to_region_dialog(x, y, w, h):
        captured['ref_rect'] = (x, y, w, h)
        return (10, 20, 30, 40)

    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", fake_to_region_dialog)

    def fake_ocr_text(roi, **kwargs):
        captured['roi_shape'] = roi.shape
        return "Conquest Georgio"

    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    result = cr.read_sender_name(frame)

    assert captured['ref_rect'] == cr.SENDER_REF_RECT
    assert captured['roi_shape'] == (40, 30, 3)
    assert result == "Conquest Georgio"


def test_read_sender_name_applies_clean_name_artifact_stripping(monkeypatch):
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 10, 10))
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: "Tess'")
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    assert cr.read_sender_name(frame) == "Tess"


def test_read_top_row_on_fixture(monkeypatch):
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (x, y, w, h))
    frame = _load_fixture()
    chest_type, sender = cr.read_top_row(frame)
    assert chest_type == "Эпический отряд нежити"
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


def test_find_open_button_region_is_top_row_right_side():
    """find_open_button must restrict the color search to the top-row band,
    not the whole dialog (avoids matching unrelated green UI elsewhere)."""
    captured = {}

    def fake_find_colored_button(region, color, pick):
        captured['region'] = region
        captured['color'] = color
        return (region[0] + 10, region[1] + 10)

    import chest_reader as cr_mod
    monkey_target = cr_mod.find_colored_button
    cr_mod.find_colored_button = fake_find_colored_button
    try:
        bbox = (671, 340, 764, 475)
        pos = cr.find_open_button(bbox)
        # region[0] = 671 + int(764*0.78) = 1266; region[1] = 340 + int(100*0.45) = 385
        # fake_find_colored_button returns (region[0]+10, region[1]+10)
        assert pos == (1276, 395)
        x, y, w, h = captured['region']
        assert x == 671 + int(764 * 0.78)
        assert y == 340 + int(100 * 0.45)
        assert captured['color'] == 'green'
    finally:
        cr_mod.find_colored_button = monkey_target


def test_collect_chests_counts_and_persists(tmp_path, monkeypatch):
    sequence = [
        ((100, 100), "Сундук Эпического Монстра", "Alice"),
        ((100, 100), "Сундук Эпического Монстра", "Bob"),
        (None, None, None),
    ]
    state = {'n': 0}

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))

    def fake_find_open_button(bbox):
        return sequence[state['n']][0]

    def fake_read_top_row(frame):
        _, chest_type, sender = sequence[state['n']]
        state['n'] += 1
        return chest_type, sender

    clicked = []
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", lambda pos: clicked.append(pos))

    db_path = str(tmp_path / "test_chest_buffer.db")
    result = cr.collect_chests(lambda: False, db_path=db_path)

    assert result["counts"] == {"Сундук Эпического Монстра": 2}
    assert len(clicked) == 2

    conn = cr.init_db(db_path)
    rows = cr.get_unsynced(conn)
    assert len(rows) == 2
    assert rows[0][1] == "Alice"
    assert rows[1][1] == "Bob"
    conn.close()


def test_collect_chests_stops_immediately_when_flag_already_set(tmp_path, monkeypatch):
    def boom():
        raise AssertionError("grab_fullscreen must not be called when stop_flag is already True")
    monkeypatch.setattr(cr, "grab_fullscreen", boom)

    db_path = str(tmp_path / "test_chest_buffer.db")
    result = cr.collect_chests(lambda: True, db_path=db_path)
    assert result == {"counts": {}, "items": []}


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_export_to_api_success(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured['url'] = url
        captured['json'] = json
        return _FakeResponse(200)

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")

    items = [{"chest_type": "Сундук Эпического Монстра", "sender": "Alice",
              "timestamp": "2026-06-17T10:00:00"}]
    result = cr.export_to_api("K229", "Legion", items)

    assert result == {"success": True}
    assert captured['url'].endswith("/api/v1/chests/import")
    assert captured['json']["hwid"] == "ABCD1234"
    assert captured['json']["kingdom"] == "K229"
    assert captured['json']["clan"] == "Legion"
    assert captured['json']["items"] == items


def test_export_to_api_http_failure(monkeypatch):
    monkeypatch.setattr(cr.requests, "post", lambda url, json, timeout: _FakeResponse(404))
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    assert cr.export_to_api("K229", "Legion", []) == {"success": False}


def test_export_to_api_network_exception(monkeypatch):
    def raise_exc(url, json, timeout):
        raise cr.requests.RequestException("no connection")
    monkeypatch.setattr(cr.requests, "post", raise_exc)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    assert cr.export_to_api("K229", "Legion", []) == {"success": False}


def test_export_to_api_low_credits(monkeypatch):
    monkeypatch.setattr(cr.requests, "post", lambda url, json, timeout: _FakeResponse(402))
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    assert cr.export_to_api("K229", "Legion", []) == {"success": False, "low_credits": True}
