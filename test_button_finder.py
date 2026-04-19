"""Tests for button_finder.py — pure functions, no real screen."""
import numpy as np
import cv2
import pytest


class TestApplyColorMask:
    def test_green_mask_detects_green_pixel(self):
        from button_finder import _apply_color_mask
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[:] = (0, 180, 0)   # BGR green
        mask = _apply_color_mask(img, 'green')
        assert mask.sum() > 0

    def test_green_mask_ignores_purple(self):
        from button_finder import _apply_color_mask
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[:] = (180, 0, 180)   # BGR purple
        mask = _apply_color_mask(img, 'green')
        assert mask.sum() == 0

    def test_purple_mask_detects_purple(self):
        from button_finder import _apply_color_mask
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[:] = (180, 0, 180)   # BGR purple
        mask = _apply_color_mask(img, 'purple')
        assert mask.sum() > 0

    def test_unknown_color_returns_empty(self):
        from button_finder import _apply_color_mask
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        mask = _apply_color_mask(img, 'unknown_color')
        assert mask.sum() == 0


class TestPickContour:
    def _make_contour(self, x, y, w, h):
        """Create a simple rectangular contour."""
        pts = np.array([[[x, y]], [[x+w, y]], [[x+w, y+h]], [[x, y+h]]], dtype=np.int32)
        return pts

    def test_returns_none_when_no_contours(self):
        from button_finder import _pick_contour
        assert _pick_contour([], 'largest', 0, 0) is None

    def test_picks_rightmost(self):
        from button_finder import _pick_contour
        left  = self._make_contour(10, 50, 80, 30)   # cx=50
        right = self._make_contour(200, 50, 80, 30)  # cx=240
        result = _pick_contour([left, right], 'rightmost', 0, 0)
        assert result is not None
        cx, cy = result
        assert cx == 240

    def test_picks_leftmost(self):
        from button_finder import _pick_contour
        left  = self._make_contour(10, 50, 80, 30)   # cx=50
        right = self._make_contour(200, 50, 80, 30)  # cx=240
        result = _pick_contour([left, right], 'leftmost', 0, 0)
        assert result is not None
        cx, cy = result
        assert cx == 50

    def test_picks_topmost(self):
        from button_finder import _pick_contour
        top    = self._make_contour(50, 10, 80, 30)   # cy=25
        bottom = self._make_contour(50, 200, 80, 30)  # cy=215
        result = _pick_contour([top, bottom], 'topmost', 0, 0)
        assert result is not None
        cx, cy = result
        assert cy == 25

    def test_skips_contours_below_min_area(self):
        from button_finder import _pick_contour
        tiny = self._make_contour(10, 10, 5, 5)   # area ~25, below min_area=800
        result = _pick_contour([tiny], 'largest', 0, 0)
        assert result is None

    def test_skips_taller_than_wide(self):
        from button_finder import _pick_contour
        tall = self._make_contour(10, 10, 20, 200)   # w < h
        result = _pick_contour([tall], 'largest', 0, 0)
        assert result is None

    def test_applies_region_offset(self):
        from button_finder import _pick_contour
        cnt = self._make_contour(10, 10, 100, 40)   # local cx=60, cy=30
        result = _pick_contour([cnt], 'largest', region_x=500, region_y=300)
        assert result == (560, 330)


class TestFindColoredButton:
    def test_returns_none_on_exception(self):
        from button_finder import find_colored_button
        # Invalid region (zero size) should not raise
        result = find_colored_button((0, 0, 0, 0), 'green')
        assert result is None
