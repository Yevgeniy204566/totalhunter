"""Unit tests for CoordinateManager — pure math, no screen."""
import pytest
from coord_manager import CoordinateManager, REF_A, REF_B


class TestCalibrate:
    def test_identity_at_reference_resolution(self):
        """Calibrating with ref coords gives scale 1.0 and anchor = REF_A."""
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        assert abs(cm.scale_x - 1.0) < 0.001
        assert abs(cm.scale_y - 1.0) < 0.001
        assert cm.anchor_x == REF_A[0]
        assert cm.anchor_y == REF_A[1]

    def test_half_resolution(self):
        """Game window at 960x540 gives scale ~0.5 on both axes."""
        cm = CoordinateManager()
        a_user = (REF_A[0] // 2, REF_A[1] // 2)
        b_user = (REF_B[0] // 2, REF_B[1] // 2)
        cm.calibrate(a_user, b_user)
        assert abs(cm.scale_x - 0.5) < 0.01
        assert abs(cm.scale_y - 0.5) < 0.01

    def test_asymmetric_scale(self):
        """Browser toolbars cause different X and Y scales."""
        cm = CoordinateManager()
        a_user = (int(REF_A[0] * 0.8), int(REF_A[1] * 0.7))
        b_user = (int(REF_B[0] * 0.8), int(REF_B[1] * 0.7))
        cm.calibrate(a_user, b_user)
        assert abs(cm.scale_x - 0.8) < 0.01
        assert abs(cm.scale_y - 0.7) < 0.01

    def test_anchor_set_to_a_user(self):
        cm = CoordinateManager()
        cm.calibrate((150, 800), (620, 40))
        assert cm.anchor_x == 150
        assert cm.anchor_y == 800


class TestToScreen:
    def test_identity_calibration_is_passthrough(self):
        """At reference resolution, to_screen returns original coords."""
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        assert cm.to_screen(689, 941) == (689, 941)
        assert cm.to_screen(1137, 777) == (1137, 777)

    def test_ref_a_maps_to_anchor(self):
        """REF_A always maps to user anchor regardless of scale."""
        cm = CoordinateManager()
        a_user = (150, 800)
        b_user = (int(REF_B[0] * 0.8), int(REF_B[1] * 0.8))
        cm.calibrate(a_user, b_user)
        x, y = cm.to_screen(REF_A[0], REF_A[1])
        assert x == a_user[0]
        assert y == a_user[1]

    def test_half_scale(self):
        """At 0.5 scale, coordinates halve."""
        cm = CoordinateManager()
        a_user = (REF_A[0] // 2, REF_A[1] // 2)
        b_user = (REF_B[0] // 2, REF_B[1] // 2)
        cm.calibrate(a_user, b_user)
        # REF_A maps to a_user exactly
        x, y = cm.to_screen(REF_A[0], REF_A[1])
        assert x == a_user[0]
        assert y == a_user[1]

    def test_returns_int_tuple(self):
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        result = cm.to_screen(100, 200)
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)


class TestToRegion:
    def test_identity_calibration(self):
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        assert cm.to_region(100, 200, 300, 50) == (100, 200, 300, 50)

    def test_scales_width_and_height(self):
        cm = CoordinateManager()
        a_user = (REF_A[0] // 2, REF_A[1] // 2)
        b_user = (REF_B[0] // 2, REF_B[1] // 2)
        cm.calibrate(a_user, b_user)
        x, y, w, h = cm.to_region(200, 400, 100, 50)
        assert w == 50
        assert h == 25

    def test_height_always_positive(self):
        """scale_y is negative (B is above A), but region height must be positive."""
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        x, y, w, h = cm.to_region(100, 200, 200, 80)
        assert h > 0
        assert w > 0


class TestSaveLoad:
    def test_round_trip(self, tmp_path):
        cm = CoordinateManager()
        cm.calibrate((100, 800), (600, 50))
        path = str(tmp_path / "profile_test.json")
        cm.save(path)

        cm2 = CoordinateManager()
        cm2.load(path)
        assert cm2.anchor_x == 100
        assert cm2.anchor_y == 800
        assert abs(cm2.scale_x - cm.scale_x) < 0.001
        assert abs(cm2.scale_y - cm.scale_y) < 0.001

    def test_to_screen_consistent_after_load(self, tmp_path):
        cm = CoordinateManager()
        cm.calibrate((100, 800), (600, 50))
        path = str(tmp_path / "profile_test.json")
        cm.save(path)

        cm2 = CoordinateManager()
        cm2.load(path)
        assert cm2.to_screen(689, 941) == cm.to_screen(689, 941)

    def test_load_missing_file_raises(self):
        cm = CoordinateManager()
        with pytest.raises(FileNotFoundError):
            cm.load("/nonexistent/path.json")
