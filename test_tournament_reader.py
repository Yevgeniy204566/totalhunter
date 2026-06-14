import os
import json
import pytest
import cv2
import numpy as np
import tournament_reader as tr


def test_load_config_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tr, "CONFIG_PATH", os.path.join(str(tmp_path), "tournament_config.json"))
    with pytest.raises(FileNotFoundError) as exc_info:
        tr.load_config()
    assert "tournament_config.example.json" in str(exc_info.value)


def test_load_config_missing_keys_raises(tmp_path, monkeypatch):
    config_path = os.path.join(str(tmp_path), "tournament_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"api_url": "https://api.total-hunter.com"}, f)
    monkeypatch.setattr(tr, "CONFIG_PATH", config_path)
    with pytest.raises(ValueError) as exc_info:
        tr.load_config()
    assert "api_token" in str(exc_info.value)


def test_load_config_valid(tmp_path, monkeypatch):
    config_path = os.path.join(str(tmp_path), "tournament_config.json")
    data = {
        "api_url": "https://api.total-hunter.com",
        "api_token": "secret123",
        "alliance_tag": "K229",
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    monkeypatch.setattr(tr, "CONFIG_PATH", config_path)
    result = tr.load_config()
    assert result == data


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


def test_compute_places_first_frame():
    rows = [('Alice', 100), ('Bob', 90), ('Carl', 80)]
    places = tr.compute_places(rows, known_places={})
    assert places == {1: ('Alice', 100), 2: ('Bob', 90), 3: ('Carl', 80)}


def test_compute_places_anchor_offset():
    known = {1: ('Alice', 100), 2: ('Bob', 90), 3: ('Carl', 80)}
    # New frame scrolled down by 1: Bob is now at index 0, Carl at index 1, Dave (new) at index 2
    rows = [('Bob', 90), ('Carl', 80), ('Dave', 70)]
    places = tr.compute_places(rows, known_places=known)
    assert places == {2: ('Bob', 90), 3: ('Carl', 80), 4: ('Dave', 70)}


def test_compute_places_no_anchor_returns_none():
    known = {1: ('Alice', 100), 2: ('Bob', 90)}
    rows = [('Zara', 999), ('Yara', 998)]
    places = tr.compute_places(rows, known_places=known)
    assert places is None


def test_is_end_of_list_identical_frames():
    dialog = np.full((546, 766, 3), 200, dtype=np.uint8)
    assert tr.is_end_of_list(dialog, dialog) is True


def test_is_end_of_list_different_text_area():
    prev = np.full((546, 766, 3), 200, dtype=np.uint8)
    curr = prev.copy()
    # change pixels in the text area (not scrollbar, not own row)
    curr[100:110, 100:110] = 50
    assert tr.is_end_of_list(prev, curr) is False


def test_is_end_of_list_ignores_scrollbar_and_own_row():
    prev = np.full((546, 766, 3), 200, dtype=np.uint8)
    curr = prev.copy()
    h, w = curr.shape[:2]
    # change only the scrollbar strip (rightmost 5%)
    scrollbar_x0 = int(w * (1 - tr.SCROLLBAR_FRAC))
    curr[:, scrollbar_x0:] = 50
    # change only the own-row strip (bottom from OWN_ROW_Y_FRAC[0])
    own_y0 = int(h * tr.OWN_ROW_Y_FRAC[0])
    curr[own_y0:, :] = 50
    assert tr.is_end_of_list(prev, curr) is True
