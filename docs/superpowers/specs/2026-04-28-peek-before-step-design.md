# Peek-Before-Step — Design Spec
**Date:** 2026-04-28
**Status:** Approved

---

## Principle

Before every physical joystick click (DIVING or RETURNING), read the minimap in the movement direction.
If water is detected — jump over it with a scaled step. If 3 screens of water (ocean) — stop/abort.

**Same rule forward and backward. No blind movement.**

---

## New Method: `_peek_step(direction_vec) → float | None`

Grabs minimap (with footprint overlay), analyzes direction in 3 passes:

```
radius=30 (1 screen):  land_px > 0  → return 1.0   (land immediate, normal step)
radius=60 (2 screens): land_px > 0  → return 1.5   (land at 1-2 screens, jump over 1 screen water)
radius=90 (3 screens): land_px > 0  → return 2.0   (land at 2-3 screens, jump over 2 screens water)
all radii: land_px == 0             → return None   (ocean / coast boundary)
```

Trigger for water detection: `land_px == 0 AND water_px > self.min_water_px` at current radius.
If neither land nor significant water at radius=30 → return 1.0 (safe to step, likely edge of map or coast right here).

```python
def _peek_step(self, direction_vec: tuple) -> float | None:
    from minimap_reader import analyze_forward_zone
    mm = self._grab_minimap()
    
    near = analyze_forward_zone(mm, direction_vec, radius=30,
                                ocean_land_ratio=self.ocean_land_ratio,
                                min_water_px=self.min_water_px)
    if near['land_px'] > 0 or near['water_px'] <= self.min_water_px:
        return 1.0
    
    mid = analyze_forward_zone(mm, direction_vec, radius=60,
                               ocean_land_ratio=self.ocean_land_ratio,
                               min_water_px=self.min_water_px)
    if mid['land_px'] > 0:
        return 1.5
    
    far = analyze_forward_zone(mm, direction_vec, radius=90,
                               ocean_land_ratio=self.ocean_land_ratio,
                               min_water_px=self.min_water_px)
    if far['land_px'] > 0:
        return 2.0
    
    return None  # ocean (DIVING) or coast boundary (RETURNING)
```

---

## `_move_perpendicular` — add multiplier param

```python
def _move_perpendicular(self, toward_water: bool, multiplier: float = 1.0) -> None:
    iv = self._inland_vec
    dx, dy = (iv[0], iv[1]) if not toward_water else (-iv[0], -iv[1])
    self._click_vec(dx * multiplier, dy * multiplier,
                    label='dive' if not toward_water else 'return')
```

---

## DIVING phase changes

Replace:
```python
self._move_perpendicular(toward_water=False)
self._inland_steps += 1
```

With:
```python
mult = self._peek_step(self._inland_vec)
if mult is None:
    # Ocean ahead mid-dive → abort, start returning
    self._shift_click()
    self._state             = 'RETURNING'
    self._return_steps      = self._inland_steps + 15
    self._steps_since_shift = 0
    return True
self._move_perpendicular(toward_water=False, multiplier=mult)
self._inland_steps += 1
```

---

## RETURNING phase changes

Replace:
```python
at_coast = is_water or self._is_at_coast_now()
cap_hit  = self._return_steps <= 0
if at_coast or cap_hit:
    self._shift_click()
    self._state = 'HOMING'
    ...
    return True
self._return_steps -= 1
self._move_perpendicular(toward_water=True)
```

With:
```python
seaward = (-self._inland_vec[0], -self._inland_vec[1])
mult    = self._peek_step(seaward)
cap_hit = self._return_steps <= 0
if mult is None or cap_hit:
    # Coast boundary reached (or safety cap) → shift + HOMING
    self._shift_click()
    self._state        = 'HOMING'
    self._inland_steps = 0
    self._homing_steps = 0
    return True
self._return_steps -= 1
self._move_perpendicular(toward_water=True, multiplier=mult)
```

---

## What Does NOT Change

| Component | Status |
|-----------|--------|
| HOMING phase | unchanged |
| `_inland_vec` detection & EMA | unchanged |
| Angular damper | unchanged |
| Footprint overlap check (HOMING→DIVING) | unchanged |
| Ocean check at HOMING→DIVING | unchanged |
| `force_shift_after` safety wall | unchanged |
| `return_steps` safety cap | kept as backup |

---

## Tests Required

- `test_peek_step_land_immediate` — radius=30 has land → 1.0
- `test_peek_step_land_mid` — radius=30 no land/water, radius=60 has land → 1.5
- `test_peek_step_land_far` — radius=60 no land, radius=90 has land → 2.0
- `test_peek_step_ocean` — all radii no land, water at r=30 → None
- `test_peek_step_no_water_no_land` — no water AND no land at r=30 → 1.0 (safe step)
- `test_diving_jumps_with_multiplier` — peek=1.5 → _move_perpendicular called with multiplier=1.5
- `test_diving_aborts_on_ocean` — peek=None → state=RETURNING
- `test_returning_jumps_with_multiplier` — peek=1.5 → move called with 1.5
- `test_returning_stops_at_coast` — peek=None → state=HOMING
- Regression: 47 existing tests green
