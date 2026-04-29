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


# ── Task 4: _place_dynamic_beacon ────────────────────────────────────────

def test_place_beacon_on_land():
    """Beacon placed 2 shift-steps from coast when land available."""
    nav = _make_nav()
    nav._inland_vec  = (1.0, 0.0)
    nav._shift_vec   = (0.0, 1.0)
    nav._inland_steps = 5
    nav._bot_gcx     = 5.0
    nav._bot_gcy     = 0.0

    with patch.object(nav, '_grab_minimap', return_value=_land_minimap()), \
         patch.object(nav, '_is_land_at', return_value=True):
        nav._place_dynamic_beacon()

    bx, by = nav._beacon_grid
    # Beacon should be at coast (0) + 2 shift steps = (0, 2)
    assert abs(bx - 0.0) < 1e-6
    assert abs(by - 2.0) < 1e-6

def test_place_beacon_shifts_off_water():
    """When first position is water, ping-pong search finds land."""
    nav = _make_nav()
    nav._inland_vec  = (1.0, 0.0)
    nav._shift_vec   = (0.0, 1.0)
    nav._inland_steps = 5
    nav._bot_gcx     = 5.0
    nav._bot_gcy     = 0.0

    # First call returns False (water), second returns True (land)
    land_responses = [False, True]
    with patch.object(nav, '_grab_minimap', return_value=_land_minimap()), \
         patch.object(nav, '_is_land_at', side_effect=land_responses):
        nav._place_dynamic_beacon()

    assert nav._beacon_grid is not None

def test_place_beacon_fallback_after_20_iterations(caplog):
    """All 20 iterations fail → use default position + log WARNING."""
    import logging
    nav = _make_nav()
    nav._inland_vec  = (1.0, 0.0)
    nav._shift_vec   = (0.0, 1.0)
    nav._inland_steps = 5
    nav._bot_gcx     = 5.0
    nav._bot_gcy     = 0.0

    with patch.object(nav, '_grab_minimap', return_value=_water_minimap()), \
         patch.object(nav, '_is_land_at', return_value=False), \
         caplog.at_level(logging.WARNING):
        nav._place_dynamic_beacon()

    assert nav._beacon_grid is not None
    assert 'land not found' in caplog.text


# ── Task 5: _grab_minimap override ───────────────────────────────────────

def test_magenta_drawn_in_processing_buffer():
    """_grab_minimap() returns frame with magenta pixels when beacon is set."""
    nav = _make_nav()
    nav._beacon_grid  = (0.0, 2.0)   # beacon at (0, 2) step-space
    nav._bot_gcx      = 5.0           # bot is 5 steps inland
    nav._bot_gcy      = 0.0
    nav._inland_vec   = (1.0, 0.0)
    nav._shift_vec    = (0.0, 1.0)

    base_mm = _land_minimap()
    with patch.object(
        nav.__class__.__bases__[0], '_grab_minimap', return_value=base_mm.copy()
    ):
        mm = nav._grab_minimap()

    # Check magenta pixels exist (BGR: B=255, G=0, R=255)
    magenta_mask = (mm[:,:,0] == 255) & (mm[:,:,1] == 0) & (mm[:,:,2] == 255)
    assert magenta_mask.any(), "No magenta pixels found in output frame"

def test_no_magenta_when_beacon_none():
    """No magenta drawn when beacon_grid is None."""
    nav = _make_nav()
    nav._beacon_grid = None

    base_mm = _land_minimap()
    with patch.object(
        nav.__class__.__bases__[0], '_grab_minimap', return_value=base_mm.copy()
    ):
        mm = nav._grab_minimap()

    magenta_mask = (mm[:,:,0] == 255) & (mm[:,:,1] == 0) & (mm[:,:,2] == 255)
    assert not magenta_mask.any()
