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


from auto_calibration import detect_point_b_from_diff


def test_detect_point_b_finds_plus_shape():
    """Synthetic hover: yellow-green blocky + appears at center."""
    baseline = np.zeros((300, 300, 3), dtype=np.uint8)
    hover = baseline.copy()
    cv2.rectangle(hover, (130, 110), (170, 190), (50, 200, 100), -1)  # vertical bar
    cv2.rectangle(hover, (110, 130), (190, 170), (50, 200, 100), -1)  # horizontal bar
    result = detect_point_b_from_diff(baseline, hover)
    assert result is not None
    cx, cy = result
    assert abs(cx - 150) <= 15, f"Expected cx≈150, got {cx}"
    assert abs(cy - 150) <= 15, f"Expected cy≈150, got {cy}"


def test_detect_point_b_returns_none_when_no_diff():
    """Identical screenshots — nothing appeared."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    assert detect_point_b_from_diff(img, img) is None


def test_detect_point_b_ignores_small_diff():
    """Less than 100 new pixels — noise, not a crosshair."""
    baseline = np.zeros((300, 300, 3), dtype=np.uint8)
    hover = baseline.copy()
    hover[100:103, 100:103] = (255, 255, 255)  # 9 pixels
    assert detect_point_b_from_diff(baseline, hover) is None


from unittest.mock import patch
from auto_calibration import auto_detect_points


def test_auto_detect_points_fallback_when_nothing_found():
    """Blank screenshots → both detectors return None → fallback to scaled REF."""
    blank = np.zeros((300, 300, 3), dtype=np.uint8)
    with patch("auto_calibration._grab_region", return_value=(blank, 0, 0)), \
         patch("auto_calibration.pyautogui"), \
         patch("auto_calibration.time"):
        pa, pb = auto_detect_points(1920, 1080)
    assert pa == REF_A
    assert pb == REF_B


def test_auto_detect_points_returns_screen_coords_when_found():
    """Detectors find points → return screen coordinates, not image coordinates."""
    blank = np.zeros((300, 300, 3), dtype=np.uint8)

    # Point A: white rectangle centered near (155, 150) in image
    img_a = blank.copy()
    cv2.rectangle(img_a, (130, 120), (180, 180), (255, 255, 255), 3)

    # Point B: hover with blocky + centered near (150, 150) in image
    img_b_hover = blank.copy()
    cv2.rectangle(img_b_hover, (130, 110), (170, 190), (50, 200, 100), -1)
    cv2.rectangle(img_b_hover, (110, 130), (190, 170), (50, 200, 100), -1)

    # For 1920x1080: a_cx=90, a_cy=925, b_cx=1149, b_cy=88
    # a: x1=max(0,90-150)=0, y1=max(0,925-150)=775
    # b: x1=max(0,1149-150)=999, y1=max(0,88-150)=0
    grab_responses = iter([
        (img_a, 0, 775),       # Point A grab
        (blank, 999, 0),       # Point B baseline
        (img_b_hover, 999, 0), # Point B hover
    ])

    with patch("auto_calibration._grab_region", side_effect=lambda *a, **kw: next(grab_responses)), \
         patch("auto_calibration.pyautogui"), \
         patch("auto_calibration.time"):
        pa, pb = auto_detect_points(1920, 1080)

    # Point A: img center from cv2.rectangle(img_a, (130,120),(180,180)) → cx≈155, cy≈150
    # screen: x1=0 + 155=155, y1=775 + 150=925
    assert abs(pa[0] - 155) <= 10
    assert abs(pa[1] - 925) <= 10

    # Point B: img center ≈ (150,150), x1=999, y1=0 → screen ≈ (1149, 150)
    assert abs(pb[0] - (999 + 150)) <= 15
    assert abs(pb[1] - (0 + 150)) <= 15
