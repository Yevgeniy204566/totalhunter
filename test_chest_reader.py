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


def test_clean_name_preserves_space_separated_stylized_name():
    assert cr.clean_name("M A R I S H A") == "M A R I S H A"


def test_clean_name_strips_trailing_digit_group():
    assert cr.clean_name("PlayerName 123") == "PlayerName"


def test_clean_name_strips_multiple_trailing_digit_groups():
    assert cr.clean_name("PlayerName 12 3") == "PlayerName"


def test_clean_name_strips_trailing_punctuation():
    assert cr.clean_name("Tess'") == "Tess"


def test_clean_name_strips_leading_clan_tag():
    assert cr.clean_name("[ABC] Niduel") == "Niduel"


def test_read_fixed_field_applies_named_offset(monkeypatch):
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (10, 10, 3, 3))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: (2, -1))

    frame = np.arange(1200).reshape(20, 20, 3).astype(np.uint8)
    captured = {}
    def fake_ocr(roi, **kwargs):
        if "roi" not in captured:
            captured["roi"] = roi.copy()
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr)

    cr.read_fixed_field(frame, (1, 2, 3, 4), offset_name="chest_type")

    expected = frame[9:12, 12:15]
    assert np.array_equal(captured["roi"], expected)


def test_read_fixed_field_without_offset_name_uses_zero_offset(monkeypatch):
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (10, 10, 3, 3))

    def fail_if_called(name):
        raise AssertionError("get_ui_offset should not be called when offset_name is None")
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", fail_if_called)

    captured = {}
    def fake_ocr(roi, **kwargs):
        if "roi" not in captured:
            captured["roi"] = roi.copy()
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr)

    frame = np.arange(1200).reshape(20, 20, 3).astype(np.uint8)
    cr.read_fixed_field(frame, (1, 2, 3, 4))

    expected = frame[10:13, 10:13]
    assert np.array_equal(captured["roi"], expected)


def test_read_chest_type_passes_chest_type_offset_name(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: captured.setdefault("name", name) and (0, 0))
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: "")

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_chest_type(frame)

    assert captured["name"] == "chest_type"


def test_read_sender_name_passes_chest_sender_offset_name(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: captured.setdefault("name", name) and (0, 0))
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: "")

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame)

    assert captured["name"] == "chest_sender"


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


def test_get_unsynced_counts_groups_by_type(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Игрок1", "2026-06-19T10:00:00")
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Игрок2", "2026-06-19T10:00:05")
    cr.insert_chest(conn, "Редкий склеп 25", "Игрок1", "2026-06-19T10:00:10")
    conn.close()

    conn = cr.init_db(db_path)
    counts = cr.get_unsynced_counts(conn)
    conn.close()

    assert counts == {"Сундук Эпического Монстра": 2, "Редкий склеп 25": 1}


def test_get_unsynced_counts_ignores_synced_rows(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Тип А", "Игрок1", "2026-06-19T10:00:00")
    cr.insert_chest(conn, "Тип Б", "Игрок1", "2026-06-19T10:00:05")
    rows = cr.get_unsynced(conn)
    ids_type_a = [r[0] for r in rows if r[2] == "Тип А"]
    cr.mark_synced(conn, ids_type_a)
    conn.close()

    conn = cr.init_db(db_path)
    counts = cr.get_unsynced_counts(conn)
    conn.close()

    assert counts == {"Тип Б": 1}


def test_get_unsynced_counts_empty_after_full_sync(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Тип А", "Игрок1", "2026-06-19T10:00:00")
    rows = cr.get_unsynced(conn)
    cr.mark_synced(conn, [r[0] for r in rows])
    conn.close()

    conn = cr.init_db(db_path)
    counts = cr.get_unsynced_counts(conn)
    conn.close()

    assert counts == {}


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

    def fake_read_top_row(frame, **kwargs):
        _, chest_type, sender = sequence[state['n']]
        state['n'] += 1
        return chest_type, sender

    clicked = []
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", lambda pos, pause_range=cr.ANTI_DETECT_PAUSE_RANGE: clicked.append(pos))

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


def test_collect_chests_counts_are_cumulative_from_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Старый", "2026-06-19T09:00:00")
    conn.close()

    calls = {"n": 0}

    def fake_find_open_button(bbox):
        calls["n"] += 1
        return (10, 10) if calls["n"] <= 1 else None

    def fake_read_top_row(frame, **kwargs):
        return ("Сундук Эпического Монстра", "Новый")

    def fake_click_open_button(pos, pause_range=cr.ANTI_DETECT_PAUSE_RANGE):
        pass

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", fake_click_open_button)

    result = cr.collect_chests(lambda: False, db_path=db_path)

    assert result["counts"] == {"Сундук Эпического Монстра": 2}


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


def test_click_open_button_uses_passed_pause_range(monkeypatch):
    captured = {}

    def fake_uniform(lo, hi):
        captured["range"] = (lo, hi)
        return 0.0

    monkeypatch.setattr(cr.random, "uniform", fake_uniform)
    monkeypatch.setattr(cr.pyautogui, "click", lambda *a, **k: None)
    monkeypatch.setattr(cr.time, "sleep", lambda *a, **k: None)

    cr.click_open_button((10, 10), pause_range=(0.5, 0.6))

    assert captured["range"] == (0.5, 0.6)


def test_click_open_button_defaults_to_module_constant(monkeypatch):
    captured = {}

    def fake_uniform(lo, hi):
        captured["range"] = (lo, hi)
        return 0.0

    monkeypatch.setattr(cr.random, "uniform", fake_uniform)
    monkeypatch.setattr(cr.pyautogui, "click", lambda *a, **k: None)
    monkeypatch.setattr(cr.time, "sleep", lambda *a, **k: None)

    cr.click_open_button((10, 10))

    assert captured["range"] == cr.ANTI_DETECT_PAUSE_RANGE


def test_collect_chests_forwards_pause_range_to_click(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    captured_ranges = []

    def fake_grab_fullscreen():
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def fake_detect_dialog_bbox(frame):
        return (0, 0, 300, 300)

    def fake_crop_dialog(frame, bbox):
        return np.zeros((300, 300, 3), dtype=np.uint8)

    calls = {"n": 0}

    def fake_find_open_button(bbox):
        calls["n"] += 1
        return (10, 10) if calls["n"] <= 1 else None

    def fake_read_top_row(frame, **kwargs):
        return ("Сундук Эпического Монстра", "Игрок")

    def fake_click_open_button(pos, pause_range=cr.ANTI_DETECT_PAUSE_RANGE):
        captured_ranges.append(pause_range)

    monkeypatch.setattr(cr, "grab_fullscreen", fake_grab_fullscreen)
    monkeypatch.setattr(cr, "detect_dialog_bbox", fake_detect_dialog_bbox)
    monkeypatch.setattr(cr, "crop_dialog", fake_crop_dialog)
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", fake_click_open_button)

    cr.collect_chests(lambda: False, db_path=db_path, pause_range=(0.5, 0.6))

    assert captured_ranges == [(0.5, 0.6)]


def test_read_sender_name_uses_literal_diacritic_config(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame)

    assert captured["lang"] == "rus+eng+script/Latin"
    assert captured["extra_config"] == "-c load_system_dawg=0 -c load_freq_dawg=0"


def test_read_chest_type_keeps_default_ocr_config(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_chest_type(frame)

    assert captured["lang"] == "rus+eng"
    assert captured["extra_config"] == ""


def test_ocr_text_appends_extra_config_to_psm_flag(monkeypatch):
    captured = {}

    def fake_image_to_string(image, config, lang, timeout):
        captured["config"] = config
        captured["lang"] = lang
        return ""
    monkeypatch.setattr(cr.pytesseract, "image_to_string", fake_image_to_string)

    roi = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.ocr_text(roi, lang="rus+eng+script/Latin", extra_config="-c load_system_dawg=0")

    assert captured["config"] == "--psm 7 -c load_system_dawg=0"
    assert captured["lang"] == "rus+eng+script/Latin"


def test_read_sender_name_light_lang_by_default(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame)

    assert captured["lang"] == "rus+eng+script/Latin"


def test_read_sender_name_full_lang_when_requested(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame, full_lang=True)

    assert captured["lang"] == "eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor"


def test_read_top_row_forwards_full_lang_to_sender(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr, "read_chest_type", lambda frame: "Сундук")

    def fake_read_sender_name(frame, full_lang=False):
        captured["full_lang"] = full_lang
        return "Player"
    monkeypatch.setattr(cr, "read_sender_name", fake_read_sender_name)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_top_row(frame, full_lang=True)

    assert captured["full_lang"] is True


def test_collect_chests_forwards_full_lang_to_read_top_row(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    captured = {}

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))

    calls = {"n": 0}

    def fake_find_open_button(bbox):
        calls["n"] += 1
        return (10, 10) if calls["n"] <= 1 else None
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)

    def fake_read_top_row(frame, full_lang=False):
        captured["full_lang"] = full_lang
        return ("Сундук", "Player")
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", lambda pos, pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)

    cr.collect_chests(lambda: False, db_path=db_path, full_lang=True)

    assert captured["full_lang"] is True
