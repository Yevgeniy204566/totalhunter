import pytest
import numpy as np
import cv2
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


# ── Task 6: _find_beacon_on_minimap + _canvas_dist_to_beacon ─────────────

def test_find_beacon_returns_coords_when_magenta_present():
    """Returns (x, y) centroid when magenta pixels exist."""
    nav  = _make_nav()
    mm   = _land_minimap()
    cv2.circle(mm, (90, 90), 6, (255, 0, 255), -1)   # draw magenta at centre
    result = nav._find_beacon_on_minimap(mm)
    assert result is not None
    x, y = result
    assert abs(x - 90) <= 5
    assert abs(y - 90) <= 5

def test_find_beacon_returns_none_when_no_magenta():
    nav = _make_nav()
    mm  = _land_minimap()   # no magenta
    assert nav._find_beacon_on_minimap(mm) is None

def test_canvas_dist_to_beacon_correct():
    """Distance from bot at (5,0) to beacon at (0,2) — Pythagorean."""
    nav = _make_nav()
    nav._beacon_grid = (0.0, 2.0)
    nav._bot_gcx     = 5.0
    nav._bot_gcy     = 0.0
    expected = np.hypot(5.0, 2.0)
    assert abs(nav._canvas_dist_to_beacon() - expected) < 1e-6

def test_canvas_dist_inf_when_no_beacon():
    nav = _make_nav()
    nav._beacon_grid = None
    assert nav._canvas_dist_to_beacon() == float('inf')


# ── helper ──────────────────────────────────────────────────────────────

def _nav_in_returning_blind(nav):
    """Put navigator into RETURNING_BLIND with standard parameters."""
    nav._state             = 'RETURNING_BLIND'
    nav._return_steps      = 20
    nav._inland_steps      = 5
    nav._homing_steps      = 0
    nav._inland_vec        = (1.0, 0.0)
    nav._shift_vec         = (0.0, 1.0)
    nav._beacon_grid       = (0.0, 2.0)
    nav._bot_gcx           = 5.0
    nav._bot_gcy           = 0.0
    nav._steps_since_shift = 0
    nav._force_shift_after = 0
    nav._beacon_lost_streak = 0

# ── RETURNING_BLIND ──────────────────────────────────────────────────────

def test_returning_blind_moves_toward_coast():
    """RETURNING_BLIND calls _move_perpendicular(toward_water=True)."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._bot_gcx = 50.0   # very far from beacon → scan NOT triggered

    with patch.object(nav, '_move_perpendicular') as mock_move, \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        nav.step()

    mock_move.assert_called_once_with(toward_water=True)

def test_returning_blind_does_not_call_hsv():
    """HSV detection must NOT run during blind phase."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._bot_gcx = 50.0   # far from beacon

    with patch.object(nav, '_find_beacon_on_minimap') as mock_hsv, \
         patch.object(nav, '_move_perpendicular'), \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        nav.step()

    mock_hsv.assert_not_called()

def test_returning_blind_transitions_to_scan_when_close():
    """RETURNING_BLIND → RETURNING_SCAN when canvas_dist < threshold."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    # Force distance below threshold: bot very close to beacon (0,2)
    nav._bot_gcx = 0.1
    nav._bot_gcy = 2.1   # ~0.14 steps from (0,2) beacon

    with patch.object(nav, '_find_beacon_on_minimap', return_value=None), \
         patch.object(nav, '_move_perpendicular'), \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        nav.step()

    assert nav._state == 'RETURNING_SCAN'

def test_returning_blind_cap_triggers_shift():
    """return_steps==0 → shift + HOMING."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._return_steps = 0

    with patch.object(nav, '_shift_click') as mock_shift, \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        nav.step()

    mock_shift.assert_called_once()
    assert nav._state == 'HOMING'

# ── RETURNING_SCAN ───────────────────────────────────────────────────────

def test_returning_scan_calls_hsv_each_step():
    """RETURNING_SCAN calls _find_beacon_on_minimap every step."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._state   = 'RETURNING_SCAN'
    nav._bot_gcx = 0.5

    with patch.object(nav, '_find_beacon_on_minimap', return_value=None) as mock_hsv, \
         patch.object(nav, '_move_perpendicular'), \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        nav.step()

    mock_hsv.assert_called_once()

def test_returning_scan_transitions_to_beacon_when_found():
    """RETURNING_SCAN → RETURNING_BEACON when magenta detected."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._state   = 'RETURNING_SCAN'
    nav._bot_gcx = 0.5

    mm_with_beacon = _land_minimap()
    cv2.circle(mm_with_beacon, (90, 90), 6, (255, 0, 255), -1)

    with patch.object(nav, '_grab_minimap', return_value=mm_with_beacon), \
         patch.object(nav, '_click_vec'):
        nav.step()

    assert nav._state in ('RETURNING_BEACON', 'HOMING')

def test_returning_scan_cap_triggers_shift():
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._state        = 'RETURNING_SCAN'
    nav._return_steps = 0

    with patch.object(nav, '_shift_click') as mock_shift, \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        nav.step()

    mock_shift.assert_called_once()
    assert nav._state == 'HOMING'
    assert nav._beacon_grid is None

# ── RETURNING_BEACON ─────────────────────────────────────────────────────

def test_returning_beacon_moves_toward_beacon():
    """_click_vec called with vector pointing toward beacon centroid."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._state = 'RETURNING_BEACON'

    mm_with_beacon = _land_minimap()
    cv2.circle(mm_with_beacon, (100, 80), 6, (255, 0, 255), -1)   # off-centre

    with patch.object(nav, '_grab_minimap', return_value=mm_with_beacon), \
         patch.object(nav, '_click_vec') as mock_click:
        nav.step()

    mock_click.assert_called_once()
    dx, dy = mock_click.call_args[0]
    assert dx > 0   # beacon is to the right of centre (100 > 90)
    assert dy < 0   # beacon is above centre (80 < 90)

def test_returning_beacon_stops_when_close():
    """dist < 5px → shift + HOMING + beacon cleared."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._state = 'RETURNING_BEACON'

    mm_with_beacon = _land_minimap()
    # Beacon right at centre → dist == 0
    cv2.circle(mm_with_beacon, (90, 90), 6, (255, 0, 255), -1)

    with patch.object(nav, '_grab_minimap', return_value=mm_with_beacon), \
         patch.object(nav, '_shift_click') as mock_shift, \
         patch.object(nav, '_click_vec'):
        nav.step()

    mock_shift.assert_called_once()
    assert nav._state == 'HOMING'
    assert nav._beacon_grid is None

def test_returning_beacon_fallback_after_3_lost_frames():
    """If beacon not found for 3 consecutive frames → RETURNING_SCAN."""
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._state              = 'RETURNING_BEACON'
    nav._beacon_lost_streak = 2   # about to hit 3

    with patch.object(nav, '_grab_minimap', return_value=_land_minimap()), \
         patch.object(nav, '_find_beacon_on_minimap', return_value=None), \
         patch.object(nav, '_move_perpendicular'):
        nav.step()

    assert nav._state == 'RETURNING_SCAN'
    assert nav._beacon_lost_streak == 0

def test_returning_beacon_cap_triggers_shift():
    nav = _make_nav()
    _nav_in_returning_blind(nav)
    nav._state        = 'RETURNING_BEACON'
    nav._return_steps = 0

    with patch.object(nav, '_shift_click') as mock_shift, \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        nav.step()

    mock_shift.assert_called_once()
    assert nav._state == 'HOMING'
    assert nav._beacon_grid is None

# ── step() dispatch ──────────────────────────────────────────────────────

def test_step_intercepts_diving_at_max_depth():
    """step() places beacon and redirects RETURNING → RETURNING_BLIND."""
    nav = _make_nav()
    nav._state         = 'DIVING'
    nav._inland_steps  = nav.max_inland_steps   # at max depth
    nav._inland_vec    = (1.0, 0.0)
    nav._shift_vec     = (0.0, 1.0)
    nav._bot_gcx       = float(nav.max_inland_steps)
    nav._return_steps  = 0

    with patch.object(nav, '_place_dynamic_beacon') as mock_place, \
         patch.object(nav, '_shift_click'), \
         patch.object(nav, '_grab_minimap', return_value=_land_minimap()):
        # Simulate parent setting RETURNING
        def fake_super_step(*a, **kw):
            nav._state        = 'RETURNING'
            nav._return_steps = nav.max_inland_steps + 15
        with patch.object(
            nav.__class__.__bases__[0], 'step', side_effect=fake_super_step
        ):
            nav.step()

    mock_place.assert_called_once()
    assert nav._state == 'RETURNING_BLIND'


# ── Task 8: reset() + canvas-zero explicit coverage ──────────────────────

def test_reset_clears_beacon_and_canvas():
    """reset() zeroes beacon_grid, _bot_gcx/y, beacon_lost_streak."""
    nav = _make_nav()
    nav._beacon_grid        = (1.0, 2.0)
    nav._bot_gcx            = 99.0
    nav._bot_gcy            = -5.0
    nav._beacon_lost_streak = 2

    nav.reset()

    assert nav._beacon_grid        is None
    assert nav._bot_gcx            == 0.0
    assert nav._bot_gcy            == 0.0
    assert nav._beacon_lost_streak == 0

def test_canvas_zeroed_at_each_dive_start():
    """_move_perpendicular(toward_water=False) with inland_steps==0 zeroes canvas."""
    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.click'):
        nav = _make_nav()
        nav._bot_gcx     = 7.0
        nav._bot_gcy     = -3.0
        nav._inland_steps = 0
        nav._inland_vec   = (1.0, 0.0)
        nav._move_perpendicular(toward_water=False)
        # zeroed THEN one step added → (1, 0)
        assert abs(nav._bot_gcx - 1.0) < 1e-6
        assert abs(nav._bot_gcy - 0.0) < 1e-6


# ── Task 9: engine factory flag tests ────────────────────────────────────

def test_engine_use_beacon_true_injects_beacon_navigator():
    """use_beacon=True → CoastalSnakeNavigatorBeacon injected into PacmanEngine."""
    from navigator_beacon import CoastalSnakeNavigatorBeacon

    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('pyautogui.click'), \
         patch('ultralytics.YOLO'), \
         patch('engine.YOLO'), \
         patch('engine.HuntEngine._start_heartbeat'), \
         patch('navigator.PacmanEngine') as MockPacman:

        mock_instance = MagicMock()
        MockPacman.return_value = mock_instance
        mock_instance.on_found_callback = None

        import engine
        import importlib; importlib.reload(engine)

        h = engine.HuntEngine()
        h.start(conf=0.7, use_beacon=True, pixels_per_step=12)

    # The injected joystick should be a CoastalSnakeNavigatorBeacon
    assert isinstance(mock_instance.joystick, CoastalSnakeNavigatorBeacon)

def test_engine_use_beacon_false_uses_default():
    """use_beacon=False (default) → joystick not replaced with beacon navigator."""
    from navigator_beacon import CoastalSnakeNavigatorBeacon

    with patch('pyautogui.size', return_value=(1920, 1080)), \
         patch('ultralytics.YOLO'), \
         patch('engine.YOLO'), \
         patch('engine.HuntEngine._start_heartbeat'), \
         patch('navigator.PacmanEngine') as MockPacman:

        mock_instance = MagicMock()
        MockPacman.return_value = mock_instance
        mock_instance.on_found_callback = None

        import engine
        import importlib; importlib.reload(engine)

        h = engine.HuntEngine()
        h.start(conf=0.7, use_beacon=False)

    # joystick attribute should NOT be a CoastalSnakeNavigatorBeacon instance
    # (it will be a MagicMock auto-attribute, not a real beacon navigator)
    joystick_val = mock_instance.__dict__.get('joystick')
    assert not isinstance(joystick_val, CoastalSnakeNavigatorBeacon)
