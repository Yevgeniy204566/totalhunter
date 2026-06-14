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
