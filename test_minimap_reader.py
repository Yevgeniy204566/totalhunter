"""
TDD tests for minimap_reader.py

Synthetic minimap images are created with numpy to simulate:
  - WATER_BGR: (180, 100, 50) — blue-dominant, matches WATER_HSV and BGR check
  - LAND_BGR:  (50, 160, 80)  — green-dominant, matches LAND_HSV H≈52

Tests verify:
  1. detect_coast_angle()  — PCA on water/land boundary → angle in radians
  2. analyze_forward_zone() — cone mask, land_ratio, ocean vs river detection
"""
import numpy as np
import pytest
from minimap_reader import detect_coast_angle, analyze_forward_zone

MINIMAP_SIZE = 180

# Blue-dominant: B=180, G=100, R=50 → HSV H≈108 → inside WATER_HSV (100-140)
WATER_BGR = np.array([180, 100, 50], dtype=np.uint8)

# Green-dominant: B=50, G=160, R=80 → HSV H≈52 → inside LAND_HSV (5-95)
LAND_BGR = np.array([50, 160, 80], dtype=np.uint8)


# ── synthetic minimap factory ──────────────────────────────────────────────

def make_minimap(pattern: str) -> np.ndarray:
    """Create a 180×180 BGR minimap for testing."""
    img = np.zeros((MINIMAP_SIZE, MINIMAP_SIZE, 3), dtype=np.uint8)

    if pattern == 'water_left':
        # Left half water, right half land → vertical coastline → angle ≈ ±π/2
        img[:, :90] = WATER_BGR
        img[:, 90:] = LAND_BGR

    elif pattern == 'water_top':
        # Top half water, bottom half land → horizontal coastline → angle ≈ 0 or ±π
        img[:90, :] = WATER_BGR
        img[90:, :] = LAND_BGR

    elif pattern == 'water_diagonal':
        # Diagonal coastline at 45° → angle ≈ ±π/4
        for y in range(MINIMAP_SIZE):
            for x in range(MINIMAP_SIZE):
                img[y, x] = WATER_BGR if (x + y) < MINIMAP_SIZE else LAND_BGR

    elif pattern == 'all_water':
        # Solid ocean — no land anywhere
        img[:] = WATER_BGR

    elif pattern == 'all_land':
        # Solid land — no water
        img[:] = LAND_BGR

    elif pattern == 'water_with_islands':
        # Water with ~10% scattered land pixels — simulates internal water / river
        img[:] = WATER_BGR
        rng = np.random.default_rng(42)
        n = int(MINIMAP_SIZE * MINIMAP_SIZE * 0.10)
        ys = rng.integers(0, MINIMAP_SIZE, size=n)
        xs = rng.integers(0, MINIMAP_SIZE, size=n)
        img[ys, xs] = LAND_BGR

    return img


# ── detect_coast_angle ─────────────────────────────────────────────────────

class TestDetectCoastAngle:
    def test_returns_float(self):
        angle = detect_coast_angle(make_minimap('water_left'))
        assert isinstance(angle, float)

    def test_vertical_coast_angle_near_pi_over_2(self):
        # Water left / land right → coast runs vertically → angle ≈ ±π/2
        angle = detect_coast_angle(make_minimap('water_left'))
        deviation = abs(abs(angle) - np.pi / 2)
        assert deviation < 0.35, f"Expected ~±π/2 (90°), got {np.degrees(angle):.1f}°"

    def test_horizontal_coast_angle_near_zero_or_pi(self):
        # Water top / land bottom → coast runs horizontally → angle ≈ 0 or ±π
        angle = detect_coast_angle(make_minimap('water_top'))
        near_zero = abs(angle) < 0.35
        near_pi   = abs(abs(angle) - np.pi) < 0.35
        assert near_zero or near_pi, (
            f"Expected ~0° or ~±180°, got {np.degrees(angle):.1f}°"
        )

    def test_diagonal_coast_angle_near_45_or_135_degrees(self):
        # Diagonal coast (x+y=180) runs at 135° in screen-space convention.
        # PCA eigenvector sign is arbitrary → accept ±45° or ±135° (same line).
        angle = detect_coast_angle(make_minimap('water_diagonal'))
        near_45  = abs(abs(angle) - np.pi / 4)       < 0.35
        near_135 = abs(abs(angle) - 3 * np.pi / 4)   < 0.35
        assert near_45 or near_135, (
            f"Expected ~±45° or ~±135°, got {np.degrees(angle):.1f}°"
        )

    def test_all_water_returns_fallback_float(self):
        # No boundary visible — must not crash, returns 0.0 fallback
        angle = detect_coast_angle(make_minimap('all_water'))
        assert isinstance(angle, float)

    def test_all_land_returns_fallback_float(self):
        angle = detect_coast_angle(make_minimap('all_land'))
        assert isinstance(angle, float)


# ── analyze_forward_zone ───────────────────────────────────────────────────

class TestAnalyzeForwardZone:
    def test_result_has_required_keys(self):
        result = analyze_forward_zone(make_minimap('all_water'), (0.0, -1.0))
        assert {'water_px', 'land_px', 'land_ratio', 'is_ocean'} <= result.keys()

    def test_all_water_is_ocean(self):
        # Pure water ahead → ocean → is_ocean=True
        result = analyze_forward_zone(make_minimap('all_water'), (0.0, -1.0))
        assert result['is_ocean'] is True

    def test_all_water_land_ratio_near_zero(self):
        result = analyze_forward_zone(make_minimap('all_water'), (0.0, -1.0))
        assert result['land_ratio'] < 0.03

    def test_water_with_islands_is_not_ocean(self):
        # Water + ~10% land patches → river / internal water → is_ocean=False
        result = analyze_forward_zone(make_minimap('water_with_islands'), (0.0, -1.0))
        assert result['is_ocean'] is False

    def test_water_with_islands_land_ratio_above_threshold(self):
        result = analyze_forward_zone(make_minimap('water_with_islands'), (0.0, -1.0))
        assert result['land_ratio'] >= 0.03

    def test_pointing_at_land_is_not_ocean(self):
        # water_left: right half is land; point RIGHT → lots of land ahead
        result = analyze_forward_zone(make_minimap('water_left'), (1.0, 0.0))
        assert result['is_ocean'] is False
        assert result['land_ratio'] > 0.5

    def test_pointing_at_water_from_land_side(self):
        # water_left: left half is water; point LEFT from center → water ahead → ocean
        result = analyze_forward_zone(make_minimap('water_left'), (-1.0, 0.0))
        assert result['is_ocean'] is True

    def test_pixel_counts_are_non_negative_ints(self):
        result = analyze_forward_zone(make_minimap('all_water'), (1.0, 0.0))
        assert isinstance(result['water_px'], int)
        assert isinstance(result['land_px'], int)
        assert result['water_px'] >= 0
        assert result['land_px'] >= 0

    def test_diagonal_direction_supported(self):
        # Should not crash with a non-cardinal direction
        result = analyze_forward_zone(make_minimap('all_water'), (0.707, -0.707))
        assert 'is_ocean' in result
