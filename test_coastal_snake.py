# test_coastal_snake.py
"""TDD tests for CoastalSnakeNavigator — hard-corridor lawnmower."""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from navigator import CoastalSnakeNavigator


# ── helpers ───────────────────────────────────────────────────────────────

def _info(is_at_coast=False, is_ocean=False, water_px=0, land_px=100):
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
            nav.step()
        assert nav._state == 'DIVING'

    def test_diving_increments_step_counter(self):
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_vec = (1.0, 0.0)
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
        with patch.object(nav, '_is_at_coast_now', return_value=False):
            nav.step()
        args = nav._click_vec.call_args[0]
        assert args[0] < 0, "Return step should click negative inland direction"

    def test_returning_stops_when_coast_detected(self):
        """RETURNING stops when is_at_coast regardless of remaining step count."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 5
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_is_at_coast_now', return_value=True):
            nav.step()
        assert nav._state == 'HOMING'

    def test_returning_stops_at_safety_cap(self):
        """RETURNING stops at safety cap even if coast not detected (curved coast)."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 0
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_is_at_coast_now', return_value=False):
            nav.step()
        assert nav._state == 'HOMING'

    def test_returning_does_not_update_inland_vec(self):
        """inland_vec must stay frozen during RETURNING — no angle recalculation."""
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._return_steps = 3
        nav._inland_vec = (1.0, 0.0)   # frozen dive direction
        original_vec = nav._inland_vec
        with patch.object(nav, '_is_at_coast_now', return_value=False):
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
        with patch.object(nav, '_is_at_coast_now', return_value=True):
            nav.step()
        nav._click_vec.assert_called_once()
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
            nav.step()
        assert nav._state == 'DIVING'

    def test_homing_dives_when_max_steps_but_land_ahead(self):
        nav = make_navigator()
        nav._state = 'HOMING'
        nav._homing_steps = 10
        with patch.object(nav, '_read_minimap',
                          return_value=_info(water_px=50, land_px=150)):
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

class TestBlindReturnPhase:
    """RETURNING is blind for first max_inland-1 steps — ignores rivers."""

    def test_blind_steps_set_when_entering_returning(self):
        """DIVING→RETURNING cardinal: blind = max_inland - 1 (full)."""
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_steps = 5
        nav._inland_vec = (1.0, 0.0)   # pure cardinal
        nav._shift_vec  = (0.0, 1.0)
        nav.step()
        assert nav._state == 'RETURNING'
        assert nav._return_blind_steps == 4   # max_inland - 1

    def test_blind_steps_halved_for_diagonal_45(self):
        """DIVING→RETURNING 45° diagonal: blind = round((max_inland-1)*0.5)."""
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_steps = 5
        nav._inland_vec = (0.707, 0.707)   # 45° diagonal
        nav._shift_vec  = (-0.707, 0.707)
        nav.step()
        assert nav._state == 'RETURNING'
        assert nav._return_blind_steps == 2   # round(4 * 0.5)

    def test_blind_steps_interpolated_for_mid_angle(self):
        """DIVING→RETURNING ~26° angle: blind interpolated smoothly."""
        import math
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_steps = 5
        angle = math.radians(26)
        nav._inland_vec = (math.cos(angle), math.sin(angle))
        nav._shift_vec  = (-math.sin(angle), math.cos(angle))
        nav.step()
        assert nav._state == 'RETURNING'
        # ratio = tan(26°) ≈ 0.488, factor = 1 - 0.488*0.5 ≈ 0.756, blind = round(4*0.756) = 3
        assert nav._return_blind_steps == 3

    def test_coast_detection_skipped_during_blind_phase(self):
        """_is_at_coast_now must NOT be called while blind_steps > 0."""
        nav = make_navigator(max_inland=5)
        nav._state = 'RETURNING'
        nav._return_steps = 8
        nav._return_blind_steps = 3
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_is_at_coast_now', return_value=True) as mock_coast:
            nav.step()
        mock_coast.assert_not_called()
        assert nav._state == 'RETURNING', "Must stay RETURNING during blind phase"

    def test_blind_steps_decrements_each_return_step(self):
        """Each RETURNING step decrements _return_blind_steps by 1."""
        nav = make_navigator(max_inland=5)
        nav._state = 'RETURNING'
        nav._return_steps = 8
        nav._return_blind_steps = 3
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_is_at_coast_now', return_value=False):
            nav.step()
        assert nav._return_blind_steps == 2

    def test_coast_detection_active_after_blind_phase(self):
        """After blind phase ends (_return_blind_steps=0), coast IS checked."""
        nav = make_navigator(max_inland=5)
        nav._state = 'RETURNING'
        nav._return_steps = 5
        nav._return_blind_steps = 0   # blind phase over
        nav._inland_vec = (1.0, 0.0)
        with patch.object(nav, '_is_at_coast_now', return_value=True) as mock_coast:
            nav.step()
        mock_coast.assert_called_once()
        assert nav._state == 'HOMING'

    def test_river_does_not_abort_returning_during_blind_phase(self):
        """River (coast=True) during blind phase must NOT trigger shift+HOMING."""
        nav = make_navigator(max_inland=5)
        nav._state = 'RETURNING'
        nav._return_steps = 7   # max_inland + 2
        nav._return_blind_steps = 4   # max_inland - 1
        nav._inland_vec = (1.0, 0.0)
        # Simulate coast detection True (river) during all blind steps
        with patch.object(nav, '_is_at_coast_now', return_value=True):
            for _ in range(4):   # exhaust blind steps
                nav.step()
        assert nav._state == 'RETURNING', "River must not abort RETURNING during blind phase"
        # Now blind phase done — next step fires vision → HOMING
        with patch.object(nav, '_is_at_coast_now', return_value=True):
            nav.step()
        assert nav._state == 'HOMING'

    def test_vision_phase_has_generous_cap(self):
        """Vision phase = _return_steps - _return_blind_steps = (max_inland+15) - (max_inland-1) = 16."""
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_steps = 5
        nav._inland_vec = (1.0, 0.0)
        nav._shift_vec  = (0.0, 1.0)
        nav.step()
        vision_steps = nav._return_steps - nav._return_blind_steps
        assert vision_steps == 16, \
            f"Expected 16 vision steps (generous safety cap), got {vision_steps}"

    def test_bot_keeps_walking_until_coast_found_in_vision_phase(self):
        """Bot walks multiple vision steps until coast is detected — no early exit."""
        nav = make_navigator(max_inland=5)
        nav._state = 'RETURNING'
        nav._return_steps = 20
        nav._return_blind_steps = 0   # vision phase active
        nav._inland_vec = (1.0, 0.0)
        # Coast not found for 5 steps, found on step 6
        responses = [False, False, False, False, False, True]
        with patch.object(nav, '_is_at_coast_now', side_effect=responses):
            for i in range(5):
                nav.step()
                assert nav._state == 'RETURNING', f"Should stay RETURNING on step {i+1}"
            nav.step()
        assert nav._state == 'HOMING', "Should reach HOMING after coast finally found"

    def test_blind_steps_zero_for_max_inland_one(self):
        """With max_inland=1: blind_steps=0 (no blind phase, always use vision)."""
        nav = make_navigator(max_inland=1)
        nav._state = 'DIVING'
        nav._inland_steps = 1
        nav._inland_vec = (1.0, 0.0)
        nav._shift_vec  = (0.0, 1.0)
        nav.step()
        assert nav._state == 'RETURNING'
        assert nav._return_blind_steps == 0

    def test_reset_clears_blind_steps(self):
        """reset() must zero _return_blind_steps."""
        nav = make_navigator(max_inland=5)
        nav._return_blind_steps = 4
        nav.reset()
        assert nav._return_blind_steps == 0
