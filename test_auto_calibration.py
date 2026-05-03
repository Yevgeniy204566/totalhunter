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
