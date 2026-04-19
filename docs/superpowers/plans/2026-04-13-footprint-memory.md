# Footprint Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `FootprintCanvas` that overlays visited-cell timestamps onto the live minimap as blue pixels, so `analyze_forward_zone` naturally avoids recently visited areas exactly like it avoids water.

**Architecture:** `FootprintCanvas` lives in `navigator.py` — a 401×401 grid of timestamps in step-space. `CoastalSnakeNavigator._grab_minimap()` overlays footprint pixels (BGR `(180,100,30)` — blue-dominant, detected as water) onto the real minimap before returning it. `_click_vec()` records each step. TTL slider (10–300 s, default 120) in GUI → through `engine.py` → `PacmanEngine` → `CoastalSnakeNavigator`.

**Tech Stack:** Python, NumPy, OpenCV (`cv2.circle`), CustomTkinter, existing `navigator.py` / `engine.py` / `main.py` pipeline.

---

## File Map

| File | Change |
|---|---|
| `navigator.py` | Add `FootprintCanvas` class (new); modify `CoastalSnakeNavigator.__init__`, `reset`, `_grab_minimap`, `_click_vec` |
| `engine.py` | Add `footprint_ttl` param to `HuntEngine.start()` → pass to `PacmanEngine` |
| `navigator.py` | Add `footprint_ttl` param to `PacmanEngine.__init__` → pass to `CoastalSnakeNavigator` |
| `main.py` | Add `nav_footprint` slider + label; update `_update_nav_labels`, `_save_settings`, `_load_settings`, `_start_hunt` |
| `gui_config.json` | Add `"nav_footprint_ttl": 120` |
| `test_footprint_canvas.py` | New — 8 TDD unit tests |

---

## Task 1: `FootprintCanvas` — TDD

**Files:**
- Create: `test_footprint_canvas.py`
- Modify: `navigator.py` — add class after `WATER_HSV` constants block (after line 86)

- [ ] **Step 1: Write all failing tests**

Create `test_footprint_canvas.py`:

```python
import time
import numpy as np
import pytest
import cv2


def test_record_moves_position():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.record(1.0, 0.0)
    assert fc._cx == FootprintCanvas.CENTER + 1
    assert fc._cy == FootprintCanvas.CENTER


def test_record_stamps_cell():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    before = time.time()
    fc.record(0.0, 0.0)
    after = time.time()
    ts = fc._grid[fc._cy, fc._cx]
    assert before <= ts <= after


def test_render_overlay_shape():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.record(0.0, 0.0)
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    assert overlay.shape == (180, 180, 3)


def test_render_overlay_blue_pixels():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.record(0.0, 0.0)
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    # Center of overlay should have a blue-dominant pixel
    cy, cx = 90, 90
    blue  = int(overlay[cy, cx, 0])
    green = int(overlay[cy, cx, 1])
    red   = int(overlay[cy, cx, 2])
    assert blue > 100, f"Expected blue pixel at center, got BGR=({blue},{green},{red})"
    assert blue > green * 1.2
    assert blue > red * 1.2


def test_render_overlay_expired():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    # Stamp with an old timestamp directly
    fc._grid[fc._cy, fc._cx] = time.time() - 999.0
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    assert overlay.sum() == 0, "Expired footprint should not render"


def test_reset_clears_grid():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.record(1.0, 0.0)
    fc.record(-1.0, 0.0)
    fc.reset()
    assert fc._grid.sum() == 0
    assert fc._cx == FootprintCanvas.CENTER
    assert fc._cy == FootprintCanvas.CENTER


def test_grid_clamp():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    for _ in range(300):
        fc.record(1.0, 0.0)
    assert fc._cx == FootprintCanvas.GRID_SIZE - 1  # no IndexError, clamped


def test_overlay_detected_as_water():
    """Footprint color must be picked up as water by get_land_water_masks."""
    from navigator import FootprintCanvas, get_land_water_masks
    fc = FootprintCanvas()
    fc.record(0.0, 0.0)
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    _, water_mask = get_land_water_masks(overlay)
    assert water_mask.sum() > 0, "Footprint pixels must be detected as water"
```

- [ ] **Step 2: Run tests — verify they all FAIL**

```
cd C:\BattleBot
pytest test_footprint_canvas.py -v
```
Expected: 8 failures — `ImportError: cannot import name 'FootprintCanvas'`

- [ ] **Step 3: Implement `FootprintCanvas` in `navigator.py`**

Insert the following block in `navigator.py` **after line 86** (after `WATER_HSV` definition), before the `_prepare_minimap` function:

```python
# ─────────────────────────────────────────────
# FootprintCanvas — visited-cell memory
# ─────────────────────────────────────────────

class FootprintCanvas:
    """
    Step-space grid that records visit timestamps.
    render_overlay() paints recent cells as blue pixels onto a minimap-sized image
    so get_land_water_masks() treats them exactly like water.
    """

    GRID_SIZE       = 401            # 200 steps in any direction from center
    CENTER          = 200            # starting cell index
    FOOTPRINT_COLOR = (180, 100, 30) # BGR — blue-dominant; detected as water

    def __init__(self):
        self._grid = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.float64)
        self._cx   = self.CENTER
        self._cy   = self.CENTER

    def record(self, dx: float, dy: float) -> None:
        """Advance position by (dx, dy) steps (rounded to int) and stamp cell."""
        self._cx = max(0, min(self.GRID_SIZE - 1, self._cx + int(round(dx))))
        self._cy = max(0, min(self.GRID_SIZE - 1, self._cy + int(round(dy))))
        self._grid[self._cy, self._cx] = time.time()

    def render_overlay(
        self,
        minimap_shape: tuple,
        ttl_sec: float,
        pixels_per_step: int = 20,
    ) -> np.ndarray:
        """
        Return a BGR image (same size as minimap_shape) with recent footprint
        cells painted as FOOTPRINT_COLOR circles.  Cells older than ttl_sec
        are transparent (black).
        """
        h, w   = minimap_shape[:2]
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        now    = time.time()
        half_x = w // (2 * pixels_per_step) + 1
        half_y = h // (2 * pixels_per_step) + 1
        radius = max(2, pixels_per_step // 2)

        for dy in range(-half_y, half_y + 1):
            for dx in range(-half_x, half_x + 1):
                gx = self._cx + dx
                gy = self._cy + dy
                if 0 <= gx < self.GRID_SIZE and 0 <= gy < self.GRID_SIZE:
                    ts = self._grid[gy, gx]
                    if ts > 0 and (now - ts) < ttl_sec:
                        px = w // 2 + dx * pixels_per_step
                        py = h // 2 + dy * pixels_per_step
                        cv2.circle(overlay, (px, py), radius,
                                   self.FOOTPRINT_COLOR, -1)
        return overlay

    def reset(self) -> None:
        self._grid[:] = 0
        self._cx = self.CENTER
        self._cy = self.CENTER
```

- [ ] **Step 4: Run tests — verify all 8 PASS**

```
pytest test_footprint_canvas.py -v
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```
git add navigator.py test_footprint_canvas.py
git commit -m "feat: add FootprintCanvas — step-space grid with TTL-based overlay"
```

---

## Task 2: Integrate `FootprintCanvas` into `CoastalSnakeNavigator`

**Files:**
- Modify: `navigator.py` — `CoastalSnakeNavigator.__init__`, `reset`, `_grab_minimap`, `_click_vec`

- [ ] **Step 1: Add params and canvas to `__init__`**

In `CoastalSnakeNavigator.__init__` (line 330), add three new parameters after `coast_ema_alpha`:

```python
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
        footprint_ttl: float    = 120.0,
        footprint_enabled: bool = True,
        pixels_per_step: int    = 20,
    ):
```

Then add at the end of `__init__`, after `self._angle_init = False`:

```python
        self._footprint_ttl     = footprint_ttl
        self._footprint_enabled = footprint_enabled
        self._pixels_per_step   = pixels_per_step
        self._footprint         = FootprintCanvas()
```

- [ ] **Step 2: Update `reset()` to also reset canvas**

Replace the existing `reset()` body (lines 365-370) with:

```python
    def reset(self):
        self._state        = 'HOMING'
        self._inland_steps = 0
        self._homing_steps = 0
        self._return_steps = 0
        self._angle_init   = False
        self._inland_vec   = (1.0, 0.0)
        self._coast_vec    = (0.0, 1.0)
        self._coast_angle  = 0.0
        self._footprint.reset()
```

- [ ] **Step 3: Update `_grab_minimap()` to apply overlay**

Replace the existing `_grab_minimap()` (lines 382-384) with:

```python
    def _grab_minimap(self) -> np.ndarray:
        from minimap_reader import get_minimap_snapshot
        mm = get_minimap_snapshot(self.center_x, self.center_y)
        if self._footprint_enabled:
            overlay = self._footprint.render_overlay(
                mm.shape, self._footprint_ttl, self._pixels_per_step)
            mask = overlay.any(axis=2)
            mm[mask] = overlay[mask]
        return mm
```

- [ ] **Step 4: Update `_click_vec()` to record each step**

Replace the existing `_click_vec()` (lines 386-395) with:

```python
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
        if self._footprint_enabled:
            self._footprint.record(ndx, ndy)
```

- [ ] **Step 5: Run existing test suite — verify no regressions**

```
pytest test_coastal_snake.py test_minimap_reader.py test_footprint_canvas.py -v
```
Expected: all existing tests pass + 8 footprint tests pass.

- [ ] **Step 6: Commit**

```
git add navigator.py
git commit -m "feat: integrate FootprintCanvas into CoastalSnakeNavigator"
```

---

## Task 3: Wire `footprint_ttl` through `PacmanEngine` and `engine.py`

**Files:**
- Modify: `navigator.py` — `PacmanEngine.__init__`
- Modify: `engine.py` — `HuntEngine.start()`

- [ ] **Step 1: Add `footprint_ttl` to `PacmanEngine.__init__`**

In `PacmanEngine.__init__` (line 537), add the new parameter after `min_water_px`:

```python
    def __init__(
        self,
        center_x: int        = 90,
        center_y: int        = 925,
        step: int            = 13,
        dive_depth: int      = 5,
        conf: float          = 0.7,
        scan_interval: float = 0.6,
        reset_minutes: float = 10.0,
        sound_path: str      = 'Logo_exchange.wav',
        yolo_model           = None,
        move_wait: float     = 2.0,
        navigation_enabled: bool = True,
        max_inland_steps: int    = 5,
        ocean_land_ratio: float  = 0.03,
        min_water_px: int        = 500,
        footprint_ttl: float     = 120.0,
        # legacy params (ignored):
        max_depth: int      = 4,
        screen_w: int       = 5,
        screen_h: int       = 39,
        magnet: float       = 0.0,
        inertia: float      = 1.0,
        random_w: float     = 0.05,
    ):
```

Then pass it through to `CoastalSnakeNavigator` — replace the joystick constructor call (lines 563-569) with:

```python
        self.joystick = CoastalSnakeNavigator(
            center_x=center_x,
            center_y=center_y,
            step=step,
            max_inland_steps=max_inland_steps,
            ocean_land_ratio=ocean_land_ratio,
            min_water_px=min_water_px,
            footprint_ttl=footprint_ttl,
        )
```

- [ ] **Step 2: Add `footprint_ttl` to `HuntEngine.start()` in `engine.py`**

Replace the `start()` signature (lines 24-37) with:

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
        max_inland_steps: int    = 5,
        ocean_land_ratio: float  = 0.03,
        min_water_px: int        = 500,
        footprint_ttl: float     = 120.0,
    ):
```

Then pass it in the `PacmanEngine(...)` constructor call (inside `start()`, line 38) — add after `min_water_px=min_water_px,`:

```python
            footprint_ttl=footprint_ttl,
```

- [ ] **Step 3: Run tests**

```
pytest test_coastal_snake.py test_footprint_canvas.py -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```
git add navigator.py engine.py
git commit -m "feat: wire footprint_ttl through PacmanEngine and HuntEngine"
```

---

## Task 4: GUI slider + config persistence

**Files:**
- Modify: `main.py`
- Modify: `gui_config.json`

- [ ] **Step 1: Add slider to nav_frame in `main.py`**

In `main.py`, find the section that ends with `nav_waterpx_slider.pack(...)` (around line 263) and the `save_btn` definition (around line 266). Insert the new footprint slider block **between** them — after `self.nav_waterpx_slider.pack(...)` and before `self.save_btn = ...`:

```python
        # Память следов (TTL секунды)
        self.nav_footprint_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_footprint_frame.pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkLabel(self.nav_footprint_frame, text="Память следов (сек):", font=ctk.CTkFont(size=11)).pack(side="left")
        self.nav_footprint_val = ctk.CTkLabel(self.nav_footprint_frame, text="120 с", font=ctk.CTkFont(weight="bold"), text_color="#3b8ed0")
        self.nav_footprint_val.pack(side="right")
        self.nav_footprint_slider = ctk.CTkSlider(
            self.nav_frame, from_=10, to=300, number_of_steps=29,
            command=self._update_nav_labels,
        )
        self.nav_footprint_slider.set(120)
        self.nav_footprint_slider.pack(padx=10, pady=(0, 2), fill="x")
```

- [ ] **Step 2: Add label update in `_update_nav_labels`**

Find `_update_nav_labels` (around line 685). After the line:
```python
        self.nav_waterpx_val.configure(text=f"{int(self.nav_waterpx_slider.get())}")
```
Add:
```python
        self.nav_footprint_val.configure(text=f"{int(self.nav_footprint_slider.get())} с")
```

- [ ] **Step 3: Add save in `_save_settings`**

Find the block in `_save_settings` that saves the coastal snake params (around lines 732-734):
```python
            cfg["max_inland_steps"] = int(self.nav_inland_slider.get())
            cfg["ocean_land_ratio"] = int(self.nav_ocean_slider.get()) / 100.0
            cfg["min_water_px"]     = int(self.nav_waterpx_slider.get())
```
Add one line after:
```python
            cfg["nav_footprint_ttl"] = int(self.nav_footprint_slider.get())
```

- [ ] **Step 4: Add load in `_load_settings`**

Find the block in `_load_settings` that loads the coastal snake params (around lines 763-765):
```python
            self.nav_inland_slider.set(cfg.get("max_inland_steps", 5))
            self.nav_ocean_slider.set(int(cfg.get("ocean_land_ratio", 0.03) * 100))
            self.nav_waterpx_slider.set(cfg.get("min_water_px", 500))
```
Add one line after:
```python
            self.nav_footprint_slider.set(cfg.get("nav_footprint_ttl", 120))
```

- [ ] **Step 5: Pass to engine in `_start_hunt`**

Find the `engine.start(...)` call in `_start_hunt` (around lines 792-798). After the line:
```python
                    min_water_px=int(self.nav_waterpx_slider.get()),
```
Add:
```python
                    footprint_ttl=float(self.nav_footprint_slider.get()),
```

- [ ] **Step 6: Add default to `gui_config.json`**

Edit `gui_config.json` — add `"nav_footprint_ttl": 120` as the last key before the closing `}`:

```json
{
  "center_x": "91",
  "center_y": "929",
  "step": 13,
  "conf": 0.26,
  "scan_interval": 1.0,
  "reset_minutes": 10,
  "move_wait": 0.8,
  "max_inland_steps": 5,
  "ocean_land_ratio": 0.12,
  "min_water_px": 500,
  "nav_footprint_ttl": 120
}
```

- [ ] **Step 7: Run full test suite**

```
pytest test_coastal_snake.py test_minimap_reader.py test_footprint_canvas.py -v
```
Expected: all pass.

- [ ] **Step 8: Commit**

```
git add main.py gui_config.json
git commit -m "feat: add Footprint TTL slider to nav GUI + config persistence"
```

---

## Task 5: Final integration commit

- [ ] **Step 1: Smoke test — launch GUI**

```
python main.py
```
Verify: navigation frame shows new slider "Память следов (сек)", range 10–300, default 120.

- [ ] **Step 2: Final commit**

```
git add -A
git commit -m "feat: footprint memory — overlay visited steps as water on minimap to prevent circling"
```
