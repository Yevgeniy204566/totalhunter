import os
import datetime
import time
import threading
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


# --- Crop/OCR split (сессия #149, конвейер): producer вырезает пиксели и сохраняет на диск,
# OCR над готовым кропом делает отдельный фоновый consumer — read_fixed_field/read_top_row
# продолжают работать как раньше (обёртки над crop+ocr), см. тесты выше, они не меняются.

def test_crop_fixed_field_returns_same_roi_as_read_fixed_field(monkeypatch):
    """crop_fixed_field must do exactly the region-lookup half of read_fixed_field
    (coord_manager + ui_offset), returning raw pixels with no OCR."""
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (10, 10, 3, 3))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: (2, -1))

    frame = np.arange(1200).reshape(20, 20, 3).astype(np.uint8)
    roi = cr.crop_fixed_field(frame, (1, 2, 3, 4), offset_name="chest_type")

    expected = frame[9:12, 12:15]
    assert np.array_equal(roi, expected)


def test_crop_chest_type_and_sender_name_match_fixture_ocr(monkeypatch):
    """crop_chest_type/crop_sender_name feed the exact same pixels that
    read_chest_type/read_sender_name already OCR correctly on the fixture —
    proves the crop step alone (no OCR yet) is a faithful split."""
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (x, y, w, h))
    frame = _load_fixture()

    type_roi = cr.crop_chest_type(frame)
    sender_roi = cr.crop_sender_name(frame)

    assert cr.ocr_chest_type_crop(type_roi) == "Эпический отряд нежити"
    assert cr.ocr_sender_name_crop(sender_roi) == "Gray Cardinal"


def test_pack_unpack_row_crops_roundtrip(monkeypatch):
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (x, y, w, h))
    frame = _load_fixture()
    type_roi = cr.crop_chest_type(frame)
    sender_roi = cr.crop_sender_name(frame)

    combined = cr.pack_row_crops(type_roi, sender_roi)
    unpacked_type, unpacked_sender = cr.unpack_row_crops(combined)

    assert np.array_equal(unpacked_type, type_roi)
    assert np.array_equal(unpacked_sender, sender_roi)


def test_unpack_row_crops_does_not_mix_fields_on_a_scaled_screen(monkeypatch):
    """Регрессия сессии #149 (живой баг владельца, 2026-09-25): coord_manager.to_region()
    масштабирует ШИРИНУ И ВЫСОТУ кропа (scale_x/scale_y), не только позицию — на реальном
    экране владельца (profile_client.json: scale_x=1.332, scale_y=1.363) кроп типа/имени
    получается ~494x33 / ~481x33, НЕ эталонные 371x24 / 361x24. unpack_row_crops резал по
    жёстко зашитым эталонным размерам — итог: срез имени наполовину состоял из НИЗА кропа
    типа (не имени!) и наполовину из ВЕРХА настоящего имени — франкенштейн из двух разных
    надписей, объясняющий мусорные строки вроде «КНАГ ЕР IRA! AL VW/AILIN» при исправно
    читающемся типе (тип лишь обрезался, но не смешивался — оставался внутри своей же
    области). Исправление пересчитывает точный масштабированный размер каждого поля через
    тот же coord_manager, что и при вырезке — мок здесь имитирует именно это состояние."""
    scale_x, scale_y = 1.332389046270066, 1.3632019115890084

    def fake_to_region_dialog(x, y, w, h):
        return (x, y, round(w * scale_x), round(h * scale_y))
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", fake_to_region_dialog)

    type_w, type_h = cr.coord_manager.to_region_dialog(*cr.SOURCE_REF_RECT)[2:4]
    sender_w, sender_h = cr.coord_manager.to_region_dialog(*cr.SENDER_REF_RECT)[2:4]
    assert (type_h, type_w) == (33, 494) and (sender_h, sender_w) == (33, 481)  # sanity, see comment above

    type_roi = np.full((type_h, type_w, 3), 100, dtype=np.uint8)
    sender_roi = np.full((sender_h, sender_w, 3), 200, dtype=np.uint8)

    combined = cr.pack_row_crops(type_roi, sender_roi)
    unpacked_type, unpacked_sender = cr.unpack_row_crops(combined)

    assert np.array_equal(unpacked_type, type_roi)
    assert np.array_equal(unpacked_sender, sender_roi)
    assert not np.any(unpacked_sender == 100), "срез имени не должен содержать ни пикселя из кропа типа"


def test_crop_top_row_and_ocr_top_row_crops_match_read_top_row(monkeypatch):
    """End-to-end for the pipeline's split: crop at capture time, OCR later on the saved
    crop, must give the exact same result as the still-synchronous read_top_row."""
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (x, y, w, h))
    frame = _load_fixture()

    combined = cr.crop_top_row(frame)
    chest_type, sender = cr.ocr_top_row_crops(combined)

    assert (chest_type, sender) == cr.read_top_row(frame)


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


def test_delete_sent_removes_rows_from_pc(tmp_path):
    """Владелец 2026-09-26: отправленные сундуки на ПК не хранятся — строки удаляются
    физически, а не помечаются is_synced=1."""
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Alice", "2026-06-17T10:00:00")
    cr.insert_chest(conn, "Сундук Легендарного Монстра", "Bob", "2026-06-17T10:01:00")
    cr.insert_chest(conn, "Сундук Легендарного Монстра", "Carol", "2026-06-17T10:02:00")
    rows = cr.get_unsynced(conn)
    cr.delete_sent(conn, [r[0] for r in rows[:2]])
    left = conn.execute("SELECT raw_player_name FROM local_chests").fetchall()
    conn.close()
    assert left == [("Carol",)]


def test_init_db_purges_rows_synced_by_old_versions(tmp_path):
    """Старые версии копили is_synced=1 вечно (у владельца 1500 строк за сутки) —
    при открытии базы они вычищаются, неотправленные не трогаются."""
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Тип", "Отправлен", "2026-09-26T09:00:00")
    cr.insert_chest(conn, "Тип", "НеОтправлен", "2026-09-26T09:00:01")
    conn.execute("UPDATE local_chests SET is_synced = 1 WHERE raw_player_name = 'Отправлен'")
    conn.commit()
    conn.close()

    conn = cr.init_db(db_path)
    left = conn.execute("SELECT raw_player_name, is_synced FROM local_chests").fetchall()
    conn.close()
    assert left == [("НеОтправлен", 0)]


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
    cr.delete_sent(conn, ids_type_a)
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
    cr.delete_sent(conn, [r[0] for r in rows])
    conn.close()

    conn = cr.init_db(db_path)
    counts = cr.get_unsynced_counts(conn)
    conn.close()

    assert counts == {}


def test_detect_row_pitch_matches_reference_fixture():
    """Sanity/parity check: on the original calibration screenshot, the dynamically
    measured pitch must equal the old hardcoded ROW_PITCH=100 — proves the dynamic
    method is a safe drop-in, not a behaviour change, at the resolution it was
    originally tuned for."""
    frame = _load_fixture()
    bbox = cr.detect_dialog_bbox(frame)
    dialog = cr.crop_dialog(frame, bbox)
    assert cr.detect_row_pitch(dialog) == (100, 1)


def _synthetic_scaled_dialog():
    """A dialog rendered at a bigger real pixel size than the reference monitor
    (e.g. a 2K screen where the game draws everything ~1.33x larger) — three
    horizontal bands 133px tall each, giving detect_row_pitch two clean edges to
    measure, exactly like tournament_reader's own fixture-based test does with a
    real screenshot. Reproduces the bug class without needing a real 2K capture."""
    h, w = 399, 600
    dialog = np.zeros((h, w, 3), dtype=np.uint8)
    dialog[0:133] = 60
    dialog[133:266] = 180
    dialog[266:399] = 60
    return dialog


def test_find_open_button_scales_search_band_to_measured_pitch_not_hardcoded_100():
    """Reproduces the 2K bug: chest_reader used to search a band computed from the
    hardcoded ROW_PITCH=100 (correct only at the original calibration resolution).
    On a dialog whose real on-screen row height is bigger (measured pitch=133 here,
    simulating a 2K monitor), the search band must scale with the MEASURED pitch —
    otherwise it lands above the real row content and the button is never found,
    which is read as "list empty" and stops collection early."""
    dialog = _synthetic_scaled_dialog()
    measured_pitch, measured_row_top = cr.detect_row_pitch(dialog)
    assert (measured_pitch, measured_row_top) == (133, 132)  # sanity on the fixture itself

    captured = {}

    def fake_find_colored_button(region, color, pick):
        captured['region'] = region
        captured['color'] = color
        return None

    import chest_reader as cr_mod
    monkey_target = cr_mod.find_colored_button
    cr_mod.find_colored_button = fake_find_colored_button
    try:
        bbox = (671, 340, 600, 399)
        cr.find_open_button(bbox, dialog)
        x, y, w, h = captured['region']
        assert (x, y, w, h) == (1139, 531, 131, 73)
    finally:
        cr_mod.find_colored_button = monkey_target


def test_find_open_button_region_is_top_row_right_side():
    """find_open_button must restrict the color search to the top-row band,
    not the whole dialog (avoids matching unrelated green UI elsewhere). Its
    return value is only a presence signal for collect_chests's stop check —
    the position itself is never used for clicking, see click_open_button.
    Uses the real fixture's own dialog crop so detect_row_pitch has real row
    boundaries to measure (row_top=1, see test_detect_row_pitch_matches_reference_fixture)."""
    captured = {}

    def fake_find_colored_button(region, color, pick):
        captured['region'] = region
        captured['color'] = color
        return (region[0] + 10, region[1] + 10)

    import chest_reader as cr_mod
    monkey_target = cr_mod.find_colored_button
    cr_mod.find_colored_button = fake_find_colored_button
    try:
        frame = _load_fixture()
        bbox = cr.detect_dialog_bbox(frame)
        dialog = cr.crop_dialog(frame, bbox)
        assert bbox == (671, 340, 764, 475)
        pos = cr.find_open_button(bbox, dialog)
        assert pos == (1276, 396)
        x, y, w, h = captured['region']
        assert x == 671 + int(764 * 0.78)
        assert y == 340 + 1 + int(100 * 0.45)
        assert captured['color'] == 'green'
    finally:
        cr_mod.find_colored_button = monkey_target


def test_click_open_button_uses_fixed_point_plus_tuning_offset(monkeypatch):
    """click_open_button must click coord_manager.to_screen_dialog(OPEN_BUTTON_REF_POS)
    shifted by the "chest_collect" tuning offset — no color/contour search."""
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_screen_dialog", lambda x, y: (1000, 500))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: (7, -3))
    monkeypatch.setattr(cr.random, "randint", lambda lo, hi: 0)
    monkeypatch.setattr(cr.random, "uniform", lambda lo, hi: 0.0)
    monkeypatch.setattr(cr.time, "sleep", lambda *a, **k: None)

    def fake_click(x, y):
        captured['pos'] = (x, y)
    monkeypatch.setattr(cr.pyautogui, "click", fake_click)

    cr.click_open_button()

    assert captured['pos'] == (1007, 497)


def test_collect_chests_counts_and_persists(tmp_path, monkeypatch):
    """Producer/consumer split (сессия #149): find_open_button gating now tracks
    crop_top_row's own call count (one per captured chest) — read_top_row is no longer
    called by the loop at all, OCR happens later in the background consumer."""
    sequence = [
        ("Сундук Эпического Монстра", "Alice"),
        ("Сундук Эпического Монстра", "Bob"),
    ]
    produced = {'n': 0}

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button",
                        lambda bbox, dialog: (10, 10) if produced['n'] < len(sequence) else None)

    def fake_crop_top_row(frame):
        produced['n'] += 1
        return np.zeros((10, 10, 3), dtype=np.uint8)
    monkeypatch.setattr(cr, "crop_top_row", fake_crop_top_row)

    consumed = {'n': 0}

    def fake_ocr_top_row_crops(combined, full_lang=False):
        item = sequence[consumed['n']]
        consumed['n'] += 1
        return item
    monkeypatch.setattr(cr, "ocr_top_row_crops", fake_ocr_top_row_crops)

    clicked = []
    monkeypatch.setattr(cr, "click_open_button", lambda pause_range=cr.ANTI_DETECT_PAUSE_RANGE: clicked.append(True))

    db_path = str(tmp_path / "test_chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir)

    assert result["counts"] == {"Сундук Эпического Монстра": 2}
    assert result["list_ended"] is True
    assert result["batch_full"] is False
    assert len(clicked) == 2

    conn = cr.init_db(db_path)
    rows = cr.get_unsynced(conn)
    assert len(rows) == 2
    assert rows[0][1] == "Alice"
    assert rows[1][1] == "Bob"
    conn.close()


def test_collect_chests_tolerates_single_transient_button_miss(tmp_path, monkeypatch):
    """Regression test: a one-off HSV miss (dialog fade-in animation, a hover-state
    color shift, a reward popup briefly overlapping the button) must not be read as
    "list is empty" — the loop must keep going and pick up the next chest instead of
    stopping instantly on the very first missed check."""
    responses = iter([(10, 10), None, (10, 10)] + [None] * cr.EMPTY_BUTTON_RETRY_LIMIT)
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: next(responses))
    monkeypatch.setattr(cr.time, "sleep", lambda s: None)
    monkeypatch.setattr(cr, "crop_top_row", lambda frame: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda combined, full_lang=False: ("Сундук", "Alice"))
    monkeypatch.setattr(cr, "click_open_button", lambda pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)

    db_path = str(tmp_path / "test_chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir)

    assert result["counts"] == {"Сундук": 2}


def test_collect_chests_stops_after_limit_consecutive_button_misses(tmp_path, monkeypatch):
    """Discriminating counterpart to the transient-miss test above: the loop must
    still stop, and after exactly EMPTY_BUTTON_RETRY_LIMIT consecutive misses — not
    fewer (would reintroduce the instant-stop bug) and not more (would hang on a
    genuinely empty list)."""
    calls = {"n": 0}

    def fake_find_open_button(bbox, dialog):
        calls["n"] += 1
        return None

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr.time, "sleep", lambda s: None)

    db_path = str(tmp_path / "test_chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir)

    assert result == {"counts": {}, "items": [], "batch_full": False, "list_ended": True}
    assert calls["n"] == cr.EMPTY_BUTTON_RETRY_LIMIT


def test_collect_chests_waits_one_second_between_button_misses(tmp_path, monkeypatch):
    """Владелец 2026-09-26: между проверками «кнопки нет» бот ждёт 1 с (было 0.3 с) —
    за ~0.6 с игра не всегда успевала подтянуть следующую строку, бот считал список
    пустым после 2 сундуков."""
    sleeps = []
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: None)
    monkeypatch.setattr(cr.time, "sleep", sleeps.append)

    cr.collect_chests(lambda: False, db_path=str(tmp_path / "db.db"),
                      pending_dir=str(tmp_path / "chest_pending"))

    assert cr.EMPTY_BUTTON_RETRY_PAUSE == 1.0
    assert sleeps.count(1.0) == cr.EMPTY_BUTTON_RETRY_LIMIT - 1


def test_collect_chests_stops_immediately_when_flag_already_set(tmp_path, monkeypatch):
    def boom():
        raise AssertionError("grab_fullscreen must not be called when stop_flag is already True")
    monkeypatch.setattr(cr, "grab_fullscreen", boom)

    db_path = str(tmp_path / "test_chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    result = cr.collect_chests(lambda: True, db_path=db_path, pending_dir=pending_dir)
    assert result == {"counts": {}, "items": [], "batch_full": False, "list_ended": False}


def test_collect_chests_counts_are_cumulative_from_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Старый", "2026-06-19T09:00:00")
    conn.close()

    produced = {"n": 0}

    def fake_find_open_button(bbox, dialog):
        return (10, 10) if produced["n"] < 1 else None

    def fake_crop_top_row(frame):
        produced["n"] += 1
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def fake_ocr_top_row_crops(combined, full_lang=False):
        return ("Сундук Эпического Монстра", "Новый")

    def fake_click_open_button(pause_range=cr.ANTI_DETECT_PAUSE_RANGE):
        pass

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "crop_top_row", fake_crop_top_row)
    monkeypatch.setattr(cr, "ocr_top_row_crops", fake_ocr_top_row_crops)
    monkeypatch.setattr(cr, "click_open_button", fake_click_open_button)

    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir)

    assert result["counts"] == {"Сундук Эпического Монстра": 2}


def test_collect_chests_clicks_dont_wait_for_slow_ocr(tmp_path, monkeypatch):
    """The whole point of the conveyor (входящие заметки, п.D): OCR must not block the
    click loop. A slow/blocked OCR must not delay any of the clicks — proven by holding
    the very first OCR call hostage on an Event and checking every click already
    happened before that Event is ever released."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    n_chests = 3
    produced = {"n": 0}
    clicked = []
    ocr_started = threading.Event()
    release_ocr = threading.Event()

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button",
                        lambda bbox, dialog: (10, 10) if produced["n"] < n_chests else None)

    def fake_crop_top_row(frame):
        produced["n"] += 1
        return np.zeros((10, 10, 3), dtype=np.uint8)
    monkeypatch.setattr(cr, "crop_top_row", fake_crop_top_row)

    def fake_click_open_button(pause_range=cr.ANTI_DETECT_PAUSE_RANGE):
        clicked.append(True)
    monkeypatch.setattr(cr, "click_open_button", fake_click_open_button)

    def fake_ocr_top_row_crops(combined, full_lang=False):
        ocr_started.set()
        release_ocr.wait(timeout=5)
        return ("Тип", "Игрок")
    monkeypatch.setattr(cr, "ocr_top_row_crops", fake_ocr_top_row_crops)

    holder = {}

    def run():
        holder["result"] = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir)

    t = threading.Thread(target=run)
    t.start()
    try:
        assert ocr_started.wait(timeout=5), "OCR (consumer) never started"
        # OCR for chest #1 is now blocked on release_ocr — the producer must not be
        # waiting on it: give it a moment to run ahead and finish ALL its clicks.
        deadline = time.time() + 3
        while len(clicked) < n_chests and time.time() < deadline:
            time.sleep(0.01)
        assert len(clicked) == n_chests
    finally:
        release_ocr.set()
        t.join(timeout=5)

    assert holder["result"]["counts"] == {"Тип": n_chests}


def test_collect_chests_stops_at_batch_limit_even_with_more_available(tmp_path, monkeypatch):
    """BATCH_LIMIT (владелец 2026-09-25): один платёж 10◆ покрывает отправку батча целиком
    независимо от размера — producer обязан остановиться на лимите, даже если в игре есть
    ещё сундуки (find_open_button продолжал бы находить кнопку бесконечно)."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: (10, 10))  # бесконечный список
    monkeypatch.setattr(cr, "crop_top_row", lambda frame: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda combined, full_lang=False: ("Тип", "Игрок"))
    monkeypatch.setattr(cr, "click_open_button", lambda pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)

    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir, batch_limit=3)

    assert result["batch_full"] is True
    assert result["list_ended"] is False
    assert sum(result["counts"].values()) == 3


def test_collect_chests_processes_leftover_crops_from_previous_run(tmp_path, monkeypatch):
    """Не допускать потери сундуков при перезапуске (входящие заметки, п.D): кроп,
    оставшийся на диске от прерванного запуска (краш/закрытие бота до того, как consumer
    успел его разобрать), подхватывается consumer'ом заново, даже если producer в ЭТОМ
    вызове вообще не работает (stop_flag уже True)."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    os.makedirs(pending_dir, exist_ok=True)
    leftover_path = os.path.join(pending_dir, "000001.png")
    cv2.imwrite(leftover_path, np.zeros((48, 400, 3), dtype=np.uint8))

    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda combined, full_lang=False: ("Старый тип", "Забытый"))

    result = cr.collect_chests(lambda: True, db_path=db_path, pending_dir=pending_dir)

    assert result["counts"] == {"Старый тип": 1}
    assert not os.path.exists(leftover_path)


def test_count_pending_reflects_queue_size(tmp_path):
    """Источник прогресс-бара очереди OCR в GUI (по образцу count_queue Биржи 2.0)."""
    pending_dir = str(tmp_path / "chest_pending")
    assert cr.count_pending(pending_dir) == 0

    os.makedirs(pending_dir, exist_ok=True)
    cv2.imwrite(os.path.join(pending_dir, "000001.png"), np.zeros((10, 10, 3), dtype=np.uint8))
    cv2.imwrite(os.path.join(pending_dir, "000002.png"), np.zeros((10, 10, 3), dtype=np.uint8))
    assert cr.count_pending(pending_dir) == 2


def test_delete_unsynced_batch_clears_db_rows_and_pending_crops(tmp_path):
    """Кнопка «Удалить батч» (владелец 2026-09-25): убирает и непринятые строки в БД
    (is_synced=0), и необработанные кропы очереди — уже отправленные (is_synced=1)
    строки на ПК не хранятся вовсе, _batch_size() должен вернуться к 0."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    os.makedirs(pending_dir, exist_ok=True)
    cv2.imwrite(os.path.join(pending_dir, "000001.png"), np.zeros((10, 10, 3), dtype=np.uint8))

    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Тип", "Игрок1", "2026-09-25T21:00:00")
    conn.execute("UPDATE local_chests SET is_synced = 1 WHERE id = 1")  # уже отправлен раньше
    cr.insert_chest(conn, "Тип", "Игрок2", "2026-09-25T21:00:01")       # ещё не отправлен
    conn.commit()
    conn.close()

    removed = cr.delete_unsynced_batch(db_path, pending_dir)

    assert removed == 1
    assert cr.count_pending(pending_dir) == 0
    conn = cr.init_db(db_path)
    rows = conn.execute("SELECT raw_player_name, is_synced FROM local_chests").fetchall()
    conn.close()
    assert rows == []  # отправленная тоже не хранится (вычищена init_db)


def test_collect_chests_calls_on_batch_ready_when_list_ends(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: None)  # сразу пусто
    monkeypatch.setattr(cr.time, "sleep", lambda s: None)

    reasons = []
    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir,
                               on_batch_ready=reasons.append)

    assert reasons == ["list_ended"]
    assert result["list_ended"] is True


def test_collect_chests_counts_reflect_state_after_on_batch_ready_not_before(tmp_path, monkeypatch):
    """Регрессия сессии #149 (живая жалоба владельца — 'после отправки в окне сундуков
    остаются записи'): 'counts' раньше считался ДО on_batch_ready — main.py показывал
    в окне сундуков всё ещё непустой (устаревший) счёт поверх только что очищенного
    успешной отправкой списка, будто отправка ничего не почистила. on_batch_ready
    здесь сам помечает всё синхронизированным (как настоящая отправка) — итоговый
    result['counts'] обязан быть уже ПУСТЫМ, не старым."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: None)  # сразу пусто
    monkeypatch.setattr(cr.time, "sleep", lambda s: None)

    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Тип", "Игрок", "2026-09-25T21:00:00")
    conn.close()

    def fake_on_batch_ready(reason):
        conn = cr.init_db(db_path)
        cr.delete_sent(conn, [r[0] for r in cr.get_unsynced(conn)])
        conn.close()

    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir,
                               on_batch_ready=fake_on_batch_ready)

    assert result["counts"] == {}


def test_collect_chests_calls_on_batch_ready_with_batch_full_reason(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: (10, 10))
    monkeypatch.setattr(cr, "crop_top_row", lambda frame: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda combined, full_lang=False: ("Тип", "Игрок"))
    monkeypatch.setattr(cr, "click_open_button", lambda pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)

    reasons = []
    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir, batch_limit=1,
                               on_batch_ready=reasons.append)

    assert reasons == ["batch_full"]
    assert result["batch_full"] is True


def test_collect_chests_on_batch_ready_exception_does_not_lose_result(tmp_path, monkeypatch):
    """A network/credit failure inside the owner's send-to-server callback must not
    swallow the (already-correct) collection result — it lands in 'batch_ready_error'."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: None)
    monkeypatch.setattr(cr.time, "sleep", lambda s: None)

    def boom(reason):
        raise RuntimeError("сервер недоступен")

    result = cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir,
                               on_batch_ready=boom)

    assert result["list_ended"] is True
    assert "сервер недоступен" in result["batch_ready_error"]


class _FakeResponse:
    def __init__(self, status_code, count=None):
        self.status_code = status_code
        self._count = count

    def json(self):
        # count=None имитирует ответ БЕЗ поля count вовсе (ключ отсутствует, не None) —
        # export_to_api должен в этом случае считать, что принято всё отправленное.
        body = {"ok": True}
        if self._count is not None:
            body["count"] = self._count
        return body


def test_export_to_api_success(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured['url'] = url
        captured['json'] = json
        return _FakeResponse(200, count=1)

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")

    items = [{"chest_type": "Сундук Эпического Монстра", "sender": "Alice",
              "timestamp": "2026-06-17T10:00:00"}]
    result = cr.export_to_api("K229", "Legion", items)

    assert result == {"success": True, "count": 1}
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


def test_export_to_api_uses_45_second_timeout(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured['timeout'] = timeout
        return _FakeResponse(200, count=0)

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    cr.export_to_api("K229", "Legion", [])
    assert captured['timeout'] == 45


def test_export_to_api_retries_once_on_timeout_then_succeeds(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise cr.requests.Timeout("timed out")
        return _FakeResponse(200, count=0)

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")

    result = cr.export_to_api("K229", "Legion", [])

    assert result == {"success": True, "count": 0}
    assert len(calls) == 2


def test_export_to_api_reports_partial_count_when_server_accepts_fewer(monkeypatch):
    """Регрессия сессии #149 (живой инцидент владельца, 2026-09-25): сервер вернул
    200 OK, но 133 из 354 отправленных сундуков реально на сервер не попали — код
    проверял только HTTP-статус, не count из ответа, и пометил ВСЕ как отправленные.
    export_to_api теперь возвращает count из ответа сервера — сверку со len(items) и
    решение, что делать при несовпадении, принимает вызывающий код (main.py)."""
    monkeypatch.setattr(cr.requests, "post", lambda url, json, timeout: _FakeResponse(200, count=2))
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")

    items = [{"chest_type": "A", "sender": "X", "timestamp": "2026-09-25T21:00:00"},
             {"chest_type": "B", "sender": "Y", "timestamp": "2026-09-25T21:00:01"},
             {"chest_type": "C", "sender": "Z", "timestamp": "2026-09-25T21:00:02"}]
    result = cr.export_to_api("229", "Феникс", items)

    assert result == {"success": True, "count": 2}


def test_export_to_api_count_defaults_to_submitted_when_missing_from_response(monkeypatch):
    """Защита от старого/нестандартного ответа без поля count — не должно ложно
    выглядеть как 'частичный провал', раз сервер вообще ничего не сообщил."""
    class _NoCountResponse:
        status_code = 200
        def json(self):
            return {"ok": True}
    monkeypatch.setattr(cr.requests, "post", lambda url, json, timeout: _NoCountResponse())
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")

    items = [{"chest_type": "A", "sender": "X", "timestamp": "2026-09-25T21:00:00"}]
    result = cr.export_to_api("229", "Феникс", items)

    assert result == {"success": True, "count": 1}


def test_export_to_api_gives_up_after_second_attempt_fails(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(1)
        raise cr.requests.RequestException("no connection")

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    monkeypatch.setattr(cr, "log_error_to_server", lambda msg: None)

    result = cr.export_to_api("K229", "Legion", [])

    assert result == {"success": False}
    assert len(calls) == 2


def test_export_to_api_does_not_retry_on_low_credits(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(1)
        return _FakeResponse(402)

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")

    cr.export_to_api("K229", "Legion", [])

    assert len(calls) == 1


def test_export_to_api_logs_failure_reason_after_exhausting_retries(monkeypatch):
    logged = {}

    def fake_post(url, json, timeout):
        raise cr.requests.Timeout("timed out")

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    monkeypatch.setattr(cr, "log_error_to_server", lambda msg: logged.setdefault('msg', msg))

    cr.export_to_api("K229", "Legion", [])

    assert 'Timeout' in logged['msg']


def test_export_to_api_does_not_log_on_success(monkeypatch):
    monkeypatch.setattr(cr.requests, "post", lambda url, json, timeout: _FakeResponse(200))
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    monkeypatch.setattr(cr, "log_error_to_server", lambda msg: (_ for _ in ()).throw(AssertionError("should not log on success")))

    result = cr.export_to_api("K229", "Legion", [])

    assert result == {"success": True, "count": 0}


def test_click_open_button_uses_passed_pause_range(monkeypatch):
    captured = {}

    def fake_uniform(lo, hi):
        captured["range"] = (lo, hi)
        return 0.0

    monkeypatch.setattr(cr.coord_manager, "to_screen_dialog", lambda x, y: (10, 10))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: (0, 0))
    monkeypatch.setattr(cr.random, "randint", lambda lo, hi: 0)
    monkeypatch.setattr(cr.random, "uniform", fake_uniform)
    monkeypatch.setattr(cr.pyautogui, "click", lambda *a, **k: None)
    monkeypatch.setattr(cr.time, "sleep", lambda *a, **k: None)

    cr.click_open_button(pause_range=(0.5, 0.6))

    assert captured["range"] == (0.5, 0.6)


def test_click_open_button_defaults_to_module_constant(monkeypatch):
    captured = {}

    def fake_uniform(lo, hi):
        captured["range"] = (lo, hi)
        return 0.0

    monkeypatch.setattr(cr.coord_manager, "to_screen_dialog", lambda x, y: (10, 10))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: (0, 0))
    monkeypatch.setattr(cr.random, "randint", lambda lo, hi: 0)
    monkeypatch.setattr(cr.random, "uniform", fake_uniform)
    monkeypatch.setattr(cr.pyautogui, "click", lambda *a, **k: None)
    monkeypatch.setattr(cr.time, "sleep", lambda *a, **k: None)

    cr.click_open_button()

    assert captured["range"] == cr.ANTI_DETECT_PAUSE_RANGE


def test_collect_chests_forwards_pause_range_to_click(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    captured_ranges = []

    def fake_grab_fullscreen():
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def fake_detect_dialog_bbox(frame):
        return (0, 0, 300, 300)

    def fake_crop_dialog(frame, bbox):
        return np.zeros((300, 300, 3), dtype=np.uint8)

    produced = {"n": 0}

    def fake_find_open_button(bbox, dialog):
        return (10, 10) if produced["n"] < 1 else None

    def fake_crop_top_row(frame):
        produced["n"] += 1
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def fake_ocr_top_row_crops(combined, full_lang=False):
        return ("Сундук Эпического Монстра", "Игрок")

    def fake_click_open_button(pause_range=cr.ANTI_DETECT_PAUSE_RANGE):
        captured_ranges.append(pause_range)

    monkeypatch.setattr(cr, "grab_fullscreen", fake_grab_fullscreen)
    monkeypatch.setattr(cr, "detect_dialog_bbox", fake_detect_dialog_bbox)
    monkeypatch.setattr(cr, "crop_dialog", fake_crop_dialog)
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "crop_top_row", fake_crop_top_row)
    monkeypatch.setattr(cr, "ocr_top_row_crops", fake_ocr_top_row_crops)
    monkeypatch.setattr(cr, "click_open_button", fake_click_open_button)

    cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir, pause_range=(0.5, 0.6))

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


def test_collect_chests_forwards_full_lang_to_ocr_top_row_crops(tmp_path, monkeypatch):
    """full_lang now reaches the background consumer's OCR call (ocr_top_row_crops),
    not read_top_row — the producer no longer OCRs anything itself."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    captured = {}

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))

    produced = {"n": 0}

    def fake_find_open_button(bbox, dialog):
        return (10, 10) if produced["n"] < 1 else None
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)

    def fake_crop_top_row(frame):
        produced["n"] += 1
        return np.zeros((10, 10, 3), dtype=np.uint8)
    monkeypatch.setattr(cr, "crop_top_row", fake_crop_top_row)

    def fake_ocr_top_row_crops(combined, full_lang=False):
        captured["full_lang"] = full_lang
        return ("Сундук", "Player")
    monkeypatch.setattr(cr, "ocr_top_row_crops", fake_ocr_top_row_crops)
    monkeypatch.setattr(cr, "click_open_button", lambda pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)

    cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir, full_lang=True)

    assert captured["full_lang"] is True


def test_chest_timestamps_unique_even_within_same_microsecond(monkeypatch):
    """Владелец 2026-09-26: бот считает АБСОЛЮТНО ВСЕ сундуки. Сервер склеивает записи с
    одинаковым (игрок, тип, время) — раньше время было с точностью до секунды, а фоновый
    OCR обрабатывает 2-3 сундука в секунду: два одинаковых сундука одного игрока подряд
    получали один ключ, и второй терялся на сервере (53 из 709 утром 26.09). Каждый
    сундук обязан получить своё, строго возрастающее время — даже если часы стоят."""
    frozen = datetime.datetime(2026, 9, 26, 10, 0, 0, 0)
    monkeypatch.setattr(cr, "_now", lambda: frozen)
    monkeypatch.setattr(cr, "_last_chest_ts", None)

    stamps = [cr._unique_chest_timestamp() for _ in range(5)]

    assert len(set(stamps)) == 5
    parsed = [datetime.datetime.fromisoformat(s) for s in stamps]
    assert parsed == sorted(parsed)
    assert all(p >= frozen for p in parsed)


def test_consumer_gives_identical_chests_distinct_timestamps(tmp_path, monkeypatch):
    """Два одинаковых сундука одного игрока, обработанные в одну секунду, должны остаться
    двумя разными записями — ключ (игрок, тип, время) у них различается."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    os.makedirs(pending_dir, exist_ok=True)
    for name in ("000001.png", "000002.png", "000003.png"):
        cv2.imwrite(os.path.join(pending_dir, name), np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda crop, full_lang=False: ("Склеп 25", "Jack"))
    frozen = datetime.datetime(2026, 9, 26, 10, 0, 0, 0)
    monkeypatch.setattr(cr, "_now", lambda: frozen)
    monkeypatch.setattr(cr, "_last_chest_ts", None)

    done = threading.Event()
    done.set()
    items = []
    cr._chest_consumer_loop(pending_dir, db_path, None, False, done, items)

    conn = cr.init_db(db_path)
    rows = conn.execute("SELECT raw_player_name, chest_type, timestamp FROM local_chests").fetchall()
    conn.close()
    assert len(rows) == 3
    assert len(set(rows)) == 3


# ── Одна база на ПК + клан в момент сбора (владелец 2026-09-26) ─────────────

def test_storage_dir_is_localappdata_for_any_copy_of_bot():
    """Исходники и exe раньше держали каждый свою базу рядом с модулем. Путь хранилища
    теперь зависит только от %LOCALAPPDATA%."""
    assert cr.resolve_storage_dir({"LOCALAPPDATA": r"C:\Users\X\AppData\Local"}) == \
        os.path.join(r"C:\Users\X\AppData\Local", "TotalHunter")


def test_storage_dir_without_localappdata_raises():
    import pytest
    with pytest.raises(RuntimeError):
        cr.resolve_storage_dir({})


def test_default_db_and_pending_live_in_storage_dir():
    assert os.path.dirname(cr.DB_PATH) == cr.STORAGE_DIR
    assert os.path.dirname(cr.PENDING_DIR) == cr.STORAGE_DIR


def test_init_db_creates_missing_dir(tmp_path):
    db_path = str(tmp_path / "new" / "chest_buffer.db")
    cr.init_db(db_path).close()
    assert os.path.exists(db_path)


def test_init_db_adds_pair_columns_to_old_table(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "chest_buffer.db")
    old = sqlite3.connect(db_path)
    old.execute("CREATE TABLE local_chests (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "raw_player_name TEXT, chest_type TEXT, timestamp TEXT, is_synced INTEGER DEFAULT 0)")
    old.execute("INSERT INTO local_chests (raw_player_name, chest_type, timestamp) VALUES ('A','T','ts')")
    old.commit(); old.close()

    conn = cr.init_db(db_path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(local_chests)")]
    rows = conn.execute("SELECT raw_player_name, kingdom, clan FROM local_chests").fetchall()
    conn.close()
    assert "kingdom" in cols and "clan" in cols
    assert rows == [("A", None, None)]


def test_migrate_legacy_storage_moves_unsent_and_removes_old_db(tmp_path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    legacy_db = str(legacy_dir / "chest_buffer.db")
    conn = cr.init_db(legacy_db)
    cr.insert_chest(conn, "Тип", "НеОтправлен", "2026-09-26T09:00:00", "229", "ELDORADO")
    conn.close()
    legacy_pending = legacy_dir / "chest_pending"
    legacy_pending.mkdir()
    cv2.imwrite(str(legacy_pending / "000003.png"), np.zeros((10, 10, 3), dtype=np.uint8))

    new_db = str(tmp_path / "store" / "chest_buffer.db")
    new_pending = str(tmp_path / "store" / "chest_pending")
    moved = cr.migrate_legacy_storage(str(legacy_dir), new_db, new_pending)

    assert moved == 1
    assert not os.path.exists(legacy_db)
    conn = cr.init_db(new_db)
    rows = conn.execute("SELECT raw_player_name, kingdom, clan FROM local_chests").fetchall()
    conn.close()
    assert rows == [("НеОтправлен", "229", "ELDORADO")]
    queue = cr._pending_queue(new_pending)
    assert len(queue) == 1
    # имя не совпадает ни с одним будущим NNNNNN.png producer'а и идёт первым в очереди
    assert os.path.basename(queue[0]) < "000001.png"
    assert not list(legacy_pending.glob("*.png"))


def test_migrate_legacy_storage_noop_when_same_place_or_absent(tmp_path):
    db = str(tmp_path / "chest_buffer.db")
    cr.init_db(db).close()
    assert cr.migrate_legacy_storage(str(tmp_path), db, str(tmp_path / "chest_pending")) == 0
    assert os.path.exists(db)
    assert cr.migrate_legacy_storage(str(tmp_path / "nothing"), db, str(tmp_path / "p")) == 0


def test_consumer_stores_pair_of_collection_time(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    os.makedirs(pending_dir, exist_ok=True)
    cv2.imwrite(os.path.join(pending_dir, "000001.png"), np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda crop, full_lang=False: ("Склеп", "Jack"))

    done = threading.Event()
    done.set()
    cr._chest_consumer_loop(pending_dir, db_path, None, False, done, [], "229", "Феникс")

    conn = cr.init_db(db_path)
    rows = conn.execute("SELECT raw_player_name, kingdom, clan FROM local_chests").fetchall()
    conn.close()
    assert rows == [("Jack", "229", "Феникс")]


def test_get_unsynced_by_pair_groups_and_uses_fallback_for_old_rows(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Т", "A", "t1", "229", "ELDORADO")
    cr.insert_chest(conn, "Т", "B", "t2", "229", "Феникс")
    cr.insert_chest(conn, "Т", "C", "t3", "229", "ELDORADO")
    cr.insert_chest(conn, "Т", "D", "t4")  # старая строка без пары
    groups = dict(cr.get_unsynced_by_pair(conn, "229", "ELDORADO"))
    conn.close()

    assert [r[1] for r in groups[("229", "ELDORADO")]] == ["A", "C", "D"]
    assert [r[1] for r in groups[("229", "Феникс")]] == ["B"]


# ── Аварийный перезапуск: кропы прошлого запуска не теряются и не меняют клан ──

def _patch_collect(monkeypatch, buttons):
    """buttons — сколько раз подряд «кнопка Открыть есть», дальше список кончился."""
    left = {"n": buttons}

    def fake_find(bbox, dialog):
        if left["n"] > 0:
            left["n"] -= 1
            return (10, 10)
        return None
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", fake_find)
    monkeypatch.setattr(cr, "crop_top_row", lambda frame: np.full((10, 10, 3), 7, dtype=np.uint8))
    monkeypatch.setattr(cr, "click_open_button", lambda pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)
    monkeypatch.setattr(cr.time, "sleep", lambda s: None)


def test_crop_names_unique_per_run_and_sorted_in_collection_order():
    a1, a2 = cr._crop_name("20260926114307000001", 1), cr._crop_name("20260926114307000001", 2)
    b1 = cr._crop_name("20260926120000000000", 1)
    assert len({a1, a2, b1}) == 3
    assert sorted([b1, a2, a1]) == [a1, a2, b1]
    assert "000000_legacy_000001.png" < a1  # перенесённые из старой базы — первыми


def test_leftover_crops_keep_their_run_pair_and_are_not_overwritten(tmp_path, monkeypatch):
    """Бот упал посреди сбора ELDORADO: 2 кропа остались в очереди. Следующий запуск —
    под Фениксом. Старые кропы обязаны уйти в ELDORADO, новые не должны их перезаписать."""
    db_path = str(tmp_path / "chest_buffer.db")
    pending_dir = str(tmp_path / "chest_pending")
    os.makedirs(pending_dir)
    old_run = "20260926100000000000"
    cr._write_run_pair(pending_dir, old_run, "229", "ELDORADO")
    for i in (1, 2):
        cv2.imwrite(os.path.join(pending_dir, cr._crop_name(old_run, i)),
                    np.full((10, 10, 3), i, dtype=np.uint8))

    seen = []

    def fake_ocr(crop, full_lang=False):
        seen.append(int(crop[0, 0, 0]))
        return ("Тип", f"P{len(seen)}")
    monkeypatch.setattr(cr, "ocr_top_row_crops", fake_ocr)
    _patch_collect(monkeypatch, buttons=2)

    cr.collect_chests(lambda: False, db_path=db_path, pending_dir=pending_dir,
                      kingdom="229", clan="Феникс")

    conn = cr.init_db(db_path)
    rows = conn.execute("SELECT kingdom, clan FROM local_chests ORDER BY id").fetchall()
    conn.close()
    assert sorted(seen[:2]) == [1, 2]          # оба старых кропа прочитаны, не перезаписаны
    assert len(rows) == 4
    assert rows.count(("229", "ELDORADO")) == 2
    assert rows.count(("229", "Феникс")) == 2
    assert os.listdir(pending_dir) == []       # очередь и файлы пар подчищены


def test_migrate_removes_empty_legacy_pending_dir(tmp_path):
    legacy = tmp_path / "legacy"
    (legacy / "chest_pending").mkdir(parents=True)
    cr.migrate_legacy_storage(str(legacy), str(tmp_path / "s" / "chest_buffer.db"),
                              str(tmp_path / "s" / "chest_pending"))
    assert not (legacy / "chest_pending").exists()
