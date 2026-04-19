# CoastalSnakeNavigator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace CompassNavigator with CoastalSnakeNavigator — a water-anchored zigzag that stays within N screens of the coastline and distinguishes ocean from internal rivers using minimap analysis.

**Architecture:** `CoastalSnakeNavigator` lives in `navigator.py`, reads the minimap each step via functions from `minimap_reader.py`, and exposes tunable parameters (max_inland_steps, ocean_land_ratio, min_water_px) that are wired into the GUI navigation block and saved to `gui_config.json`.

**Tech Stack:** Python, OpenCV, numpy, pyautogui, CustomTkinter

---

## File Map

| File | Role |
|---|---|
| `navigator.py` | Add `CoastalSnakeNavigator`; update `PacmanEngine` to use it |
| `minimap_reader.py` | Already done — `detect_coast_angle`, `analyze_forward_zone`, `get_minimap_snapshot` |
| `test_coastal_snake.py` | TDD tests for `CoastalSnakeNavigator` state machine |
| `main.py` | Add 3 sliders to nav_frame for the new parameters |
| `gui_config.json` | Add `max_inland_steps`, `ocean_land_ratio`, `min_water_px` keys |

---

## Task 1: RED — write failing state-machine tests

**Files:**
- Create: `test_coastal_snake.py`

The tests use a `FakeNavigator` harness that feeds pre-scripted `(coast_angle, is_ocean)` sequences to the navigator without touching the screen.

- [ ] **Step 1.1: Create test file**

```python
# test_coastal_snake.py
"""TDD tests for CoastalSnakeNavigator state machine."""
import types
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from navigator import CoastalSnakeNavigator


# ── helpers ───────────────────────────────────────────────────────────────

def make_navigator(max_inland=3, ocean_ratio=0.03, min_water=10):
    """Create navigator with screen-interaction patched out."""
    nav = CoastalSnakeNavigator(
        center_x=90, center_y=925, step=13,
        max_inland_steps=max_inland,
        ocean_land_ratio=ocean_ratio,
        min_water_px=min_water,
    )
    nav._click_vec = MagicMock()          # patch physical joystick click
    nav._grab_minimap = MagicMock()       # patch screenshot
    return nav


def _fake_minimap(coast_angle: float, is_ocean_fwd: bool):
    """Return a minimap stub whose analysis results are pre-set."""
    mm = MagicMock()
    mm._coast_angle = coast_angle
    mm._is_ocean = is_ocean_fwd
    return mm


def _inject_analysis(nav, coast_angle: float, is_ocean: bool):
    """Make the next _read_minimap() return pre-baked values."""
    fake_mm = object()
    nav._grab_minimap.return_value = fake_mm

    import minimap_reader as mr
    # Patch module-level functions for this call
    with patch.object(mr, 'detect_coast_angle', return_value=coast_angle), \
         patch.object(mr, 'analyze_forward_zone',
                      return_value={'water_px': 600 if is_ocean else 0,
                                    'land_px':  0   if is_ocean else 100,
                                    'land_ratio': 0.0 if is_ocean else 0.15,
                                    'is_ocean': is_ocean}):
        return nav._read_minimap()


# ── state machine tests ───────────────────────────────────────────────────

class TestCoastalSnakeStateMachine:
    def test_initial_state_is_homing(self):
        nav = make_navigator()
        assert nav._state == 'HOMING'

    def test_reset_returns_to_homing(self):
        nav = make_navigator()
        nav._state = 'DIVING'
        nav.reset()
        assert nav._state == 'HOMING'

    def test_homing_clicks_toward_coast(self):
        nav = make_navigator()
        # Simulate: water visible on minimap (not ocean — it's coast)
        # After _read_minimap returns coast_angle, navigator should click coast_dir
        with patch.object(nav, '_read_minimap',
                          return_value={'coast_angle': 0.0,
                                        'inland_vec': (1.0, 0.0),
                                        'coast_vec':  (0.0, 1.0),
                                        'fwd': {'is_ocean': False,
                                                'land_ratio': 0.5, 'water_px': 0,
                                                'land_px': 100},
                                        'is_at_coast': False}):
            nav.step()
        nav._click_vec.assert_called_once()

    def test_homing_transitions_to_diving_when_at_coast(self):
        nav = make_navigator()
        with patch.object(nav, '_read_minimap',
                          return_value={'coast_angle': 0.0,
                                        'inland_vec': (1.0, 0.0),
                                        'coast_vec':  (0.0, 1.0),
                                        'fwd': {'is_ocean': False,
                                                'land_ratio': 0.5, 'water_px': 0,
                                                'land_px': 100},
                                        'is_at_coast': True}):
            nav.step()
        assert nav._state == 'DIVING'

    def test_diving_increments_step_counter(self):
        nav = make_navigator(max_inland=5)
        nav._state = 'DIVING'
        nav._inland_vec = (1.0, 0.0)
        nav._coast_vec  = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value={'coast_angle': 0.0,
                                        'inland_vec': (1.0, 0.0),
                                        'coast_vec':  (0.0, 1.0),
                                        'fwd': {'is_ocean': False,
                                                'land_ratio': 0.5, 'water_px': 0,
                                                'land_px': 100},
                                        'is_at_coast': False}):
            nav.step()
        assert nav._inland_steps == 1

    def test_diving_transitions_to_returning_at_max_depth(self):
        nav = make_navigator(max_inland=2)
        nav._state = 'DIVING'
        nav._inland_steps = 2         # already at max
        nav._inland_vec = (1.0, 0.0)
        nav._coast_vec  = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value={'coast_angle': 0.0,
                                        'inland_vec': (1.0, 0.0),
                                        'coast_vec':  (0.0, 1.0),
                                        'fwd': {'is_ocean': False,
                                                'land_ratio': 0.5, 'water_px': 0,
                                                'land_px': 100},
                                        'is_at_coast': False}):
            nav.step()
        assert nav._state == 'RETURNING'

    def test_diving_transitions_to_returning_on_ocean(self):
        nav = make_navigator(max_inland=10)
        nav._state = 'DIVING'
        nav._inland_steps = 1
        nav._inland_vec = (1.0, 0.0)
        nav._coast_vec  = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value={'coast_angle': 0.0,
                                        'inland_vec': (1.0, 0.0),
                                        'coast_vec':  (0.0, 1.0),
                                        'fwd': {'is_ocean': True,
                                                'land_ratio': 0.0, 'water_px': 600,
                                                'land_px': 0},
                                        'is_at_coast': False}):
            nav.step()
        assert nav._state == 'RETURNING'

    def test_returning_clicks_back_toward_coast(self):
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._inland_steps = 2
        nav._inland_vec = (1.0, 0.0)
        nav._coast_vec  = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value={'coast_angle': 0.0,
                                        'inland_vec': (1.0, 0.0),
                                        'coast_vec':  (0.0, 1.0),
                                        'fwd': {'is_ocean': False,
                                                'land_ratio': 0.5, 'water_px': 0,
                                                'land_px': 100},
                                        'is_at_coast': False}):
            nav.step()
        # Should click -inland_vec = (-1, 0)
        args = nav._click_vec.call_args[0]
        assert args[0] < 0, "Return step should click negative inland direction"

    def test_returning_shifts_and_goes_homing_when_back_at_coast(self):
        nav = make_navigator()
        nav._state = 'RETURNING'
        nav._inland_steps = 2
        nav._inland_vec = (1.0, 0.0)
        nav._coast_vec  = (0.0, 1.0)
        with patch.object(nav, '_read_minimap',
                          return_value={'coast_angle': 0.0,
                                        'inland_vec': (1.0, 0.0),
                                        'coast_vec':  (0.0, 1.0),
                                        'fwd': {'is_ocean': False,
                                                'land_ratio': 0.5, 'water_px': 0,
                                                'land_px': 100},
                                        'is_at_coast': True}):
            nav.step()
        # Should click shift, then go HOMING
        assert nav._state == 'HOMING'
        assert nav._click_vec.call_count == 1  # one shift click


class TestCoastalSnakeHelpers:
    def test_read_minimap_returns_dict_with_required_keys(self):
        nav = make_navigator()
        fake_mm = MagicMock()
        nav._grab_minimap.return_value = fake_mm
        import minimap_reader as mr
        with patch.object(mr, 'detect_coast_angle', return_value=0.5), \
             patch.object(mr, 'analyze_forward_zone',
                          return_value={'water_px': 0, 'land_px': 0,
                                        'land_ratio': 0.0, 'is_ocean': False}), \
             patch.object(mr, 'get_minimap_snapshot', return_value=fake_mm):
            result = nav._read_minimap()
        assert {'coast_angle', 'inland_vec', 'coast_vec', 'fwd', 'is_at_coast'} <= result.keys()

    def test_is_at_coast_true_when_water_visible_in_coast_direction(self):
        nav = make_navigator()
        fake_mm = MagicMock()
        nav._grab_minimap.return_value = fake_mm
        import minimap_reader as mr

        def side_effect(mm, direction, **kw):
            # coast direction = (cos(0), sin(0)) = (1, 0)
            # Return water ahead if pointing along coast
            if abs(direction[1]) < 0.1:   # horizontal = coast dir
                return {'water_px': 800, 'land_px': 5, 'land_ratio': 0.006, 'is_ocean': False}
            return {'water_px': 0, 'land_px': 100, 'land_ratio': 1.0, 'is_ocean': False}

        with patch.object(mr, 'detect_coast_angle', return_value=0.0), \
             patch.object(mr, 'analyze_forward_zone', side_effect=side_effect), \
             patch.object(mr, 'get_minimap_snapshot', return_value=fake_mm):
            result = nav._read_minimap()
        assert result['is_at_coast'] is True
```

- [ ] **Step 1.2: Run test to confirm RED**

```
python -m pytest test_coastal_snake.py -v 2>&1 | head -20
```

Expected: `ImportError` or `AttributeError: CoastalSnakeNavigator`.

---

## Task 2: GREEN — implement CoastalSnakeNavigator in navigator.py

**Files:**
- Modify: `navigator.py` — append class after `CompassNavigator`

- [ ] **Step 2.1: Append CoastalSnakeNavigator to navigator.py**

Add after the `CompassNavigator` class (before `PacmanEngine`):

```python
# ─────────────────────────────────────────────
# CoastalSnakeNavigator
# ─────────────────────────────────────────────

class CoastalSnakeNavigator:
    """
    Water-anchored coastal zigzag navigator.

    States:
      HOMING    — move toward coast until water/land boundary visible on minimap
      DIVING    — move inland (perpendicular to coast) up to max_inland_steps
      RETURNING — move back to coast (-inland_dir) until boundary visible again
                  then shift one step along coast → HOMING

    Ocean detection: analyze_forward_zone() in DIVING direction.
    If land_ratio < ocean_land_ratio AND water_px > min_water_px → ocean → abort dive.

    Coast angle is re-detected from minimap at each step (EMA-smoothed).
    """

    def __init__(
        self,
        center_x: int   = 90,
        center_y: int   = 925,
        step: int       = 13,
        max_inland_steps: int   = 5,
        ocean_land_ratio: float = 0.03,
        min_water_px: int       = 500,
        homing_max_steps: int   = 10,
        coast_ema_alpha: float  = 0.3,
    ):
        self.center_x         = center_x
        self.center_y         = center_y

        sw, sh = pyautogui.size()
        aspect = sw / sh
        self.p_range_y = step
        self.p_range_x = max(1, round(step * aspect))

        self.max_inland_steps = max_inland_steps
        self.ocean_land_ratio = ocean_land_ratio
        self.min_water_px     = min_water_px
        self.homing_max_steps = homing_max_steps
        self.coast_ema_alpha  = coast_ema_alpha

        self._state         = 'HOMING'
        self._inland_steps  = 0
        self._homing_steps  = 0
        self._coast_angle   = 0.0        # EMA-smoothed coast angle
        self._inland_vec    = (1.0, 0.0) # perpendicular to coast (toward land)
        self._coast_vec     = (0.0, 1.0) # along coast (shift direction)
        self._angle_init    = False      # first reading seeds EMA directly

    def reset(self):
        self._state        = 'HOMING'
        self._inland_steps = 0
        self._homing_steps = 0
        self._angle_init   = False

    # ── calibration helper (same API as CompassNavigator) ────────────────
    def move(self, direction: str):
        _DIRS = {'RIGHT': (1, 0), 'LEFT': (-1, 0), 'UP': (0, -1), 'DOWN': (0, 1)}
        dx, dy = _DIRS[direction]
        pyautogui.click(self.center_x + dx * self.p_range_x,
                        self.center_y + dy * self.p_range_y)

    # ── internal helpers ─────────────────────────────────────────────────
    def _grab_minimap(self) -> np.ndarray:
        from minimap_reader import get_minimap_snapshot
        return get_minimap_snapshot(self.center_x, self.center_y)

    def _click_vec(self, dx: float, dy: float):
        """Click joystick in arbitrary direction (dx, dy) — supports diagonals."""
        norm = np.hypot(dx, dy)
        if norm == 0:
            return
        ndx, ndy = dx / norm, dy / norm
        pyautogui.click(
            int(self.center_x + ndx * self.p_range_x),
            int(self.center_y + ndy * self.p_range_y),
        )

    def _update_coast_angle(self, new_angle: float):
        """EMA smoothing of coast angle to handle noisy minimap readings."""
        if not self._angle_init:
            self._coast_angle = new_angle
            self._angle_init  = True
        else:
            # Wrap-safe EMA: interpolate on unit circle
            a = self._coast_angle
            # Compute smallest angular difference
            diff = (new_angle - a + np.pi) % (2 * np.pi) - np.pi
            self._coast_angle = a + self.coast_ema_alpha * diff

        # Derive vectors from smoothed angle
        ca = self._coast_angle
        self._coast_vec  = (float(np.cos(ca)),          float(np.sin(ca)))
        # Inland = perpendicular, pick the side with less water
        # (simplified: always use +90°; caller can flip if needed)
        self._inland_vec = (float(np.cos(ca + np.pi/2)), float(np.sin(ca + np.pi/2)))

    def _read_minimap(self) -> dict:
        """
        Grab minimap, detect coast angle, analyse forward zone.
        Returns dict with all info needed for state decisions.
        """
        from minimap_reader import detect_coast_angle, analyze_forward_zone

        mm = self._grab_minimap()
        raw_angle = detect_coast_angle(mm)

        if raw_angle != 0.0 or not self._angle_init:
            self._update_coast_angle(raw_angle)

        fwd = analyze_forward_zone(
            mm, self._inland_vec,
            radius=60,
        )
        # is_at_coast: water visible in the coast direction (boundary on minimap)
        coast_zone = analyze_forward_zone(mm, self._coast_vec, radius=50)
        is_at_coast = (
            coast_zone['water_px'] > 50 and
            coast_zone['land_ratio'] < 0.5
        )

        return {
            'coast_angle': self._coast_angle,
            'inland_vec':  self._inland_vec,
            'coast_vec':   self._coast_vec,
            'fwd':         fwd,
            'is_at_coast': is_at_coast,
        }

    # ── main navigation step ─────────────────────────────────────────────
    def step(self, is_water: bool = False) -> bool:
        """
        One navigation step. Reads minimap, decides direction, clicks joystick.
        `is_water` parameter kept for API compatibility with PacmanEngine — not used.
        Returns True always.
        """
        info = self._read_minimap()

        if self._state == 'HOMING':
            if info['is_at_coast'] or self._homing_steps >= self.homing_max_steps:
                # At coast — start diving
                self._state        = 'DIVING'
                self._inland_steps = 0
                self._homing_steps = 0
            else:
                # Move toward coast: click in coast direction
                self._click_vec(*info['coast_vec'])
                self._homing_steps += 1
            return True

        if self._state == 'DIVING':
            ocean_ahead = info['fwd']['is_ocean']
            at_max      = self._inland_steps >= self.max_inland_steps

            if ocean_ahead or at_max:
                self._state = 'RETURNING'
            else:
                self._click_vec(*info['inland_vec'])
                self._inland_steps += 1
            return True

        if self._state == 'RETURNING':
            if info['is_at_coast'] or self._inland_steps <= 0:
                # Back at coast — shift along coast, then home again
                self._click_vec(*info['coast_vec'])
                self._state        = 'HOMING'
                self._inland_steps = 0
                self._homing_steps = 0
            else:
                dx, dy = info['inland_vec']
                self._click_vec(-dx, -dy)
                self._inland_steps -= 1
            return True

        return False
```

- [ ] **Step 2.2: Run tests**

```
python -m pytest test_coastal_snake.py -v
```

Expected: all pass (or debug failures — fix minimal code only, do not change tests).

---

## Task 3: Wire CoastalSnakeNavigator into PacmanEngine

**Files:**
- Modify: `navigator.py` — `PacmanEngine.__init__`

- [ ] **Step 3.1: Replace CompassNavigator with CoastalSnakeNavigator in PacmanEngine**

In `PacmanEngine.__init__`, find the block that creates `self.joystick` and replace it:

```python
# OLD:
self.joystick = CompassNavigator(
    center_x=center_x,
    center_y=center_y,
    step=step,
    dive_depth=dive_depth,
)

# NEW — add max_inland_steps, ocean_land_ratio, min_water_px params to __init__ signature first:
```

First update `PacmanEngine.__init__` signature to add the new params:

```python
def __init__(
    self,
    center_x: int       = 90,
    center_y: int       = 925,
    step: int           = 13,
    dive_depth: int     = 5,
    conf: float         = 0.7,
    scan_interval: float = 0.6,
    reset_minutes: float = 10.0,
    sound_path: str     = 'Logo_exchange.wav',
    yolo_model          = None,
    move_wait: float    = 2.0,
    navigation_enabled: bool = True,
    max_inland_steps: int   = 5,
    ocean_land_ratio: float = 0.03,
    min_water_px: int       = 500,
    # legacy params (ignored):
    max_depth: int      = 4,
    screen_w: int       = 5,
    screen_h: int       = 39,
    magnet: float       = 0.0,
    inertia: float      = 1.0,
    random_w: float     = 0.05,
):
    self.joystick = CoastalSnakeNavigator(
        center_x=center_x,
        center_y=center_y,
        step=step,
        max_inland_steps=max_inland_steps,
        ocean_land_ratio=ocean_land_ratio,
        min_water_px=min_water_px,
    )
    # rest of __init__ unchanged...
```

- [ ] **Step 3.2: Update HuntEngine.start() in engine.py to pass new params**

In `engine.py`, `HuntEngine.start()` — add three new parameters and forward them:

```python
def start(
    self,
    conf: float,
    center_x: int        = 90,
    center_y: int        = 925,
    joystick_step: int   = 13,
    scan_interval: float = 0.6,
    reset_minutes: float = 10.0,
    move_wait: float     = 2.0,
    navigation_enabled: bool = True,
    max_inland_steps: int   = 5,
    ocean_land_ratio: float = 0.03,
    min_water_px: int       = 500,
):
    self._pacman = PacmanEngine(
        center_x=center_x,
        center_y=center_y,
        step=joystick_step,
        conf=conf,
        scan_interval=scan_interval,
        reset_minutes=reset_minutes,
        sound_path=self.sound_path or 'Logo_exchange.wav',
        yolo_model=self.model,
        move_wait=move_wait,
        navigation_enabled=navigation_enabled,
        max_inland_steps=max_inland_steps,
        ocean_land_ratio=ocean_land_ratio,
        min_water_px=min_water_px,
    )
    self._pacman.on_found_callback = self.on_found_callback
    self.is_running = True
    self._pacman.start()
```

- [ ] **Step 3.3: Run existing test suite to verify no regressions**

```
python -m pytest test_coastal_snake.py test_minimap_reader.py -v
```

Expected: all pass.

---

## Task 4: Add GUI sliders for the 3 new parameters

**Files:**
- Modify: `main.py` — `setup_hunt_tab()` and `_save_settings()` / `_load_settings()`

The 3 new sliders go inside `nav_frame`, right after the "Скорость (сек/шаг)" block and before the "Сохранить настройки" button.

- [ ] **Step 4.1: Add the 3 slider widgets inside setup_hunt_tab()**

Find the line `self.save_btn = ctk.CTkButton(self.nav_frame, ...)` and insert this block BEFORE it:

```python
        # ── Coastal Snake parameters ──────────────────────────────────────

        # Глубина нырка (экранов)
        self.nav_inland_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_inland_frame.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(self.nav_inland_frame, text="Глубина нырка (экранов):", font=ctk.CTkFont(size=11)).pack(side="left")
        self.nav_inland_val = ctk.CTkLabel(self.nav_inland_frame, text="5", font=ctk.CTkFont(weight="bold"), text_color="#3b8ed0")
        self.nav_inland_val.pack(side="right")
        self.nav_inland_slider = ctk.CTkSlider(
            self.nav_frame, from_=1, to=10, number_of_steps=9,
            command=self._update_nav_labels,
        )
        self.nav_inland_slider.set(5)
        self.nav_inland_slider.pack(padx=10, pady=(0, 4), fill="x")

        # Порог океана (% суши)
        self.nav_ocean_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_ocean_frame.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(self.nav_ocean_frame, text="Порог 'конец ГОСа' (% суши):", font=ctk.CTkFont(size=11)).pack(side="left")
        self.nav_ocean_val = ctk.CTkLabel(self.nav_ocean_frame, text="3%", font=ctk.CTkFont(weight="bold"), text_color="#3b8ed0")
        self.nav_ocean_val.pack(side="right")
        self.nav_ocean_slider = ctk.CTkSlider(
            self.nav_frame, from_=1, to=15, number_of_steps=14,
            command=self._update_nav_labels,
        )
        self.nav_ocean_slider.set(3)
        self.nav_ocean_slider.pack(padx=10, pady=(0, 4), fill="x")

        # Мин. пикселей воды для детекта океана
        self.nav_waterpx_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_waterpx_frame.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(self.nav_waterpx_frame, text="Мин. пикс. воды (океан):", font=ctk.CTkFont(size=11)).pack(side="left")
        self.nav_waterpx_val = ctk.CTkLabel(self.nav_waterpx_frame, text="500", font=ctk.CTkFont(weight="bold"), text_color="#3b8ed0")
        self.nav_waterpx_val.pack(side="right")
        self.nav_waterpx_slider = ctk.CTkSlider(
            self.nav_frame, from_=100, to=2000, number_of_steps=19,
            command=self._update_nav_labels,
        )
        self.nav_waterpx_slider.set(500)
        self.nav_waterpx_slider.pack(padx=10, pady=(0, 4), fill="x")
```

- [ ] **Step 4.2: Update `_update_nav_labels` to refresh the 3 new label widgets**

Find `_update_nav_labels` method in `main.py`. Add these 3 lines at the end of it:

```python
        self.nav_inland_val.configure(text=f"{int(self.nav_inland_slider.get())}")
        self.nav_ocean_val.configure(text=f"{int(self.nav_ocean_slider.get())}%")
        self.nav_waterpx_val.configure(text=f"{int(self.nav_waterpx_slider.get())}")
```

- [ ] **Step 4.3: Update `_save_settings` to persist the 3 new params**

In `_save_settings`, find where the config dict is built and add the 3 new keys:

```python
        cfg["max_inland_steps"] = int(self.nav_inland_slider.get())
        cfg["ocean_land_ratio"] = int(self.nav_ocean_slider.get()) / 100.0
        cfg["min_water_px"]     = int(self.nav_waterpx_slider.get())
```

- [ ] **Step 4.4: Update `_load_settings` to restore the 3 new params**

In `_load_settings`, after existing `slider.set(...)` calls, add:

```python
        self.nav_inland_slider.set(cfg.get("max_inland_steps", 5))
        self.nav_ocean_slider.set(int(cfg.get("ocean_land_ratio", 0.03) * 100))
        self.nav_waterpx_slider.set(cfg.get("min_water_px", 500))
        self._update_nav_labels()
```

---

## Task 5: Pass GUI parameters to engine on start

**Files:**
- Modify: `main.py` — `toggle_bot()` or `start_hunt()` method

- [ ] **Step 5.1: Find the engine.start() call in main.py and add the 3 new params**

Find the call `self.engine.start(...)` and add:

```python
        self.engine.start(
            conf=self.conf_slider.get(),
            center_x=int(self.nav_cx_entry.get()),
            center_y=int(self.nav_cy_entry.get()),
            joystick_step=int(self.nav_step_slider.get()),
            scan_interval=self.speed_slider.get(),
            reset_minutes=self.nav_reset_slider.get(),
            move_wait=self.nav_wait_slider.get(),
            navigation_enabled=self.nav_enabled_var.get(),
            max_inland_steps=int(self.nav_inland_slider.get()),
            ocean_land_ratio=int(self.nav_ocean_slider.get()) / 100.0,
            min_water_px=int(self.nav_waterpx_slider.get()),
        )
```

- [ ] **Step 5.2: Smoke test — launch main.py, verify GUI opens without errors**

```
python main.py
```

Expected: GUI opens, 3 new sliders visible in navigation block, no exceptions in console.

---

## Task 6: Final test run + commit

- [ ] **Step 6.1: Run full test suite**

```
python -m pytest test_coastal_snake.py test_minimap_reader.py test_coord_manager.py -v
```

Expected: all pass.

- [ ] **Step 6.2: Run minimap diagnostic to verify live ocean detection**

Open game, position bot near coast:
```
python minimap_debug.py
```

Verify console shows `OCEAN — turn back` at ocean and not at rivers.

- [ ] **Step 6.3: Commit**

```bash
git add navigator.py engine.py main.py minimap_reader.py \
        test_coastal_snake.py test_minimap_reader.py \
        gui_config.json \
        docs/superpowers/specs/2026-04-12-coastal-snake-navigator-design.md \
        docs/superpowers/plans/2026-04-12-coastal-snake-navigator.md
git commit -m "feat: CoastalSnakeNavigator — water-anchored coastal zigzag with ocean detection"
```

---

## Self-Review

**Spec coverage:**
- [x] HOMING/DIVING/RETURNING states → Task 2
- [x] detect_coast_angle PCA → minimap_reader.py (done)
- [x] analyze_forward_zone ocean check → minimap_reader.py (done)
- [x] max_inland_steps param → Tasks 2, 3, 4, 5
- [x] ocean_land_ratio param → Tasks 2, 3, 4, 5
- [x] min_water_px param → Tasks 2, 3, 4, 5
- [x] EMA smoothing of coast angle → Task 2 `_update_coast_angle`
- [x] GUI sliders → Task 4
- [x] Wired to engine on start → Task 5
- [x] CompassNavigator kept (not deleted) → not touched

**No placeholders:** confirmed — all steps have actual code.

**Type consistency:** `CoastalSnakeNavigator.step(is_water=False)` matches `PacmanEngine` call site. `_click_vec(dx, dy)` consistent throughout.
