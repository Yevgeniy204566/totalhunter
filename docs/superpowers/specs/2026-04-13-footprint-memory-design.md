# Footprint Memory — Design Spec
**Date:** 2026-04-13  
**Status:** Approved

## Problem

CoastalSnakeNavigator circles near the coast — it revisits the same areas because it has no memory of where it has been. The bot needs to treat recently visited areas like obstacles (similar to water) so it is forced to keep progressing in one direction along the coast.

## Solution

Overlay a virtual **footprint canvas** (step-space grid with timestamps) onto the real minimap image before passing it to existing analysis functions. Footprint cells are painted as blue pixels — identical to water pixels — so `analyze_forward_zone()` and `detect_coast_angle()` treat them as obstacles without any changes.

```
Real minimap (BGR)         Virtual footprint canvas
  [water = blue]     +       [recent steps = blue]
  [land  = green]            [old/clear    = black]
        ↓                           ↓
        └──────── cv2 overlay ──────┘
                     ↓
           merged_minimap (BGR)
                     ↓
          analyze_forward_zone()   ← unchanged
          detect_coast_angle()     ← unchanged
```

## Components

### 1. `FootprintCanvas` (new class in `navigator.py`)

**Grid:** `np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.float64)` — each cell stores Unix timestamp of last visit (0 = never visited).  
**GRID_SIZE:** 401 (201 cells each side from center → supports ~200 steps of travel in any direction).  
**Current position:** `(cx, cy)` integer cell index, starts at `(200, 200)`.

**Methods:**
- `record(dx_step, dy_step)` — move position by step vector, stamp current cell with `time.time()`
- `render_overlay(minimap_shape, ttl_sec, pixels_per_step)` → `np.ndarray` (BGR, same size as minimap) — renders a blue-pixel image of cells within TTL window, centered on current position
- `reset()` — clears grid and resets position to center

**Step → pixel conversion:**  
`pixels_per_step` = `minimap_size / VISIBLE_STEPS` where `VISIBLE_STEPS = 9` (empirical — minimap shows ~9 steps across at default zoom).  
Each cell is rendered as a filled circle with radius `max(2, pixels_per_step // 2)`.

**Footprint color:** `(180, 100, 30)` BGR — matches `WATER_HSV` blue range so `get_land_water_masks` reliably detects it as water.

### 2. Overlay merge in `CoastalSnakeNavigator._grab_minimap()`

After grabbing the live minimap, overlay footprint pixels:

```python
def _grab_minimap(self) -> np.ndarray:
    mm = get_minimap_snapshot(self.center_x, self.center_y)
    if self._footprint_enabled:
        overlay = self._footprint.render_overlay(
            mm.shape, self._footprint_ttl, self._pixels_per_step)
        mask = overlay.any(axis=2)          # non-black pixels = footprints
        mm[mask] = overlay[mask]            # paint over minimap
    return mm
```

### 3. Record step in `CoastalSnakeNavigator.step()`

After every joystick click, call `self._footprint.record(dx, dy)` with the direction vector rounded to `(-1, 0, 1)` per axis.

### 4. New constructor parameters

```python
footprint_ttl: float = 120.0    # seconds, range 10–300
footprint_enabled: bool = True
pixels_per_step: int = 20       # auto-calculated from minimap size
```

### 5. GUI slider in `main.py`

New slider in the navigation frame (alongside `nav_inland_slider`, `nav_ocean_slider`, `nav_waterpx_slider`):

- **Label:** `Память следов (сек)` / `Footprint TTL (sec)`  
- **Range:** 10 – 300, step 1, default 120  
- **Key in `gui_config.json`:** `nav_footprint_ttl`
- Passed through `engine.py` → `PacmanEngine` → `CoastalSnakeNavigator`

## Data Flow

```
step() called
  → _grab_minimap()
       → get_minimap_snapshot()   [live screen]
       → footprint.render_overlay()  [virtual canvas]
       → overlay merge
       → returns merged BGR image
  → detect_coast_angle(merged)
  → analyze_forward_zone(merged, ...)
  → click joystick direction
  → footprint.record(dx, dy)
```

## Edge Cases

- **Grid overflow:** if bot travels > 200 steps from start, `record()` clamps position to grid bounds — effectively the oldest trail corner becomes permanent until `reset()`. This is acceptable; `reset()` is called every `reset_minutes`.
- **Reset:** `CoastalSnakeNavigator.reset()` also calls `self._footprint.reset()` — clears all trails.
- **footprint_enabled = False:** overlay skipped entirely, backward-compatible with existing behavior.
- **TTL = 10s:** effectively no memory (trail disappears almost immediately). TTL = 300s = 5-min wall behind bot.

## Testing

New file: `test_footprint_canvas.py`

- `test_record_moves_position` — position advances correctly
- `test_record_stamps_cell` — visited cell has recent timestamp
- `test_render_overlay_shape` — output matches minimap shape
- `test_render_overlay_blue_pixels` — visited cells render as blue
- `test_render_overlay_expired` — cells older than TTL render as black
- `test_reset_clears_grid` — reset zeroes all cells
- `test_grid_clamp` — no IndexError when position hits grid edge
- `test_overlay_detected_as_water` — run `get_land_water_masks` on overlay, verify water_px > 0

## Files Changed

| File | Change |
|---|---|
| `navigator.py` | Add `FootprintCanvas` class; modify `CoastalSnakeNavigator.__init__`, `_grab_minimap`, `step`, `reset` |
| `engine.py` | Pass `footprint_ttl` param through to navigator |
| `main.py` | Add `nav_footprint_ttl` slider in nav_frame |
| `gui_config.json` | Add `nav_footprint_ttl: 120` |
| `test_footprint_canvas.py` | New — 8 unit tests |
