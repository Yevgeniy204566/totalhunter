import tkinter as tk
from unittest.mock import patch
import calibration_ui
from coord_manager import REF_A, REF_B


def test_run_calibration_passes_start_a_to_point_dialog(monkeypatch):
    """Когда start_a передан — лупа открывается на start_a, не на REF_A."""
    calls = []

    def fake_calibrate_one(root, start_pos, label_text):
        calls.append(start_pos)
        return start_pos  # симулируем нажатие «Зафиксировать»

    monkeypatch.setattr(calibration_ui, "_calibrate_one_point", fake_calibrate_one)

    root = tk.Tk()
    root.withdraw()
    try:
        pa, pb = calibration_ui.run_calibration(
            parent=root, start_a=(111, 222), start_b=(333, 444)
        )
    finally:
        root.destroy()

    assert calls[0] == (111, 222), f"Point A start: expected (111,222), got {calls[0]}"
    assert calls[1] == (333, 444), f"Point B start: expected (333,444), got {calls[1]}"
    assert pa == (111, 222)
    assert pb == (333, 444)


def test_run_calibration_defaults_to_ref_when_no_start(monkeypatch):
    """Без start_a/start_b используются REF_A / REF_B."""
    calls = []

    def fake_calibrate_one(root, start_pos, label_text):
        calls.append(start_pos)
        return start_pos

    monkeypatch.setattr(calibration_ui, "_calibrate_one_point", fake_calibrate_one)

    root = tk.Tk()
    root.withdraw()
    try:
        calibration_ui.run_calibration(parent=root)
    finally:
        root.destroy()

    assert calls[0] == REF_A
    assert calls[1] == REF_B


import cv2
import numpy as np
from auto_calibration import scale_ref, detect_point_a_in_region


def test_scale_ref_identity_1920x1080():
    assert scale_ref(REF_A, 1920, 1080) == REF_A
    assert scale_ref(REF_B, 1920, 1080) == REF_B


def test_scale_ref_double_resolution():
    a = scale_ref(REF_A, 3840, 2160)
    assert a == (REF_A[0] * 2, REF_A[1] * 2)


def test_scale_ref_non_integer_rounds_down():
    a = scale_ref((90, 925), 2560, 1440)
    assert a == (120, int(925 * 1440 / 1080))


def test_detect_point_a_finds_white_rectangle():
    """Synthetic image: dark background + white rectangle."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (80, 100), (180, 200), (255, 255, 255), 3)
    result = detect_point_a_in_region(img)
    assert result is not None
    cx, cy = result
    assert abs(cx - 130) <= 10, f"Expected cx≈130, got {cx}"
    assert abs(cy - 150) <= 10, f"Expected cy≈150, got {cy}"


def test_detect_point_a_returns_none_when_no_rect():
    """Completely dark image — no rectangle found."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    assert detect_point_a_in_region(img) is None


def test_detect_point_a_ignores_small_contours():
    """Small rectangle (< 500 px²) is ignored."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (148, 148), (152, 152), (255, 255, 255), 1)  # ~16 px²
    assert detect_point_a_in_region(img) is None
