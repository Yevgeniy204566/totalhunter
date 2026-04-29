# Dynamic Beacon V2 — Design Spec
**Date:** 2026-04-29
**Status:** Approved (Sections 1-4 + Gemini critical fixes)

---

## Context

Three days of failed RETURNING improvements (see `Краш-Клод.md`). Root causes:
- Canvas drift from fractional steps → wrong beacon position
- `is_water` false stops on rivers
- `pixels_per_step=20` hardcode → 67% position error

**This spec introduces blind return + visual landing as separate phases.**
`navigator.py` (stable base 536772f) is never touched.

---

## Section 1: Files

| File | Action |
|---|---|
| `navigator.py` | **UNCHANGED** — stable base 536772f |
| `navigator_beacon.py` | **NEW** — `CoastalSnakeNavigatorBeacon(CoastalSnakeNavigator)` |
| `engine.py` | Add `use_beacon: bool` flag — selects navigator class |
| `gui_config.json` | Add `"use_beacon": false` key — user toggle without code |
| `test_coastal_snake_beacon.py` | **NEW** — beacon-only tests |

**Rollback:** Set `use_beacon=false` in `gui_config.json` → instantly back to old navigator.

---

## Section 2: State Machine

Old single `RETURNING` state replaced by three phases:

```
HOMING ──► DIVING ──(inland_steps >= max)──► _place_dynamic_beacon()
                                                      │
                                               _shift_click()
                                                      │
                                             RETURNING_BLIND
                                                      │
                              (canvas_dist_to_beacon < 1.2 * pixels_per_step)
                                                      │
                                             RETURNING_SCAN ──(cap_hit)──► shift → HOMING
                                                      │
                                    (HSV magenta found near minimap centre)
                                                      │
                                             RETURNING_BEACON ──(cap_hit)──► shift → HOMING
                                                      │
                                    (minimap_dist_to_beacon < 5px)
                                                      │
                                               shift_click() → HOMING
```

Every safety-cap path ends with `shift → HOMING`. The bot never hangs.

---

## Section 3: New Data Fields

Added to `__init__`:

```python
self._beacon_grid:    tuple[float, float] | None = None
self._bot_gcx:        float = 0.0   # canvas grid X (step-space, not pixels)
self._bot_gcy:        float = 0.0   # canvas grid Y
self._pixels_per_step: int  = pixels_per_step   # nav_pps from autocalibration
```

**`_bot_gcx/y` reset rules (Gemini fix #2):**
- Zeroed in `reset()`
- Zeroed at every `DIVING_START` (HOMING→DIVING transition) — prevents drift accumulation across multiple dives

---

## Section 4: Beacon Placement — `_place_dynamic_beacon()`

Called once at `DIVING → RETURNING_BLIND` transition.

```python
def _place_dynamic_beacon(self):
    sv = self._shift_vec                  # shift direction (⊥ to inland_vec)
    bx = self._bot_gcx + 2 * sv[0]
    by = self._bot_gcy + 2 * sv[1]

    # Ground check: if beacon falls on water, iterate Y ±5px (Gemini fix #1)
    mm = self._grab_minimap()
    limit = 20
    for i in range(limit):
        px = int(mm.shape[1]//2 + (bx - self._bot_gcx) * self._pixels_per_step)
        py = int(mm.shape[0]//2 + (by - self._bot_gcy) * self._pixels_per_step)
        # _is_land_at: check land_mask (from get_land_water_masks) at given pixel coord
    if self._is_land_at(mm, px, py):  # see implementation: land_mask[py, px] > 0
            break
        # alternate up/down: +5, -5, +10, -10, +15, -15, ...
        sign = 1 if i % 2 == 0 else -1
        by = (self._bot_gcy + 2 * sv[1]) + sign * (i // 2 + 1) * (5 / self._pixels_per_step)
    else:
        # Fallback: default position + warning log (never hang the thread)
        import logging
        logging.warning("_place_dynamic_beacon: land not found in 20 iterations, using default")
        bx = self._bot_gcx + 2 * sv[0]
        by = self._bot_gcy + 2 * sv[1]

    self._beacon_grid = (bx, by)
```

---

## Section 5: Minimap Override — `_grab_minimap()`

**Gemini fix #3:** Beacon is drawn on the INTERNAL processing buffer — the bot reads it via HSV, not just screen display.

```python
def _grab_minimap(self) -> np.ndarray:
    mm = super()._grab_minimap()          # footprints from parent (red overlay)

    if self._beacon_grid is not None:
        bx, by = self._beacon_grid
        h, w = mm.shape[:2]
        cx, cy = w // 2, h // 2
        rel_x = int((bx - self._bot_gcx) * self._pixels_per_step)
        rel_y = int((by - self._bot_gcy) * self._pixels_per_step)
        px = max(0, min(w - 1, cx + rel_x))
        py = max(0, min(h - 1, cy + rel_y))
        # Magenta (BGR 255,0,255) drawn ON TOP of footprints
        cv2.circle(mm, (px, py), 6, (255, 0, 255), -1)

    return mm
```

---

## Section 6: Beacon Detection — `_find_beacon_on_minimap(mm)`

HSV magenta range (no PNG templates — AP-2):

```python
def _find_beacon_on_minimap(self, mm: np.ndarray) -> tuple[int,int] | None:
    hsv = cv2.cvtColor(mm, cv2.COLOR_BGR2HSV)
    # Magenta: H=140-170, S>150, V>100
    mask = cv2.inRange(hsv, np.array([140, 150, 100]), np.array([170, 255, 255]))
    pts = np.column_stack(np.where(mask > 0))
    if len(pts) < 5:
        return None
    cy_m = float(pts[:, 0].mean())
    cx_m = float(pts[:, 1].mean())
    return (int(cx_m), int(cy_m))
```

Player is always at minimap centre `(w//2, h//2)` — no HSV detection needed.

---

## Section 7: Canvas Distance Trigger

```python
def _canvas_dist_to_beacon(self) -> float:
    if self._beacon_grid is None:
        return float('inf')
    bx, by = self._beacon_grid
    return float(np.hypot(bx - self._bot_gcx, by - self._bot_gcy))
```

Trigger: `_canvas_dist_to_beacon() * pixels_per_step < minimap_radius * 1.2`

Where `minimap_radius = 90` (half of 180px snapshot).
In steps: `_canvas_dist_to_beacon() < 90 * 1.2 / pixels_per_step` (≈9 steps at pps=12).
This ensures the beacon circle is within the visible minimap area before HSV scan starts.

---

## Section 8: `_click_vec()` Override

Track canvas position on every movement (needed for beacon rendering):

```python
def _click_vec(self, dx: float, dy: float):
    super()._click_vec(dx, dy)
    norm = np.hypot(dx, dy)
    if norm > 0:
        self._bot_gcx += dx / norm
        self._bot_gcy += dy / norm
```

---

## Section 9: engine.py Changes

```python
# __init__ signature addition:
use_beacon:      bool = False,
pixels_per_step: int  = 20,

# Navigator selection:
if use_beacon:
    from navigator_beacon import CoastalSnakeNavigatorBeacon
    self.joystick = CoastalSnakeNavigatorBeacon(
        ..., pixels_per_step=pixels_per_step
    )
else:
    self.joystick = CoastalSnakeNavigator(...)
```

`gui_config.json` gets `"use_beacon": false` key. `engine.py` reads it at startup.

---

## Section 10: Tests

**All 42 existing tests remain green** — `navigator.py` unchanged.

New tests in `test_coastal_snake_beacon.py`:

| # | Test | What it verifies |
|---|---|---|
| 1 | `test_place_beacon_on_land` | Beacon placed 2 steps in shift direction |
| 2 | `test_place_beacon_shifts_off_water` | Water → Y-iteration finds land |
| 3 | `test_place_beacon_fallback_after_20` | 20 iterations exhausted → default + warning |
| 4 | `test_returning_blind_ignores_beacon` | `_find_beacon_on_minimap` NOT called during blind phase |
| 5 | `test_canvas_dist_trigger` | dist < 1.2 → state = RETURNING_SCAN |
| 6 | `test_scan_calls_hsv_detection` | RETURNING_SCAN calls `_find_beacon_on_minimap` each step |
| 7 | `test_beacon_homing_moves_by_vector` | RETURNING_BEACON clicks toward beacon centroid |
| 8 | `test_beacon_reached_triggers_shift` | minimap dist < 5px → shift → HOMING |
| 9 | `test_safety_cap_terminates_scan` | cap_hit in RETURNING_SCAN → shift → HOMING |
| 10 | `test_safety_cap_terminates_homing` | cap_hit in RETURNING_BEACON → shift → HOMING |
| 11 | `test_reset_clears_beacon` | `reset()` → `_beacon_grid = None`, `_bot_gcx/y = 0` |
| 12 | `test_bot_gcx_reset_at_dive_start` | HOMING→DIVING → `_bot_gcx/y` zeroed |
| 13 | `test_magenta_drawn_in_processing_buffer` | `_grab_minimap()` returns frame with magenta pixels |
| 14 | `test_engine_use_beacon_flag` | `use_beacon=True` → `CoastalSnakeNavigatorBeacon` instantiated |
| 15 | `test_old_navigator_42_tests_unaffected` | Regression — all 42 old tests pass |

---

## Anti-Patterns Respected

| AP | Rule | How respected |
|---|---|---|
| AP-2 | No PNG template | HSV-only beacon detection |
| AP-32 | No `is_water` in RETURNING | All three RETURNING phases use zero water checks |
| AP-33 | Stop only on visual contact | `minimap_dist < 5px` is the only stop condition |
| AP-34 | No hardcoded pixels_per_step | `nav_pps` from autocalibration passed as param |

---

## What Does NOT Change

| Component | Status |
|---|---|
| `navigator.py` entire file | Unchanged |
| HOMING phase | Inherited unchanged |
| DIVING phase | Inherited, one addition: `_bot_gcx/y` zeroed at entry |
| `_shift_click()` | Inherited unchanged |
| `_move_perpendicular()` | Inherited unchanged |
| Angular damper | Inherited unchanged |
| Footprint overlap check | Inherited unchanged |
| Ocean column skip | Inherited unchanged |
| All 42 existing tests | Green |
