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
