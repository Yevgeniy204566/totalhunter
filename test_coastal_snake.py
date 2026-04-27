# test_coastal_snake.py
"""TDD tests for CoastalSnakeNavigator — hard-corridor lawnmower."""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from navigator import CoastalSnakeNavigator


# ── helpers ───────────────────────────────────────────────────────────────

def _info(is_at_coast=False, is_ocean=False, water_px=0, land_px=100, footprint_px=0):
    """Build a _read_minimap return dict with all required keys."""
    return {
        'coast_angle': 0.0,
        'inland_vec':  (1.0, 0.0),
        'coast_vec':   (0.0, 1.0),
        'fwd': {
            'is_ocean':   is_ocean,
            'land_ratio': 0.0 if is_ocean else 0.5,
            'water_px':   water_px,
            'land_px':    land_px,
        },
        'is_at_coast': is_at_coast,
        'fwd_footprint': {'footprint_px': footprint_px},
    }


def make_navigator(max_inland=3, ocean_ratio=0.03, min_water=10):
    nav = CoastalSnakeNavigator(
        center_x=90, center_y=925, step=13,
        max_inland_steps=max_inland,
        ocean_land_ratio=ocean_ratio,
        min_water_px=min_water,
    )
    nav._click_vec    = MagicMock()
    nav._grab_minimap = MagicMock()
    return nav


# ── state machine ─────────────────────────────────────────────────────────

class TestCoastalSnakeStateMachine:
    def test_initial_state_is_homing(self):
        nav = make_navigator()
        assert nav._state == 'HOMING'

    def test_reset_returns_to_homing(self):
        nav = make_navigator()
        nav._state = 'DIVING'
        nav.reset()
        assert nav._state == 'HOMING'

    def test_homing_clicks_perpendicular_to_coast_toward_water(self):
        """On land (no ocean ahead): HOMING clicks -inland_vec (toward water)."""
        nav = make_navigator()
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_read_minimap', return_value=_info(is_ocean=False)):
            nav.step()
        nav._click_vec.assert_called_once()
        args = nav._click_vec.call_args[0]
        # -inland_vec = (-1, 0)
        assert args[0] < 0, f"Expected click toward water (-inland), got {args}"

    def test_homing_clicks_toward_land_when_in_ocean(self):
        """In open ocean (is_ocean=True): HOMING clicks inland_vec (toward land)."""
        nav = make_navigator()
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_read_minimap', return_value=_info(is_ocean=True, water_px=600)):
            nav.step()
        nav._click_vec.assert_called_once()
        args = nav._click_vec.call_args[0]
        # inland_vec = (1, 0)
        assert args[0] > 0, f"Expected click toward land (+inland), got {args}"

    def test_homing_transitions_to_diving_when_at_coast(self):
        nav = make_navigator()
        with patch.object(nav, '_read_minimap', return_value=_info(is_at_coast=True)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'

    def test_diving_increments_step_counter(self):
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_peek_step', return_value=1.0):
            nav.step()
        assert nav._inland_steps == 1

    def test_diving_transitions_to_returning_at_max_depth(self):
        nav = make_navigator(max_inland=2)
        nav._state = 'DIVING'
        nav._inland_steps = 2
        nav._inland_vec = (1.0, 0.0)
        nav.step()
        assert nav._state == 'RETURNING'

    def test_returning_clicks_back_toward_coast(self):
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 2
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_peek_step', return_value=1.0):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=True, multiplier=1.0)

    def test_returning_stops_when_coast_detected(self):
        """RETURNING stops when is_at_coast regardless of remaining step count."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 5
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_peek_step', return_value=None):
            nav.step()
        assert nav._state == 'HOMING'

    def test_returning_stops_at_safety_cap(self):
        """RETURNING stops at safety cap even if coast not detected (curved coast)."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 0
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_peek_step', return_value=1.0):
            nav.step()
        assert nav._state == 'HOMING'

    def test_returning_does_not_update_inland_vec(self):
        """inland_vec must stay frozen during RETURNING — no angle recalculation."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 3
        nav._inland_vec = (1.0, 0.0)   # frozen dive direction
        original_vec = nav._inland_vec
        with patch.object(nav, '_peek_step', return_value=1.0):
            with patch.object(nav, '_move_perpendicular'):
                nav.step()
        assert nav._inland_vec == original_vec, \
            "inland_vec must not change during RETURNING"


# ── shift is inline, not a separate state ─────────────────────────────────

class TestInlineShift:
    def test_shift_click_at_max_depth(self):
        """At max depth: shift click fired inline, then RETURNING."""
        nav = make_navigator(max_inland=2)
        nav._state = 'DIVING'
        nav._inland_steps = 2
        nav._inland_vec = (1.0, 0.0)
        nav._coast_vec  = (0.0, 1.0)
        nav._shift_vec  = (0.0, 1.0)
        nav.step()
        nav._click_vec.assert_called_once()
        args = nav._click_vec.call_args[0]
        assert abs(args[0] - 0.0) < 0.01 and abs(args[1] - 1.0) < 0.01, \
            f"Expected shift_vec (0,1), got {args}"

    def test_shift_click_when_returning_to_coast(self):
        """When coast detected during RETURNING: shift click + HOMING."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 5
        nav._inland_vec = (1.0, 0.0)
        nav._shift_vec  = (0.0, 1.0)
        with patch.object(nav, '_peek_step', return_value=None):
            nav.step()
        assert nav._state == 'HOMING'

    def test_return_steps_safety_cap_horizontal(self):
        """Horizontal movement: _return_steps = max_inland + 15 (generous safety cap)."""
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_steps = 5
        nav._inland_vec = (1.0, 0.0)   # horizontal
        nav._shift_vec  = (0.0, 1.0)
        nav.step()
        assert nav._state == 'RETURNING'
        assert nav._return_steps == 20   # 5 + 15

    def test_return_steps_safety_cap_vertical_no_bonus(self):
        """Vertical movement: cap is max_inland + 15, same as horizontal."""
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_steps = 5
        nav._inland_vec = (0.0, 1.0)   # vertical
        nav._shift_vec  = (1.0, 0.0)
        nav.step()
        assert nav._state == 'RETURNING'
        assert nav._return_steps == 20   # 5 + 15, no vertical bonus

    def test_shift_vec_locked_on_first_real_angle(self):
        """_shift_vec is set only from a non-zero (real) angle, not from fallback 0.0."""
        nav = make_navigator()
        nav._shift_vec_set = False
        fake_mm = np.zeros((180, 180, 3), dtype=np.uint8)
        nav._grab_minimap.return_value = fake_mm

        import minimap_reader as mr
        with patch.object(mr, 'detect_coast_angle', return_value=0.0), \
             patch.object(mr, 'analyze_forward_zone',
                          return_value={'water_px': 0, 'land_px': 0,
                                        'land_ratio': 0.0, 'is_ocean': False}):
            nav._read_minimap()
        # fallback 0.0 → should NOT lock shift_vec
        assert nav._shift_vec_set is False, \
            "shift_vec must NOT be set from a fallback 0.0 angle"

    def test_shift_vec_locked_when_real_angle_detected(self):
        """shift_vec is locked when detect_coast_angle returns a real non-zero angle."""
        nav = make_navigator()
        nav._shift_vec_set = False
        fake_mm = np.zeros((180, 180, 3), dtype=np.uint8)
        nav._grab_minimap.return_value = fake_mm

        import minimap_reader as mr
        # coast_angle = π/2 → coast_vec = (0, 1) (vertical coast)
        with patch.object(mr, 'detect_coast_angle', return_value=np.pi / 2), \
             patch.object(mr, 'analyze_forward_zone',
                          return_value={'water_px': 0, 'land_px': 100,
                                        'land_ratio': 1.0, 'is_ocean': False}):
            nav._read_minimap()
        assert nav._shift_vec_set is True
        # coast_angle=π/2 → coast_vec=(cos(π/2), sin(π/2)) ≈ (0, 1)
        assert abs(nav._shift_vec[1] - 1.0) < 0.01, \
            f"Expected vertical shift_vec (0,1) for vertical coast, got {nav._shift_vec}"

    def test_shift_vec_not_updated_on_subsequent_angle_reads(self):
        """Once locked, _shift_vec stays fixed even if coast angle drifts."""
        nav = make_navigator()
        nav._shift_vec     = (1.0, 0.0)
        nav._shift_vec_set = True
        # Simulate angle drift
        nav._update_coast_angle(np.pi / 2)
        assert nav._shift_vec == (1.0, 0.0)  # unchanged


# ── inland direction validation ───────────────────────────────────────────

class TestInlandDirectionValidation:
    def test_inland_vec_picks_side_with_more_land(self):
        nav = make_navigator()
        nav._coast_angle = 0.0
        nav._angle_init  = True
        fake_mm = np.zeros((180, 180, 3), dtype=np.uint8)
        nav._grab_minimap.return_value = fake_mm

        import minimap_reader as mr

        def fwd_side_effect(mm, direction, **kw):
            if direction[1] > 0:
                return {'water_px': 600, 'land_px': 5,  'land_ratio': 0.008, 'is_ocean': True}
            else:
                return {'water_px': 0,   'land_px': 250, 'land_ratio': 0.9,  'is_ocean': False}

        with patch.object(mr, 'detect_coast_angle', return_value=0.0), \
             patch.object(mr, 'analyze_forward_zone', side_effect=fwd_side_effect):
            result = nav._read_minimap()

        assert result['inland_vec'][1] < 0, \
            f"Expected inland toward land (y<0), got {result['inland_vec']}"

    def test_inland_vec_unchanged_when_no_land_visible(self):
        nav = make_navigator()
        nav._coast_angle = 0.0
        nav._angle_init  = True
        nav._inland_vec  = (0.0, 1.0)
        fake_mm = np.zeros((180, 180, 3), dtype=np.uint8)
        nav._grab_minimap.return_value = fake_mm

        import minimap_reader as mr

        with patch.object(mr, 'detect_coast_angle', return_value=0.0), \
             patch.object(mr, 'analyze_forward_zone',
                          return_value={'water_px': 800, 'land_px': 0,
                                        'land_ratio': 0.0, 'is_ocean': True}):
            result = nav._read_minimap()

        assert abs(result['inland_vec'][1] - 1.0) < 0.01, \
            f"Expected inland_vec unchanged (0,1), got {result['inland_vec']}"


# ── _read_minimap API ─────────────────────────────────────────────────────

class TestReadMinimap:
    def test_returns_required_keys(self):
        nav = make_navigator()
        fake_mm = np.zeros((180, 180, 3), dtype=np.uint8)
        nav._grab_minimap.return_value = fake_mm

        import minimap_reader as mr
        with patch.object(mr, 'detect_coast_angle', return_value=0.5), \
             patch.object(mr, 'analyze_forward_zone',
                          return_value={'water_px': 0, 'land_px': 0,
                                        'land_ratio': 0.0, 'is_ocean': False}):
            result = nav._read_minimap()

        assert {'coast_angle', 'inland_vec', 'coast_vec', 'fwd', 'is_at_coast'} \
               <= result.keys()

    def test_is_at_coast_true_when_water_in_seaward_direction(self):
        nav = make_navigator()
        fake_mm = np.zeros((180, 180, 3), dtype=np.uint8)
        nav._grab_minimap.return_value = fake_mm

        import minimap_reader as mr

        def fwd_side_effect(mm, direction, **kw):
            if abs(direction[1]) > 0.9:
                return {'water_px': 800, 'land_px': 5, 'land_ratio': 0.006, 'is_ocean': False}
            return {'water_px': 0, 'land_px': 100, 'land_ratio': 1.0, 'is_ocean': False}

        with patch.object(mr, 'detect_coast_angle', return_value=0.0), \
             patch.object(mr, 'analyze_forward_zone', side_effect=fwd_side_effect):
            result = nav._read_minimap()

        assert result['is_at_coast'] is True


# ── ocean hard-stop in HOMING ─────────────────────────────────────────────

class TestOceanHardStop:
    def test_homing_retreats_when_max_steps_in_open_ocean(self):
        nav = make_navigator()
        nav._state = 'HOMING'
        nav._homing_steps = 10
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_ocean=True, water_px=700, land_px=0)):
            nav.step()
        assert nav._state == 'RETURNING'

    def test_homing_dives_when_coast_found_normally(self):
        nav = make_navigator()
        nav._state = 'HOMING'
        nav._homing_steps = 3
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'

    def test_homing_dives_when_max_steps_but_land_ahead(self):
        nav = make_navigator()
        nav._state = 'HOMING'
        nav._homing_steps = 10
        with patch.object(nav, '_read_minimap',
                          return_value=_info(water_px=50, land_px=150)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'


# ── shift НАМЕРТВО perpendicular to inland_vec ───────────────────────────────

class TestShiftAlwaysPerpendicular:
    """Shift must ALWAYS be ⊥ to inland_vec — для любого угла берега."""

    def test_shift_not_parallel_to_inland_after_pca_zero(self):
        """Bug fix: when PCA returns 0.0 fallback, shift_vec must NOT equal inland_vec."""
        nav = make_navigator()
        fake_mm = np.zeros((180, 180, 3), dtype=np.uint8)
        nav._grab_minimap.return_value = fake_mm

        import minimap_reader as mr
        with patch.object(mr, 'detect_coast_angle', return_value=0.0), \
             patch.object(mr, 'analyze_forward_zone',
                          return_value={'water_px': 0, 'land_px': 100,
                                        'land_ratio': 1.0, 'is_ocean': False}):
            nav._read_minimap()

        iv = nav._inland_vec
        sv = nav._shift_vec
        dot = iv[0] * sv[0] + iv[1] * sv[1]
        assert abs(dot) < 0.01, \
            f"shift_vec must be ⊥ to inland_vec after PCA=0.0  dot={dot:.4f}  iv={iv}  sv={sv}"

    def test_shift_click_perpendicular_for_diagonal_inland(self):
        """Shift click is ⊥ to diagonal inland_vec (45° coast)."""
        nav = make_navigator(max_inland=2)
        nav._state = 'DIVING'
        nav._inland_steps = 2
        iv = (-0.707, 0.707)
        nav._inland_vec = iv
        nav.step()
        args = nav._click_vec.call_args[0]
        dot = args[0] * iv[0] + args[1] * iv[1]
        assert abs(dot) < 0.01, \
            f"Shift must be ⊥ to inland (-0.707,0.707)  dot={dot:.4f}  shift={args}"

    def test_shift_click_perpendicular_for_cardinal_down(self):
        """Shift click is ⊥ to inland=(0,1) (diving down)."""
        nav = make_navigator(max_inland=2)
        nav._state = 'DIVING'
        nav._inland_steps = 2
        nav._inland_vec = (0.0, 1.0)
        nav.step()
        args = nav._click_vec.call_args[0]
        dot = args[0] * 0.0 + args[1] * 1.0
        assert abs(dot) < 0.01, \
            f"Shift must be ⊥ to inland (0,1)  dot={dot:.4f}  shift={args}"

    def test_shift_click_perpendicular_for_cardinal_left(self):
        """Shift click is ⊥ to inland=(-1,0) (diving left)."""
        nav = make_navigator(max_inland=2)
        nav._state = 'DIVING'
        nav._inland_steps = 2
        nav._inland_vec = (-1.0, 0.0)
        nav.step()
        args = nav._click_vec.call_args[0]
        dot = args[0] * (-1.0) + args[1] * 0.0
        assert abs(dot) < 0.01, \
            f"Shift must be ⊥ to inland (-1,0)  dot={dot:.4f}  shift={args}"

    def test_force_shift_after_n_steps_in_diving(self):
        """After force_shift_after steps without shift, bot forces lateral shift in DIVING."""
        from navigator import CoastalSnakeNavigator
        nav = CoastalSnakeNavigator(
            center_x=90, center_y=925, step=13,
            max_inland_steps=5,
            force_shift_after=3,
        )
        nav._click_vec    = MagicMock()
        nav._grab_minimap = MagicMock()
        nav._state = 'DIVING'
        nav._inland_steps = 0
        iv = (1.0, 0.0)
        nav._inland_vec = iv
        nav._steps_since_shift = 3   # at limit

        nav.step()

        args = nav._click_vec.call_args[0]
        dot = args[0] * iv[0] + args[1] * iv[1]
        assert abs(dot) < 0.01, \
            f"Force-shift must be ⊥ to inland (1,0)  got={args}  dot={dot:.4f}"
        assert nav._steps_since_shift == 0, "steps_since_shift must reset after force-shift"

    def test_force_shift_after_n_steps_in_returning(self):
        """After force_shift_after steps without shift, bot forces lateral shift in RETURNING."""
        from navigator import CoastalSnakeNavigator
        nav = CoastalSnakeNavigator(
            center_x=90, center_y=925, step=13,
            max_inland_steps=5,
            force_shift_after=3,
        )
        nav._click_vec    = MagicMock()
        nav._grab_minimap = MagicMock()
        nav._state = 'RETURNING'
        nav._return_steps = 5
        iv = (0.0, 1.0)
        nav._inland_vec = iv
        nav._steps_since_shift = 3   # at limit

        with patch.object(nav, '_is_at_coast_now', return_value=False):
            nav.step()

        args = nav._click_vec.call_args[0]
        dot = args[0] * iv[0] + args[1] * iv[1]
        assert abs(dot) < 0.01, \
            f"Force-shift must be ⊥ to inland (0,1)  got={args}  dot={dot:.4f}"
        assert nav._steps_since_shift == 0


# ── blind return phase ────────────────────────────────────────────────────

class TestOceanColumnCheck:
    def test_ocean_column_skips_dive(self):
        """At coast: fwd has no land and lots of water → shift, stay HOMING."""
        nav = make_navigator(min_water=10)
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=0, water_px=500)):
            with patch.object(nav, '_shift_click') as mock_shift:
                nav.step()
        mock_shift.assert_called_once()
        assert nav._state == 'HOMING'

    def test_ocean_column_insufficient_water_dives(self):
        """At coast: fwd land_px=0 but water_px <= min_water_px → normal dive."""
        nav = make_navigator(min_water=10)
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=0, water_px=5)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'

    def test_returning_stops_on_water(self):
        """RETURNING: peek=None (coast) → shift + HOMING."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 10
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_peek_step', return_value=None):
            nav.step()
        assert nav._state == 'HOMING'

    def test_returning_continues_on_land(self):
        """RETURNING: peek=1.0 (land ahead) → continues."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 10
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_peek_step', return_value=1.0):
            with patch.object(nav, '_move_perpendicular'):
                nav.step()
        assert nav._state == 'RETURNING'


import math
from navigator import _clamp_vec


class TestClampVec:
    def test_unit_length(self):
        """Result is always a unit vector."""
        result = _clamp_vec((0.0, 1.0), (1.0, 0.0), math.radians(10))
        length = math.sqrt(result[0]**2 + result[1]**2)
        assert abs(length - 1.0) < 1e-9

    def test_passes_small_angle(self):
        """Angle below threshold → v_new returned unchanged."""
        v_prev = (1.0, 0.0)
        v_new  = (math.cos(math.radians(5)), math.sin(math.radians(5)))
        result = _clamp_vec(v_new, v_prev, math.radians(10))
        assert abs(result[0] - v_new[0]) < 1e-9
        assert abs(result[1] - v_new[1]) < 1e-9

    def test_clamps_large_angle(self):
        """Angle above threshold → result is exactly max_delta from v_prev."""
        v_prev = (1.0, 0.0)
        v_new  = (0.0, 1.0)   # 90°
        max_d  = math.radians(10)
        result = _clamp_vec(v_new, v_prev, max_d)
        dot    = max(-1.0, min(1.0, result[0]*v_prev[0] + result[1]*v_prev[1]))
        assert abs(math.acos(dot) - max_d) < 1e-9

    def test_rotates_toward_v_new(self):
        """Clamping rotates toward v_new (CCW when v_new is CCW of v_prev)."""
        v_prev = (1.0, 0.0)   # 0°
        v_new  = (0.0, 1.0)   # 90° CCW
        result = _clamp_vec(v_new, v_prev, math.radians(10))
        assert result[1] > 0   # y > 0 → rotated CCW

    def test_exact_threshold_passes(self):
        """Angle exactly equal to max_delta → v_new unchanged."""
        max_d  = math.radians(10)
        v_prev = (1.0, 0.0)
        v_new  = (math.cos(max_d), math.sin(max_d))
        result = _clamp_vec(v_new, v_prev, max_d)
        assert abs(result[0] - v_new[0]) < 1e-9
        assert abs(result[1] - v_new[1]) < 1e-9


class TestAngularDamper:
    def test_first_dive_no_clamp(self):
        """First dive: _prev_inland_vec is None → inland_vec unchanged."""
        nav = make_navigator()
        nav._max_pitch_delta = math.radians(10)
        nav._inland_vec      = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'
        assert abs(nav._prev_inland_vec[0] - 0.0) < 1e-9
        assert abs(nav._prev_inland_vec[1] - 1.0) < 1e-9

    def test_second_dive_clamps_large_angle(self):
        """Second dive with angle > max_pitch_delta → inland_vec clamped."""
        nav = make_navigator()
        nav._max_pitch_delta = math.radians(10)
        nav._prev_inland_vec = (1.0, 0.0)   # previous was 0°
        nav._inland_vec      = (0.0, 1.0)   # new would be 90°
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'
        iv  = nav._inland_vec
        dot = max(-1.0, min(1.0, iv[0]*1.0 + iv[1]*0.0))
        assert abs(math.acos(dot) - math.radians(10)) < 1e-9

    def test_damper_disabled_at_zero(self):
        """max_pitch_delta=0 → no clamping regardless of angle."""
        nav = make_navigator()
        nav._max_pitch_delta = 0.0
        nav._prev_inland_vec = (1.0, 0.0)
        nav._inland_vec      = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert abs(nav._prev_inland_vec[0] - 0.0) < 1e-9
        assert abs(nav._prev_inland_vec[1] - 1.0) < 1e-9

    def test_reset_clears_prev_vec(self):
        """reset() clears _prev_inland_vec."""
        nav = make_navigator()
        nav._prev_inland_vec = (1.0, 0.0)
        nav.reset()
        assert nav._prev_inland_vec is None


class TestFootprintCheck:
    def test_footprint_ahead_skips_dive(self):
        """At coast with footprint ahead → shift_click, stay HOMING."""
        nav = make_navigator()
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50, footprint_px=25)):
            with patch.object(nav, '_shift_click') as mock_shift:
                nav.step()
        mock_shift.assert_called_once()
        assert nav._state == 'HOMING'

    def test_no_footprint_dives_normally(self):
        """At coast with no footprint ahead → normal DIVING transition."""
        nav = make_navigator()
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50, footprint_px=0)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'

    def test_footprint_check_disabled_when_footprint_off(self):
        """footprint_enabled=False → footprint check skipped, dive proceeds."""
        nav = make_navigator()
        nav._footprint_enabled = False
        with patch.object(nav, '_read_minimap',
                          return_value=_info(is_at_coast=True, land_px=50, footprint_px=999)):
            with patch.object(nav, '_peek_step', return_value=1.0):
                nav.step()
        assert nav._state == 'DIVING'


class TestPeekStep:
    def _nav(self):
        nav = make_navigator()
        nav._inland_vec = (1.0, 0.0)
        return nav

    def test_land_immediate_returns_1x(self):
        """radius=30 has land → 1.0 (normal step)."""
        nav = self._nav()
        land_info  = {'land_px': 50, 'water_px': 0, 'is_ocean': False, 'land_ratio': 0.5}
        with patch('minimap_reader.analyze_forward_zone', return_value=land_info):
            result = nav._peek_step((1.0, 0.0))
        assert result == 1.0

    def test_water_then_land_mid_returns_1_5x(self):
        """radius=30 water, radius=60 has land → 1.5 (jump 1 screen)."""
        nav = self._nav()
        water_info = {'land_px': 0, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.0}
        land_info  = {'land_px': 30, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.3}
        with patch('minimap_reader.analyze_forward_zone', side_effect=[water_info, land_info]):
            result = nav._peek_step((1.0, 0.0))
        assert result == 1.5

    def test_water_then_land_far_returns_2x(self):
        """radius=30 water, radius=60 water, radius=90 has land → 2.0 (jump 2 screens)."""
        nav = self._nav()
        water_info = {'land_px': 0, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.0}
        land_far   = {'land_px': 20, 'water_px': 600, 'is_ocean': False, 'land_ratio': 0.2}
        with patch('minimap_reader.analyze_forward_zone', side_effect=[water_info, water_info, land_far]):
            result = nav._peek_step((1.0, 0.0))
        assert result == 2.0

    def test_all_water_returns_none(self):
        """All 3 radii no land, water present → None (ocean / coast boundary)."""
        nav = self._nav()
        water_info = {'land_px': 0, 'water_px': 600, 'is_ocean': True, 'land_ratio': 0.0}
        with patch('minimap_reader.analyze_forward_zone', return_value=water_info):
            result = nav._peek_step((1.0, 0.0))
        assert result is None

    def test_no_significant_water_returns_1x(self):
        """radius=30 no land but water_px <= min_water_px → 1.0 (safe to step)."""
        nav = self._nav()
        dry_info = {'land_px': 0, 'water_px': 5, 'is_ocean': False, 'land_ratio': 0.0}
        with patch('minimap_reader.analyze_forward_zone', return_value=dry_info):
            result = nav._peek_step((1.0, 0.0))
        assert result == 1.0


class TestPeekIntegration:
    def _nav_diving(self):
        nav = make_navigator(max_inland=5)
        nav._state       = 'DIVING'
        nav._inland_steps = 2
        nav._inland_vec  = (1.0, 0.0)
        nav._shift_vec   = (0.0, 1.0)
        return nav

    def _nav_returning(self):
        nav = make_navigator(max_inland=5)
        nav._state        = 'RETURNING'
        nav._return_steps = 10
        nav._inland_vec   = (1.0, 0.0)
        nav._shift_vec    = (0.0, 1.0)
        return nav

    def test_diving_normal_step(self):
        """DIVING: peek=1.0 → _move_perpendicular(toward_water=False, multiplier=1.0)."""
        nav = self._nav_diving()
        with patch.object(nav, '_peek_step', return_value=1.0):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=False, multiplier=1.0)
        assert nav._state == 'DIVING'

    def test_diving_jump_step(self):
        """DIVING: peek=1.5 → multiplier=1.5 passed to _move_perpendicular."""
        nav = self._nav_diving()
        with patch.object(nav, '_peek_step', return_value=1.5):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=False, multiplier=1.5)

    def test_diving_aborts_on_ocean(self):
        """DIVING: peek=None (ocean ahead) → shift and start RETURNING."""
        nav = self._nav_diving()
        with patch.object(nav, '_peek_step', return_value=None):
            with patch.object(nav, '_shift_click') as mock_shift:
                nav.step()
        mock_shift.assert_called_once()
        assert nav._state == 'RETURNING'
        assert nav._return_steps == 17  # inland_steps=2 + 15 safety

    def test_returning_normal_step(self):
        """RETURNING: peek=1.0 → _move_perpendicular(toward_water=True, multiplier=1.0)."""
        nav = self._nav_returning()
        with patch.object(nav, '_peek_step', return_value=1.0):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=True, multiplier=1.0)
        assert nav._state == 'RETURNING'

    def test_returning_jump_step(self):
        """RETURNING: peek=1.5 → multiplier=1.5 passed to _move_perpendicular."""
        nav = self._nav_returning()
        with patch.object(nav, '_peek_step', return_value=1.5):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=True, multiplier=1.5)

    def test_returning_stops_at_coast(self):
        """RETURNING: peek=None (coast boundary) → shift + HOMING."""
        nav = self._nav_returning()
        with patch.object(nav, '_peek_step', return_value=None):
            with patch.object(nav, '_shift_click') as mock_shift:
                nav.step()
        mock_shift.assert_called_once()
        assert nav._state == 'HOMING'

    def test_diving_jump_2x(self):
        """DIVING: peek=2.0 → multiplier=2.0 passed to _move_perpendicular."""
        nav = self._nav_diving()
        with patch.object(nav, '_peek_step', return_value=2.0):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=False, multiplier=2.0)

    def test_returning_jump_2x(self):
        """RETURNING: peek=2.0 → multiplier=2.0 passed to _move_perpendicular."""
        nav = self._nav_returning()
        with patch.object(nav, '_peek_step', return_value=2.0):
            with patch.object(nav, '_move_perpendicular') as mock_move:
                nav.step()
        mock_move.assert_called_once_with(toward_water=True, multiplier=2.0)
