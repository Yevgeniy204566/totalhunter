import pytest
import numpy as np
from unittest.mock import patch, MagicMock


# ── shared minimap stub ──────────────────────────────────────────────────
def _land_minimap():
    """180×180 BGR frame that looks like land (green-ish)."""
    mm = np.zeros((180, 180, 3), dtype=np.uint8)
    mm[:, :] = (30, 120, 30)   # BGR green ≈ land
    return mm


def _water_minimap():
    """180×180 BGR frame that looks like water (blue-ish)."""
    mm = np.zeros((180, 180, 3), dtype=np.uint8)
    mm[:, :] = (160, 80, 20)   # BGR blue ≈ water
    return mm


# ── Test 1 ───────────────────────────────────────────────────────────────
def test_old_navigator_class_unchanged():
    """CoastalSnakeNavigator from navigator.py must be importable and intact."""
    from navigator import CoastalSnakeNavigator
    nav = CoastalSnakeNavigator.__new__(CoastalSnakeNavigator)
    assert hasattr(CoastalSnakeNavigator, 'step')
    assert hasattr(CoastalSnakeNavigator, 'move')
    assert 'max_inland_steps' in CoastalSnakeNavigator.__init__.__code__.co_varnames


# ── Test 2 ───────────────────────────────────────────────────────────────
def test_beacon_navigator_importable():
    from navigator_beacon import CoastalSnakeNavigatorBeacon
    from navigator import CoastalSnakeNavigator
    assert issubclass(CoastalSnakeNavigatorBeacon, CoastalSnakeNavigator)


# ── Step 2.1: Canvas tracking tests ──────────────────────────────────────
def _make_nav(**kwargs):
    """Build beacon navigator with pyautogui.size() mocked."""
    with patch('pyautogui.size', return_value=(1920, 1080)):
        from navigator_beacon import CoastalSnakeNavigatorBeacon
        return CoastalSnakeNavigatorBeacon(
            center_x=90, center_y=925, step=13,
            pixels_per_step=12,
            **kwargs
        )


def test_click_vec_updates_canvas_after_super():
    """After _click_vec(1,0), _bot_gcx increases by 1.0."""
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.click'):
        nav = _make_nav()
        nav._click_vec(1.0, 0.0)
        assert abs(nav._bot_gcx - 1.0) < 1e-6
        assert abs(nav._bot_gcy - 0.0) < 1e-6


def test_move_perpendicular_zeros_canvas_at_dive_start():
    """When inland_steps==0 and toward_water=False, canvas is zeroed before moving."""
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.click'):
        nav = _make_nav()
        nav._bot_gcx = 99.0   # dirty state
        nav._bot_gcy = -7.0
        nav._inland_steps = 0
        nav._inland_vec = (1.0, 0.0)
        nav._move_perpendicular(toward_water=False)
        # After zeroing + one inland step: should be (1, 0)
        assert abs(nav._bot_gcx - 1.0) < 1e-6
        assert abs(nav._bot_gcy - 0.0) < 1e-6


def test_canvas_not_zeroed_on_non_first_step():
    """inland_steps > 0: no zeroing, canvas accumulates normally."""
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.click'):
        nav = _make_nav()
        nav._bot_gcx = 3.0
        nav._inland_steps = 3
        nav._inland_vec = (1.0, 0.0)
        nav._move_perpendicular(toward_water=False)
        assert abs(nav._bot_gcx - 4.0) < 1e-6


# ── Task 3: _is_land_at ───────────────────────────────────────────────────

def test_is_land_at_returns_true_on_land_pixel():
    nav = _make_nav()
    mm = _land_minimap()   # solid green → land mask fires
    # centre pixel of land minimap should be land
    cx, cy = mm.shape[1] // 2, mm.shape[0] // 2
    assert nav._is_land_at(mm, cx, cy) is True

def test_is_land_at_returns_false_on_water_pixel():
    nav = _make_nav()
    mm = _water_minimap()
    cx, cy = mm.shape[1] // 2, mm.shape[0] // 2
    assert nav._is_land_at(mm, cx, cy) is False

def test_is_land_at_out_of_bounds_returns_false():
    nav = _make_nav()
    mm = _land_minimap()
    assert nav._is_land_at(mm, -1, 50)  is False
    assert nav._is_land_at(mm, 200, 50) is False
