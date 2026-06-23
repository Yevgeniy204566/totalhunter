import json
import cv2
import numpy as np
import tournament_reader as tr


def _load_fixture():
    return cv2.imdecode(np.fromfile("Турнир.png", dtype=np.uint8), cv2.IMREAD_COLOR)


def test_detect_dialog_bbox():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    assert bbox == (578, 268, 766, 546)


def test_crop_dialog():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    assert dialog.shape[:2] == (546, 766)


class _FakeShot:
    def __init__(self, bgra):
        self.bgra = bgra
        self.size = (bgra.shape[1], bgra.shape[0])

    def __array__(self):
        return self.bgra


class _FakeSct:
    def __init__(self, bgra):
        self._bgra = bgra
        self.monitors = [None, {"left": 0, "top": 0, "width": bgra.shape[1], "height": bgra.shape[0]}]

    def grab(self, monitor):
        return _FakeShot(self._bgra)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_grab_fullscreen(monkeypatch):
    frame = _load_fixture()
    bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
    monkeypatch.setattr(tr.mss, "mss", lambda: _FakeSct(bgra))
    result = tr.grab_fullscreen()
    assert np.array_equal(result, frame)


def test_detect_row_pitch():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    assert (pitch, row_top) == (100, 12)


def test_get_row_crops():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    rows = tr.get_row_crops(dialog, pitch, row_top)
    assert len(rows) == tr.NUM_VISIBLE_ROWS
    for name_roi, pts_roi in rows:
        assert name_roi.shape[0] > 0 and name_roi.shape[1] > 0
        assert pts_roi.shape[0] > 0 and pts_roi.shape[1] > 0


def test_ocr_text_row0_points_contains_digits():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    rows = tr.get_row_crops(dialog, pitch, row_top)
    _, pts_roi = rows[0]
    text = tr.ocr_text(pts_roi, threshold=tr.OCR_THRESHOLD)
    assert '488' in text
    assert '644' in text
    assert '262' in text


def test_clean_name_strips_tag_and_badge():
    assert tr.clean_name("[K229] Scaramouche 22") == "Scaramouche"
    assert tr.clean_name("[k229] МазаФака ZY") == "МазаФака"
    assert tr.clean_name("[K229] Yuki ay") == "Yuki"
    assert tr.clean_name("[K229] VikTor 2") == "VikTor"


def test_clean_name_no_tag():
    assert tr.clean_name("ЗОЛОТОЙ") == "ЗОЛОТОЙ"


def test_clean_name_strips_trailing_artifact_char():
    # background-noise artifacts (',  `, ?) glued to the name without a
    # space - seen in live test 4 (Evgeniuss', Jack', Berserk', Моралас`)
    assert tr.clean_name("Evgeniuss’") == "Evgeniuss"
    assert tr.clean_name("Jack’") == "Jack"
    assert tr.clean_name("Berserk’") == "Berserk"
    assert tr.clean_name("Моралас`") == "Моралас"
    assert tr.clean_name("ум?") == "ум"


def test_clean_points_strips_non_digits():
    assert tr.clean_points("488 644 262 очки") == 488644262
    assert tr.clean_points("71 896 730") == 71896730


def test_clean_points_empty_returns_none():
    assert tr.clean_points("очки") is None
    assert tr.clean_points("") is None


def test_ocr_row_all_visible_rows():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    rows = tr.get_row_crops(dialog, pitch, row_top)

    expected_names = ['Scaramouche', 'МазаФака', 'Yuki', 'VikTor']
    expected_points = [488644262, 315634592, 301084730, 300471402]

    for i, (name_roi, pts_roi) in enumerate(rows):
        name, points = tr.ocr_row(name_roi, pts_roi)
        assert name == expected_names[i]
        assert points == expected_points[i]


def test_ocr_own_row():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    own_row = tr.get_own_row(dialog)
    place_roi, name_roi, pts_roi = tr.get_own_row_crops(own_row)
    result = tr.ocr_own_row(place_roi, name_roi, pts_roi)
    assert result == {'rank': 79, 'name': 'ЗОЛОТОЙ', 'points': 71896730}


def test_ocr_name_otsu_aeon():
    img = cv2.imdecode(np.fromfile("name_crop_aeon.png", dtype=np.uint8), cv2.IMREAD_COLOR)
    # Otsu picks a per-ROI threshold; tesseract still misreads AEON as AEGON
    assert tr.ocr_name(img) == "AEGON"


def test_ocr_name_otsu_gigabyte():
    img = cv2.imdecode(np.fromfile("name_crop_gigabyte.png", dtype=np.uint8), cv2.IMREAD_COLOR)
    assert tr.ocr_name(img) == "Gigabyte"


def _load_debug_crop(rank):
    return cv2.imdecode(np.fromfile(f"debug_name_crops/rank_{rank:02d}.png", dtype=np.uint8), cv2.IMREAD_COLOR)


def test_ocr_name_otsu_pattern_b_dark_shadow():
    # rank 4: all 4 fixed thresholds returned '' despite readable "Dark Shadow"
    img = _load_debug_crop(4)
    assert tr.ocr_name(img) == "Dark Shadow"


def test_ocr_name_otsu_pattern_b_ayar_md():
    # rank 11: all 4 fixed thresholds returned '' despite readable "AYAR MD"
    img = _load_debug_crop(11)
    assert tr.ocr_name(img) == "AYAR MD"


def test_ocr_name_otsu_pattern_b_lord():
    # rank 31: all 4 fixed thresholds returned '' despite readable "Lord"
    img = _load_debug_crop(31)
    assert tr.ocr_name(img) == "Lord"


def test_ocr_name_otsu_pattern_b_mikajar():
    # rank 35: all 4 fixed thresholds returned '' despite readable "Mikajar"
    img = _load_debug_crop(35)
    assert tr.ocr_name(img) == "Mikajar"


def test_measure_scroll_shift_identical_frames_returns_zero():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)

    shift = tr.measure_scroll_shift(dialog, dialog, pitch, row_top)
    assert shift == 0


def test_measure_scroll_shift_detects_pixel_shift():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)

    shift_amount = 20
    shifted = np.zeros_like(dialog)
    shifted[:-shift_amount, :] = dialog[shift_amount:, :]
    shifted[-shift_amount:, :] = dialog[-1, :]

    shift = tr.measure_scroll_shift(dialog, shifted, pitch, row_top)
    assert shift == shift_amount


def test_collect_tournament_data(monkeypatch):
    frame = _load_fixture()

    monkeypatch.setattr(tr, "grab_fullscreen", lambda: frame)
    monkeypatch.setattr(tr.pyautogui, "scroll", lambda *a, **k: None)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(tr.random, "uniform", lambda a, b: 0)

    result = tr.collect_tournament_data()

    leaderboard = result['leaderboard']
    assert [row['rank'] for row in leaderboard] == [1, 2, 3, 4]
    assert [row['name'] for row in leaderboard] == ['Scaramouche', 'МазаФака', 'Yuki', 'VikTor']
    assert [row['points'] for row in leaderboard] == [488644262, 315634592, 301084730, 300471402]

    assert result['own_data'] == {'rank': 79, 'name': 'ЗОЛОТОЙ', 'points': 71896730}


def test_collect_tournament_data_handles_missing_pitch(monkeypatch):
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    real_pitch, real_row_top = tr.detect_row_pitch(dialog)

    monkeypatch.setattr(tr, "grab_fullscreen", lambda: frame)
    monkeypatch.setattr(tr.pyautogui, "scroll", lambda *a, **k: None)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(tr.random, "uniform", lambda a, b: 0)

    # first call returns no pitch (must not crash, just counts as stagnation);
    # subsequent calls return the real pitch
    pitch_results = [(None, None)]
    monkeypatch.setattr(
        tr, "detect_row_pitch",
        lambda d: pitch_results.pop(0) if pitch_results else (real_pitch, real_row_top),
    )

    result = tr.collect_tournament_data()

    assert 'leaderboard' in result
    assert 'own_data' in result


def test_collect_tournament_data_stops_after_zero_shifts(monkeypatch):
    frame = _load_fixture()

    monkeypatch.setattr(tr, "grab_fullscreen", lambda: frame)
    monkeypatch.setattr(tr.pyautogui, "scroll", lambda *a, **k: None)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(tr.random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(tr, "measure_scroll_shift", lambda *a, **k: 0)

    result = tr.collect_tournament_data()

    leaderboard = result['leaderboard']
    assert [row['rank'] for row in leaderboard] == [1, 2, 3, 4]
    assert [row['name'] for row in leaderboard] == ['Scaramouche', 'МазаФака', 'Yuki', 'VikTor']


def test_collect_tournament_data_accumulates_partial_row_shifts(monkeypatch):
    frame = _load_fixture()

    monkeypatch.setattr(tr, "grab_fullscreen", lambda: frame)
    monkeypatch.setattr(tr.pyautogui, "scroll", lambda *a, **k: None)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(tr.random, "uniform", lambda a, b: 0)

    # pitch == 100 for this fixture (see test_detect_row_pitch). Two 50px
    # shifts accumulate to one full row before the 2 zero-shifts end the loop.
    shifts = iter([50, 50, 0, 0])
    monkeypatch.setattr(tr, "measure_scroll_shift", lambda *a, **k: next(shifts))

    result = tr.collect_tournament_data()

    leaderboard = result['leaderboard']
    assert [row['rank'] for row in leaderboard] == [1, 2, 3, 4, 5]
    assert leaderboard[4]['name'] == 'VikTor'
    assert leaderboard[4]['points'] == 300471402


def test_anti_afk_click_targets_dialog_header(monkeypatch):
    clicks = []
    monkeypatch.setattr(tr.pyautogui, "click", lambda x, y: clicks.append((x, y)))
    monkeypatch.setattr(tr.random, "randint", lambda a, b: 0)

    tr.anti_afk_click((100, 200, 800, 600))

    assert clicks == [(100 + 800 // 2, 200 + int(600 * tr.ANTI_AFK_HEADER_Y_FRAC))]


def test_collect_tournament_data_anti_afk_triggers_after_interval(monkeypatch):
    frame = _load_fixture()

    monkeypatch.setattr(tr, "grab_fullscreen", lambda: frame)
    monkeypatch.setattr(tr.pyautogui, "scroll", lambda *a, **k: None)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(tr.random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(tr, "measure_scroll_shift", lambda *a, **k: 0)

    afk_calls = []
    monkeypatch.setattr(tr, "anti_afk_click", lambda bbox: afk_calls.append(bbox))

    # 2 iterations run before END_OF_LIST_ZERO_SHIFTS stops the loop; make
    # ANTI_AFK_INTERVAL_SEC appear to have elapsed before each one.
    times = iter([0, 1000, 2000, 3000, 4000, 5000])
    monkeypatch.setattr(tr.time, "time", lambda: next(times, 5000))

    tr.collect_tournament_data()

    assert len(afk_calls) >= 1


def test_collect_tournament_data_no_anti_afk_when_recent(monkeypatch):
    frame = _load_fixture()

    monkeypatch.setattr(tr, "grab_fullscreen", lambda: frame)
    monkeypatch.setattr(tr.pyautogui, "scroll", lambda *a, **k: None)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(tr.random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(tr, "measure_scroll_shift", lambda *a, **k: 0)

    afk_calls = []
    monkeypatch.setattr(tr, "anti_afk_click", lambda bbox: afk_calls.append(bbox))
    monkeypatch.setattr(tr.time, "time", lambda: 0)

    tr.collect_tournament_data()

    assert afk_calls == []


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_export_to_api_success(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured['url'] = url
        captured['json'] = json
        return _FakeResponse(200)

    monkeypatch.setattr(tr.requests, "post", fake_post)
    monkeypatch.setattr(tr, "get_hwid", lambda: "abc123hwid")

    data = {
        "leaderboard": [{"rank": 1, "name": "Scaramouche", "points": 488644262}],
        "own_data": {"rank": 79, "name": "ЗОЛОТОЙ", "points": 71896730},
    }

    result = tr.export_to_api("K229", "BERS", data, event_timestamp="2026-06-14T21:30:00")

    assert result is True
    assert captured['url'] == tr.SERVER_URL + "/api/v1/tournaments/import"
    assert captured['json'] == {
        "hwid": "abc123hwid",
        "kingdom": "K229",
        "clan": "BERS",
        "timestamp": "2026-06-14T21:30:00",
        "items": [
            {"name": "Scaramouche", "place": 1, "points": 488644262},
            {"name": "ЗОЛОТОЙ", "place": 79, "points": 71896730},
        ],
    }


def test_export_to_api_failure_writes_local_fallback(monkeypatch, tmp_path):
    def fake_post(url, json=None, timeout=None):
        return _FakeResponse(500)

    monkeypatch.setattr(tr.requests, "post", fake_post)
    monkeypatch.setattr(tr, "get_hwid", lambda: "abc123hwid")
    monkeypatch.chdir(tmp_path)

    data = {
        "leaderboard": [{"rank": 1, "name": "Scaramouche", "points": 488644262}],
        "own_data": {"rank": 79, "name": "ЗОЛОТОЙ", "points": 71896730},
    }

    result = tr.export_to_api("K229", "BERS", data, event_timestamp="2026-06-14T21:30:00")

    assert result is False
    files = list(tmp_path.glob("tournament_export_*.json"))
    assert len(files) == 1
    with open(files[0], encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["kingdom"] == "K229"
    assert saved["clan"] == "BERS"
    assert saved["items"][0] == {"name": "Scaramouche", "place": 1, "points": 488644262}


def test_main_smoke(monkeypatch):
    collected = {
        "leaderboard": [{"rank": 1, "name": "Scaramouche", "points": 488644262}],
        "own_data": {"rank": 79, "name": "ЗОЛОТОЙ", "points": 71896730},
    }

    monkeypatch.setattr(tr.sys, "argv", ["tournament_reader.py", "K229", "BERS"])
    monkeypatch.setattr(tr, "collect_tournament_data", lambda: collected)
    monkeypatch.setattr(tr, "export_to_api", lambda kingdom, clan, data, event_timestamp: True)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)

    tr.main()
