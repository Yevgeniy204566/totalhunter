"""Tests for the Click Tuning (D-Pad) system.

ui_offsets stores per-button (dx, dy) corrections applied on top of
the base calibration to compensate for non-standard TV / windowed modes.
"""
import json
import pytest
from coord_manager import CoordinateManager, REF_A, REF_B

KNOWN_BUTTONS = {"wt_icon", "carter", "top_accel", "march_accel"}


class TestUiOffsetsDefaults:
    def test_all_four_buttons_present_after_init(self):
        cm = CoordinateManager()
        assert KNOWN_BUTTONS == set(cm.ui_offsets.keys())

    def test_all_offsets_zero_on_fresh_instance(self):
        cm = CoordinateManager()
        for name in KNOWN_BUTTONS:
            assert cm.ui_offsets[name] == [0, 0]

    def test_get_ui_offset_returns_int_tuple(self):
        cm = CoordinateManager()
        dx, dy = cm.get_ui_offset("carter")
        assert isinstance(dx, int)
        assert isinstance(dy, int)

    def test_get_ui_offset_default_is_zero_zero(self):
        cm = CoordinateManager()
        assert cm.get_ui_offset("wt_icon") == (0, 0)

    def test_get_ui_offset_unknown_key_returns_zero_zero(self):
        """Unknown button names must not crash — silently return (0, 0)."""
        cm = CoordinateManager()
        assert cm.get_ui_offset("nonexistent_button") == (0, 0)


class TestSetUiOffset:
    def test_set_and_get_positive_values(self):
        cm = CoordinateManager()
        cm.set_ui_offset("carter", 12, -5)
        assert cm.get_ui_offset("carter") == (12, -5)

    def test_set_negative_x_offset(self):
        cm = CoordinateManager()
        cm.set_ui_offset("march_accel", -20, 0)
        assert cm.get_ui_offset("march_accel") == (-20, 0)

    def test_set_does_not_affect_other_buttons(self):
        cm = CoordinateManager()
        cm.set_ui_offset("carter", 10, 10)
        assert cm.get_ui_offset("wt_icon") == (0, 0)
        assert cm.get_ui_offset("top_accel") == (0, 0)
        assert cm.get_ui_offset("march_accel") == (0, 0)

    def test_set_unknown_key_is_ignored(self):
        """Setting an unknown key must not crash or add spurious entries."""
        cm = CoordinateManager()
        cm.set_ui_offset("garbage", 5, 5)
        assert "garbage" not in cm.ui_offsets

    def test_overwrite_existing_offset(self):
        cm = CoordinateManager()
        cm.set_ui_offset("wt_icon", 3, 7)
        cm.set_ui_offset("wt_icon", -1, -2)
        assert cm.get_ui_offset("wt_icon") == (-1, -2)


class TestSaveLoadUiOffsets:
    def test_round_trip_saves_and_restores_offsets(self, tmp_path):
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        cm.set_ui_offset("carter", 12, -5)
        cm.set_ui_offset("march_accel", -20, 3)
        path = str(tmp_path / "profile.json")
        cm.save(path)

        cm2 = CoordinateManager()
        cm2.load(path)
        assert cm2.get_ui_offset("carter") == (12, -5)
        assert cm2.get_ui_offset("march_accel") == (-20, 3)

    def test_ui_offsets_key_in_saved_json(self, tmp_path):
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        path = str(tmp_path / "profile.json")
        cm.save(path)

        with open(path) as f:
            data = json.load(f)
        assert "ui_offsets" in data

    def test_load_profile_without_ui_offsets_defaults_to_zero(self, tmp_path):
        """Old profiles (pre-tuning) must load without error — offsets stay 0."""
        old_profile = {
            "point_a": list(REF_A),
            "point_b": list(REF_B),
            "scale_x": 1.0,
            "scale_y": 1.0,
            "dialog_offset_x": 0,
            "dialog_offset_y": 0,
        }
        path = str(tmp_path / "old_profile.json")
        with open(path, "w") as f:
            json.dump(old_profile, f)

        cm = CoordinateManager()
        cm.load(path)
        for name in KNOWN_BUTTONS:
            assert cm.get_ui_offset(name) == (0, 0)

    def test_load_profile_with_partial_ui_offsets(self, tmp_path):
        """Profile with only some keys in ui_offsets — rest default to 0."""
        profile = {
            "point_a": list(REF_A),
            "point_b": list(REF_B),
            "scale_x": 1.0,
            "scale_y": 1.0,
            "dialog_offset_x": 0,
            "dialog_offset_y": 0,
            "ui_offsets": {"carter": [7, -3]},
        }
        path = str(tmp_path / "partial.json")
        with open(path, "w") as f:
            json.dump(profile, f)

        cm = CoordinateManager()
        cm.load(path)
        assert cm.get_ui_offset("carter") == (7, -3)
        assert cm.get_ui_offset("wt_icon") == (0, 0)

    def test_other_calibration_data_survives_save_with_offsets(self, tmp_path):
        """Saving ui_offsets must not corrupt existing calibration data."""
        cm = CoordinateManager()
        cm.calibrate((100, 800), (600, 50))
        cm.dialog_offset_y = 85
        cm.set_ui_offset("carter", 5, -3)
        path = str(tmp_path / "profile.json")
        cm.save(path)

        cm2 = CoordinateManager()
        cm2.load(path)
        assert cm2.anchor_x == 100
        assert cm2.dialog_offset_y == 85
        assert cm2.get_ui_offset("carter") == (5, -3)


class TestOffsetApplication:
    def test_offset_adds_to_base_coordinate(self):
        """The caller adds offset to whatever base function returns."""
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        cm.set_ui_offset("carter", 12, -5)

        base_x, base_y = cm.to_screen_dialog(1137, 785)
        ox, oy = cm.get_ui_offset("carter")
        assert (base_x + ox, base_y + oy) == (base_x + 12, base_y - 5)

    def test_zero_offset_leaves_coordinate_unchanged(self):
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        base = cm.to_screen(693, 949)
        ox, oy = cm.get_ui_offset("wt_icon")
        assert (base[0] + ox, base[1] + oy) == base
