# Button Finder — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded pixel coordinates in `crypt_hunter.py` with color-based button detection that works on any resolution, language, and client.

**Architecture:** Two new modules — `window_scaler.py` (finds game window, computes scale vs 1920×1080) and `button_finder.py` (finds buttons by HSV color within a scaled search region). `crypt_hunter.py` gets a `_find_button()` helper that tries color detection first and falls back to scaled hardcoded coords.

**Tech Stack:** Python, OpenCV (HSV masking + contours), mss (screenshots), pyautogui (window detection)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `window_scaler.py` | **Create** | Game window detection + coordinate scaling |
| `button_finder.py` | **Create** | HSV color detection in screen regions |
| `test_window_scaler.py` | **Create** | Unit tests for scaling math |
| `test_button_finder.py` | **Create** | Unit tests for mask + contour logic |
| `crypt_hunter.py` | **Modify** | Use `_find_button()` for 5 critical clicks |

---

## Task 1: `window_scaler.py`

**Files:**
- Create: `C:\BattleBot\window_scaler.py`
- Create: `C:\BattleBot\test_window_scaler.py`

### Step 1.1 — Write failing tests

- [ ] Create `test_window_scaler.py`:

```python
"""Tests for window_scaler.py — pure math, no real screen."""
import pytest


class TestGetScale:
    def test_returns_1_1_when_no_window(self):
        from unittest.mock import patch
        import window_scaler as ws
        with patch.object(ws, 'get_game_rect', return_value=None):
            assert ws.get_scale() == (1.0, 1.0)

    def test_computes_scale_from_rect(self):
        from unittest.mock import patch
        import window_scaler as ws
        with patch.object(ws, 'get_game_rect', return_value=(0, 0, 960, 540)):
            sx, sy = ws.get_scale()
            assert abs(sx - 0.5) < 0.001
            assert abs(sy - 0.5) < 0.001


class TestScaleCoord:
    def test_no_window_returns_original(self):
        from unittest.mock import patch
        import window_scaler as ws
        with patch.object(ws, 'get_game_rect', return_value=None):
            assert ws.scale_coord(100, 200) == (100, 200)

    def test_scales_and_offsets(self):
        from unittest.mock import patch
        import window_scaler as ws
        # Window at (100, 50), size 960×540 → scale 0.5
        with patch.object(ws, 'get_game_rect', return_value=(100, 50, 960, 540)):
            x, y = ws.scale_coord(200, 400)
            assert x == 100 + int(200 * 0.5)  # 200
            assert y == 50  + int(400 * 0.5)  # 250


class TestScaleRegion:
    def test_no_window_returns_original(self):
        from unittest.mock import patch
        import window_scaler as ws
        with patch.object(ws, 'get_game_rect', return_value=None):
            assert ws.scale_region(10, 20, 100, 50) == (10, 20, 100, 50)

    def test_scales_region(self):
        from unittest.mock import patch
        import window_scaler as ws
        with patch.object(ws, 'get_game_rect', return_value=(0, 0, 960, 540)):
            x, y, w, h = ws.scale_region(100, 200, 400, 100)
            assert x == 50
            assert y == 100
            assert w == 200
            assert h == 50
```

- [ ] **Run to confirm FAIL:**
```
python -m pytest test_window_scaler.py -v
```
Expected: `ModuleNotFoundError: No module named 'window_scaler'`

### Step 1.2 — Implement `window_scaler.py`

- [ ] Create `C:\BattleBot\window_scaler.py`:

```python
"""
window_scaler.py — Game window detection + coordinate scaling.
Reference resolution: 1920×1080.
Falls back to (1.0, 1.0) scale if game window not found.
"""
import pyautogui

REFERENCE_W = 1920
REFERENCE_H = 1080

# Substrings to search for in window title (case-insensitive)
GAME_TITLE_SUBSTRINGS = ["total battle", "totalbattle"]


def get_game_rect() -> tuple[int, int, int, int] | None:
    """
    Find the game window. Returns (left, top, width, height) or None.
    Searches visible windows for title containing a known game string.
    """
    try:
        all_windows = pyautogui.getAllWindows()
        for w in all_windows:
            title_lower = w.title.lower()
            if any(s in title_lower for s in GAME_TITLE_SUBSTRINGS):
                if w.width > 100 and w.height > 100:
                    return (w.left, w.top, w.width, w.height)
    except Exception:
        pass
    return None


def get_scale() -> tuple[float, float]:
    """
    Returns (scale_x, scale_y) = game_window_size / reference_size.
    Returns (1.0, 1.0) if window not found.
    """
    rect = get_game_rect()
    if rect is None:
        return (1.0, 1.0)
    _, _, w, h = rect
    return (w / REFERENCE_W, h / REFERENCE_H)


def scale_coord(x: int, y: int) -> tuple[int, int]:
    """
    Scale reference (1920×1080) coordinates to actual screen position.
    Includes window offset.
    """
    rect = get_game_rect()
    if rect is None:
        return (int(x), int(y))
    left, top, w, h = rect
    return (
        left + int(x * w / REFERENCE_W),
        top  + int(y * h / REFERENCE_H),
    )


def scale_region(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
    """
    Scale reference region (x, y, w, h) to actual screen coordinates.
    """
    rect = get_game_rect()
    if rect is None:
        return (int(x), int(y), int(w), int(h))
    gl, gt, gw, gh = rect
    return (
        gl + int(x * gw / REFERENCE_W),
        gt + int(y * gh / REFERENCE_H),
        int(w * gw / REFERENCE_W),
        int(h * gh / REFERENCE_H),
    )
```

- [ ] **Run tests — confirm PASS:**
```
python -m pytest test_window_scaler.py -v
```
Expected: `4 passed`

- [ ] **Commit:**
```
git add window_scaler.py test_window_scaler.py
git commit -m "feat: add window_scaler — game window detection and coordinate scaling"
```

---

## Task 2: `button_finder.py`

**Files:**
- Create: `C:\BattleBot\button_finder.py`
- Create: `C:\BattleBot\test_button_finder.py`

### Step 2.1 — Write failing tests

- [ ] Create `test_button_finder.py`:

```python
"""Tests for button_finder.py — pure functions, no real screen."""
import numpy as np
import cv2
import pytest


class TestApplyColorMask:
    def test_green_mask_detects_green_pixel(self):
        from button_finder import _apply_color_mask
        # Pure green BGR pixel
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[:] = (0, 180, 0)   # BGR green
        mask = _apply_color_mask(img, 'green')
        assert mask.sum() > 0

    def test_green_mask_ignores_purple(self):
        from button_finder import _apply_color_mask
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[:] = (180, 0, 180)   # BGR purple
        mask = _apply_color_mask(img, 'green')
        assert mask.sum() == 0

    def test_purple_mask_detects_purple(self):
        from button_finder import _apply_color_mask
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[:] = (180, 0, 180)   # BGR purple
        mask = _apply_color_mask(img, 'purple')
        assert mask.sum() > 0

    def test_unknown_color_returns_empty(self):
        from button_finder import _apply_color_mask
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        mask = _apply_color_mask(img, 'unknown_color')
        assert mask.sum() == 0


class TestPickContour:
    def _make_contour(self, x, y, w, h):
        """Create a simple rectangular contour."""
        pts = np.array([[[x, y]], [[x+w, y]], [[x+w, y+h]], [[x, y+h]]], dtype=np.int32)
        return pts

    def test_returns_none_when_no_contours(self):
        from button_finder import _pick_contour
        assert _pick_contour([], 'largest', 0, 0) is None

    def test_picks_rightmost(self):
        from button_finder import _pick_contour
        left  = self._make_contour(10, 50, 80, 30)   # cx=50
        right = self._make_contour(200, 50, 80, 30)  # cx=240
        result = _pick_contour([left, right], 'rightmost', 0, 0)
        assert result is not None
        cx, cy = result
        assert cx == 240

    def test_picks_leftmost(self):
        from button_finder import _pick_contour
        left  = self._make_contour(10, 50, 80, 30)   # cx=50
        right = self._make_contour(200, 50, 80, 30)  # cx=240
        result = _pick_contour([left, right], 'leftmost', 0, 0)
        assert result is not None
        cx, cy = result
        assert cx == 50

    def test_picks_topmost(self):
        from button_finder import _pick_contour
        top    = self._make_contour(50, 10, 80, 30)   # cy=25
        bottom = self._make_contour(50, 200, 80, 30)  # cy=215
        result = _pick_contour([top, bottom], 'topmost', 0, 0)
        assert result is not None
        cx, cy = result
        assert cy == 25

    def test_skips_contours_below_min_area(self):
        from button_finder import _pick_contour
        tiny = self._make_contour(10, 10, 5, 5)   # area ~25, below min_area=800
        result = _pick_contour([tiny], 'largest', 0, 0)
        assert result is None

    def test_skips_taller_than_wide(self):
        from button_finder import _pick_contour
        # Tall thin contour — not a button
        tall = self._make_contour(10, 10, 20, 200)   # w < h
        result = _pick_contour([tall], 'largest', 0, 0)
        assert result is None

    def test_applies_region_offset(self):
        from button_finder import _pick_contour
        cnt = self._make_contour(10, 10, 100, 40)   # local cx=60, cy=30
        result = _pick_contour([cnt], 'largest', region_x=500, region_y=300)
        assert result == (560, 330)


class TestFindColoredButton:
    def test_returns_none_on_exception(self):
        from button_finder import find_colored_button
        # Invalid region (zero size) should not raise
        result = find_colored_button((0, 0, 0, 0), 'green')
        assert result is None
```

- [ ] **Run to confirm FAIL:**
```
python -m pytest test_button_finder.py -v
```
Expected: `ModuleNotFoundError: No module named 'button_finder'`

### Step 2.2 — Implement `button_finder.py`

- [ ] Create `C:\BattleBot\button_finder.py`:

```python
"""
button_finder.py — Finds UI buttons by color (HSV) in a screen region.
Language-independent: matches button color/shape, not text.

Usage:
    from button_finder import find_colored_button
    pos = find_colored_button((900, 85, 500, 60), color='purple', pick='largest')
    # pos = (cx, cy) absolute screen coords, or None
"""
import numpy as np
import cv2

try:
    import mss as _mss
    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False

# ── HSV colour ranges ──────────────────────────────────────────────────────
# Calibrated from targets_2/ screenshots (Total Battle game buttons).
# Hue: 0-179 in OpenCV. Green ≈ 40-85. Purple/violet ≈ 125-160.
HSV_RANGES: dict[str, tuple[tuple, tuple]] = {
    'green':  ((35, 40, 40),  (85, 255, 200)),
    'purple': ((125, 50, 50), (160, 255, 255)),
}

MIN_AREA = 800   # px² — ignore specks smaller than this


def _apply_color_mask(img_bgr: np.ndarray, color: str) -> np.ndarray:
    """
    Apply HSV color mask to BGR image.
    Returns binary mask (uint8). Returns all-zeros for unknown color.
    """
    if color not in HSV_RANGES:
        return np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    lo, hi = HSV_RANGES[color]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8))


def _pick_contour(
    contours: list,
    pick: str,
    region_x: int,
    region_y: int,
) -> tuple[int, int] | None:
    """
    Filter contours by size/shape, pick by rule, return absolute (cx, cy).
    pick: 'rightmost' | 'leftmost' | 'topmost' | 'largest'
    """
    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if w <= h:               # buttons must be wider than tall
            continue
        cx = region_x + x + w // 2
        cy = region_y + y + h // 2
        candidates.append((cx, cy, area))

    if not candidates:
        return None

    if pick == 'rightmost':
        return max(candidates, key=lambda c: c[0])[:2]
    if pick == 'leftmost':
        return min(candidates, key=lambda c: c[0])[:2]
    if pick == 'topmost':
        return min(candidates, key=lambda c: c[1])[:2]
    # default: largest
    return max(candidates, key=lambda c: c[2])[:2]


def _screenshot_region(region: tuple[int, int, int, int]) -> np.ndarray:
    """Grab screen region (x, y, w, h). Returns BGR numpy array."""
    x, y, w, h = region
    with _mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        raw = sct.grab(monitor)
    img = np.array(raw)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def find_colored_button(
    region: tuple[int, int, int, int],
    color: str = 'green',
    pick: str = 'largest',
) -> tuple[int, int] | None:
    """
    Find a button in a screen region by color.

    Args:
        region: (x, y, w, h) absolute screen coordinates
        color:  'green' or 'purple'
        pick:   'rightmost' | 'leftmost' | 'topmost' | 'largest'

    Returns:
        (cx, cy) absolute screen coordinates of button centre, or None.
    """
    try:
        img = _screenshot_region(region)
        mask = _apply_color_mask(img, color)
        # Close small gaps in the button area
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return _pick_contour(contours, pick, region[0], region[1])
    except Exception:
        return None


# ── Demo CLI ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    """
    python button_finder.py --demo
    Takes a screenshot and draws found buttons for visual calibration.
    Saves result to button_finder_demo.png
    """
    import sys
    import pyautogui

    print("Taking screenshot in 2 seconds — switch to game window...")
    import time; time.sleep(2)

    with _mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
    full = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR)
    h, w = full.shape[:2]

    # Search regions in reference coords — scale to actual screen size
    searches = [
        # (label,  ref_region,              color,    pick)
        ("Study",  (850, 720, 450, 120),    'green',  'rightmost'),
        ("Open",   (750, 720, 350, 120),    'green',  'leftmost'),
        ("Accel",  (900, 85,  500,  60),    'purple', 'largest'),
        ("Use",    (900, 380, 450, 250),    'green',  'topmost'),
    ]

    from window_scaler import scale_region
    colours_bgr = {'green': (0, 200, 0), 'purple': (200, 0, 200)}

    for label, ref_region, color, pick in searches:
        region = scale_region(*ref_region)
        pos = find_colored_button(region, color, pick)
        rx, ry, rw, rh = region
        cv2.rectangle(full, (rx, ry), (rx + rw, ry + rh), (200, 200, 0), 1)
        if pos:
            cx, cy = pos
            c = colours_bgr[color]
            cv2.circle(full, (cx, cy), 12, c, -1)
            cv2.putText(full, label, (cx - 20, cy - 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)
            print(f"  {label}: found at ({cx}, {cy})")
        else:
            print(f"  {label}: NOT FOUND")

    out = "button_finder_demo.png"
    cv2.imwrite(out, full)
    print(f"\nSaved: {out}")
```

- [ ] **Run tests — confirm PASS:**
```
python -m pytest test_button_finder.py -v
```
Expected: `10 passed`

- [ ] **Commit:**
```
git add button_finder.py test_button_finder.py
git commit -m "feat: add button_finder — HSV color-based button detection"
```

---

## Task 3: Update `crypt_hunter.py`

**Files:**
- Modify: `C:\BattleBot\crypt_hunter.py`

### Step 3.1 — Add imports and `_find_button` helper

- [ ] Add at the top of `crypt_hunter.py`, after the existing imports:

```python
# Visual button detection (language-independent)
try:
    from button_finder import find_colored_button
    from window_scaler import scale_region, scale_coord
    _VISUAL_NAV_AVAILABLE = True
except ImportError:
    _VISUAL_NAV_AVAILABLE = False
```

- [ ] Add `_find_button` as a method of `CryptHunter` (insert after `_close_dialog`):

```python
def _find_button(
    self,
    ref_region: tuple,
    color: str,
    pick: str,
    fallback: tuple,
) -> tuple[int, int]:
    """
    Try to find button by color in ref_region (1920×1080 coords).
    Falls back to scale_coord(*fallback) if not found or visual nav unavailable.

    ref_region: (x, y, w, h) in 1920×1080 reference coordinates
    color:      'green' or 'purple'
    pick:       'rightmost' | 'leftmost' | 'topmost' | 'largest'
    fallback:   (x, y) hardcoded reference coordinates
    """
    if _VISUAL_NAV_AVAILABLE:
        region = scale_region(*ref_region)
        pos = find_colored_button(region, color, pick)
        if pos:
            self._status(f"  [visual] {color}/{pick} → {pos}")
            return pos
        self._status(f"  [visual] not found — using fallback coords")
    if _VISUAL_NAV_AVAILABLE:
        return scale_coord(*fallback)
    return fallback
```

### Step 3.2 — Replace 5 hardcoded clicks

- [ ] In `_send_captain`, replace the two `_click` calls:

```python
def _send_captain(self, crypt_type: str) -> bool:
    self._random_pause()
    if crypt_type in RARE_CRYPT_TYPES:
        self._status("Редкий склеп — нажимаю «Открыть»")
        pos = self._find_button(
            ref_region=(750, 720, 350, 120),
            color='green', pick='leftmost',
            fallback=CRYPT_OPEN_BTN,
        )
        self._click(*pos)
        self._random_pause(0.8, 1.2)

    self._status("Нажимаю «Исследовать»...")
    pos = self._find_button(
        ref_region=(850, 720, 450, 120),
        color='green', pick='rightmost',
        fallback=CRYPT_STUDY_BTN,
    )
    self._click(*pos)
    self._random_pause(1.2, 1.8)
    return True
```

- [ ] In `_click_captain_event`, replace click:

```python
def _click_captain_event(self):
    self._status("Кликаю по полосе Картера...")
    pos = self._find_button(
        ref_region=(900, 85, 500, 60),
        color='purple', pick='largest',
        fallback=CARTER_EVENT_BAR,
    )
    self._click(*pos)
    self._random_pause(0.8, 1.2)
```

- [ ] In `_accelerate`, replace click inside the loop (both loops — blind and normal):

```python
def _accelerate(self, n: int) -> float:
    remaining = self._read_remaining_time()

    if remaining == 0:
        self._status(f"OCR времени не сработал — применяю {n} ускорений вслепую")
        for _ in range(n):
            pos = self._find_button(
                ref_region=(900, 380, 450, 250),
                color='green', pick='topmost',
                fallback=ACCEL_USE_BTN,
            )
            self._click(*pos)
            self._random_pause(0.4, 0.7)
        remaining = self._read_remaining_time()
        wait_time = (remaining * 2.0 + 2.0) if remaining > 0 else (60.0 * n + 2.0)
        return wait_time

    applied, remaining = calc_accelerations(remaining, max_n=n)
    self._status(f"Ускоряю {applied} раз (из {n})...")
    for _ in range(applied):
        pos = self._find_button(
            ref_region=(900, 380, 450, 250),
            color='green', pick='topmost',
            fallback=ACCEL_USE_BTN,
        )
        self._click(*pos)
        self._random_pause(0.4, 0.7)
    wait_time = remaining * 2.0 + 2.0
    return wait_time
```

- [ ] In `_scroll_and_find`, replace the «Перейти» click (only X is taken from visual, Y stays from YOLO):

```python
# Replace this line:
#   self._click(WT_GOTO_BTN_X, cy + 17, jitter=0)
# With:

if _VISUAL_NAV_AVAILABLE:
    goto_x = scale_coord(WT_GOTO_BTN_X, 0)[0]
else:
    goto_x = WT_GOTO_BTN_X
self._click(goto_x, cy + 17, jitter=0)
```

### Step 3.3 — Run existing tests to confirm no regression

- [ ] Run the full test suite:
```
python -m pytest test_crypt_hunter.py -v
```
Expected: `34 passed`

- [ ] **Commit:**
```
git add crypt_hunter.py
git commit -m "feat: crypt_hunter uses visual button detection with hardcoded fallback"
```

---

## Task 4: Visual Calibration Demo

**Goal:** Verify HSV thresholds work on real game screen before any live hunt.

- [ ] Switch to the game window, navigate to a crypt dialog (or Carter march bar)

- [ ] Run the demo:
```
python button_finder.py --demo
```
Expected output (example):
```
Taking screenshot in 2 seconds — switch to game window...
  Study: found at (1137, 777)
  Open:  NOT FOUND           ← OK if crypt dialog not open
  Accel: found at (1126, 113) ← OK if Carter march active
  Use:   NOT FOUND           ← OK if speed-up dialog not open
Saved: button_finder_demo.png
```

- [ ] Open `button_finder_demo.png` and verify:
  - Yellow rectangles = search regions (should cover the right area of screen)
  - Green/purple filled circles = detected button centres (should be ON the button)

- [ ] **If a button is not detected** — adjust HSV range in `button_finder.py`:
  - Use `debug_vision.py` or a paint app to eyedropper the button's colour
  - Convert RGB → HSV: `H = hue/2` (OpenCV uses 0-179), S and V stay 0-255
  - Widen the range ±10 on H, ±20 on S

- [ ] **Commit after any HSV adjustments:**
```
git add button_finder.py
git commit -m "fix: calibrate HSV ranges for green/purple game buttons"
```

---

## HSV Calibration Reference

From `targets_2/` screenshots (approximate ranges to start with):

| Button | BGR sample | HSV approx | Range to use |
|--------|-----------|------------|--------------|
| Green buttons | (0, 120, 20) | H≈60, S≈255, V≈120 | H 35-85, S 40-255, V 40-200 |
| Purple «Ускорить» | (150, 30, 180) | H≈145, S≈220, V≈180 | H 125-160, S 50-255, V 50-255 |

These are starting values — adjust after the demo run (Task 4).
