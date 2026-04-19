# 2-Point Coordinate Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `window_scaler.py` with a `CoordinateManager` that uses two user-defined anchor points to compute separate X/Y scale factors, enabling accurate click positioning on any resolution/browser.

**Architecture:** `coord_manager.py` holds the math singleton and profile save/load. `calibration_ui.py` provides a Tkinter magnifier (zoom + red dot + coordinate inputs) for precise anchor point selection. `main.py` gets a new «Калибровка» tab. All coordinate usage in `crypt_hunter.py` migrates from `window_scaler` to `coord_manager`.

**Tech Stack:** Python, Tkinter, MSS (screenshots), CustomTkinter (main GUI), JSON profiles

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `coord_manager.py` | CREATE | CoordinateManager class + global singleton |
| `calibration_ui.py` | CREATE | Tkinter magnifier GUI for anchor point selection |
| `profiles/profile_client.json` | CREATE | Default profile for game client |
| `profiles/profile_chrome.json` | CREATE | Default profile for Chrome browser |
| `profiles/profile_firefox.json` | CREATE | Default profile for Firefox browser |
| `test_coord_manager.py` | CREATE | Unit tests for CoordinateManager math |
| `main.py` | MODIFY | Add «Калибровка» tab |
| `crypt_hunter.py` | MODIFY | Replace window_scaler imports with coord_manager |
| `test_window_scaler.py` | DELETE | Replaced by test_coord_manager.py |
| `window_scaler.py` | DELETE | Replaced by coord_manager.py |

---

## Task 1: CoordinateManager — core math

**Files:**
- Create: `coord_manager.py`
- Create: `test_coord_manager.py`

### Reference constants

```
REF_A = (90, 925)   # minimap center (bottom-left anchor)
REF_B = (648, 47)   # silver crosshair (top-right anchor)
dx_ref = 648 - 90  = 558
dy_ref = 47 - 925  = -878
```

- [ ] **Step 1: Write failing tests**

Create `test_coord_manager.py`:

```python
"""Unit tests for CoordinateManager — pure math, no screen."""
import pytest
from coord_manager import CoordinateManager, REF_A, REF_B


class TestCalibrate:
    def test_identity_at_reference_resolution(self):
        """Calibrating with ref coords → scale 1.0, anchor = REF_A."""
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        assert abs(cm.scale_x - 1.0) < 0.001
        assert abs(cm.scale_y - 1.0) < 0.001
        assert cm.anchor_x == REF_A[0]
        assert cm.anchor_y == REF_A[1]

    def test_half_resolution(self):
        """Game window at 960×540 → scale ≈ 0.5 on both axes."""
        cm = CoordinateManager()
        a_user = (REF_A[0] // 2, REF_A[1] // 2)
        b_user = (REF_B[0] // 2, REF_B[1] // 2)
        cm.calibrate(a_user, b_user)
        assert abs(cm.scale_x - 0.5) < 0.01
        assert abs(cm.scale_y - 0.5) < 0.01

    def test_asymmetric_scale(self):
        """Browser toolbars cause different X and Y scales."""
        cm = CoordinateManager()
        # Simulate: game area is 80% width, 70% height
        a_user = (int(REF_A[0] * 0.8), int(REF_A[1] * 0.7))
        b_user = (int(REF_B[0] * 0.8), int(REF_B[1] * 0.7))
        cm.calibrate(a_user, b_user)
        assert abs(cm.scale_x - 0.8) < 0.01
        assert abs(cm.scale_y - 0.7) < 0.01


class TestToScreen:
    def test_ref_a_maps_to_anchor(self):
        """REF_A itself must map to the user anchor."""
        cm = CoordinateManager()
        a_user = (150, 800)
        b_user = (int(REF_B[0] * (a_user[0] / REF_A[0])), int(REF_B[1] * 0.9))
        cm.calibrate(a_user, b_user)
        x, y = cm.to_screen(REF_A[0], REF_A[1])
        assert x == a_user[0]
        assert y == a_user[1]

    def test_identity_calibration_is_passthrough(self):
        """At reference resolution to_screen returns original coords."""
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        assert cm.to_screen(689, 941) == (689, 941)
        assert cm.to_screen(1137, 777) == (1137, 777)

    def test_half_scale(self):
        cm = CoordinateManager()
        a_user = (REF_A[0] // 2, REF_A[1] // 2)
        b_user = (REF_B[0] // 2, REF_B[1] // 2)
        cm.calibrate(a_user, b_user)
        # WT_ICON = (689, 941) → should land at approx half
        x, y = cm.to_screen(689, 941)
        assert abs(x - 689 // 2) <= 1
        assert abs(y - 941 // 2) <= 1


class TestToRegion:
    def test_identity_calibration(self):
        cm = CoordinateManager()
        cm.calibrate(REF_A, REF_B)
        assert cm.to_region(100, 200, 300, 50) == (100, 200, 300, 50)

    def test_scales_width_and_height(self):
        cm = CoordinateManager()
        a_user = (REF_A[0] // 2, REF_A[1] // 2)
        b_user = (REF_B[0] // 2, REF_B[1] // 2)
        cm.calibrate(a_user, b_user)
        x, y, w, h = cm.to_region(200, 400, 100, 50)
        assert w == 50
        assert h == 25


class TestSaveLoad:
    def test_round_trip(self, tmp_path):
        cm = CoordinateManager()
        cm.calibrate((100, 800), (600, 50))
        path = str(tmp_path / "profile_test.json")
        cm.save(path)

        cm2 = CoordinateManager()
        cm2.load(path)
        assert cm2.anchor_x == 100
        assert cm2.anchor_y == 800
        assert abs(cm2.scale_x - cm.scale_x) < 0.001
        assert abs(cm2.scale_y - cm.scale_y) < 0.001

    def test_load_missing_file_raises(self):
        cm = CoordinateManager()
        with pytest.raises(FileNotFoundError):
            cm.load("/nonexistent/path.json")
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd C:\BattleBot && python -m pytest test_coord_manager.py -v
```
Expected: `ModuleNotFoundError: No module named 'coord_manager'`

- [ ] **Step 3: Implement coord_manager.py**

Create `coord_manager.py`:

```python
"""
coord_manager.py — 2-point coordinate calibration system.
Replaces window_scaler.py.

Reference resolution: 1920×1080.
Anchor A: minimap center (bottom-left).
Anchor B: silver resource crosshair (top-right).
"""
import json

# Reference anchor points at 1920×1080
REF_A: tuple[int, int] = (90, 925)
REF_B: tuple[int, int] = (648, 47)

_DX_REF = REF_B[0] - REF_A[0]  # 558
_DY_REF = REF_B[1] - REF_A[1]  # -878


class CoordinateManager:
    """Transforms reference (1920×1080) coordinates to actual screen coordinates."""

    def __init__(self):
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.anchor_x: int = REF_A[0]
        self.anchor_y: int = REF_A[1]
        self._point_a: tuple[int, int] = REF_A
        self._point_b: tuple[int, int] = REF_B

    def calibrate(self, a_user: tuple[int, int], b_user: tuple[int, int]) -> None:
        """
        Compute scale factors from two user-measured anchor points.
        a_user: pixel position of minimap center on user's screen.
        b_user: pixel position of silver crosshair on user's screen.
        """
        self._point_a = a_user
        self._point_b = b_user
        self.anchor_x, self.anchor_y = a_user
        self.scale_x = (b_user[0] - a_user[0]) / _DX_REF
        self.scale_y = (b_user[1] - a_user[1]) / _DY_REF

    def to_screen(self, x: int, y: int) -> tuple[int, int]:
        """Convert reference coordinate to actual screen pixel."""
        return (
            int(self.anchor_x + (x - REF_A[0]) * self.scale_x),
            int(self.anchor_y + (y - REF_A[1]) * self.scale_y),
        )

    def to_region(self, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        """Convert reference region (x, y, w, h) to actual screen region."""
        sx, sy = self.to_screen(x, y)
        return (sx, sy, int(w * self.scale_x), int(h * abs(self.scale_y)))

    def save(self, path: str) -> None:
        """Save calibration to JSON profile."""
        data = {
            "point_a": list(self._point_a),
            "point_b": list(self._point_b),
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """Load calibration from JSON profile and re-calibrate."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.calibrate(tuple(data["point_a"]), tuple(data["point_b"]))


# Global singleton — import this everywhere instead of window_scaler
coord_manager = CoordinateManager()
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd C:\BattleBot && python -m pytest test_coord_manager.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
cd C:\BattleBot && git add coord_manager.py test_coord_manager.py
git commit -m "feat: add CoordinateManager with 2-point calibration"
```

---

## Task 2: Default profile files

**Files:**
- Create: `profiles/profile_client.json`
- Create: `profiles/profile_chrome.json`
- Create: `profiles/profile_firefox.json`

- [ ] **Step 1: Create profiles directory and files**

```bash
mkdir -p C:\BattleBot\profiles
```

Create `profiles/profile_client.json`:
```json
{
  "name": "Client",
  "point_a": [90, 925],
  "point_b": [648, 47],
  "scale_x": 1.0,
  "scale_y": 1.0
}
```

Create `profiles/profile_chrome.json`:
```json
{
  "name": "Chrome",
  "point_a": [90, 925],
  "point_b": [648, 47],
  "scale_x": 1.0,
  "scale_y": 1.0
}
```

Create `profiles/profile_firefox.json`:
```json
{
  "name": "Firefox",
  "point_a": [90, 925],
  "point_b": [648, 47],
  "scale_x": 1.0,
  "scale_y": 1.0
}
```

Note: default values = reference (1920×1080). Each user calibrates to their actual positions.

- [ ] **Step 2: Verify load works**

```
cd C:\BattleBot && python -c "
from coord_manager import coord_manager
coord_manager.load('profiles/profile_client.json')
print('scale_x:', coord_manager.scale_x)
print('scale_y:', coord_manager.scale_y)
"
```
Expected output:
```
scale_x: 1.0
scale_y: 1.0
```

- [ ] **Step 3: Commit**

```bash
cd C:\BattleBot && git add profiles/
git commit -m "feat: add default calibration profiles (client, chrome, firefox)"
```

---

## Task 3: Calibration UI — magnifier with red dot

**Files:**
- Create: `calibration_ui.py`

The UI runs sequentially: Point A first, then Point B.
For each point:
1. Takes MSS screenshot of full screen
2. Opens Tkinter window with 600% zoom canvas centered at estimated point position
3. Shows live red dot (16×16 Toplevel) at current X/Y
4. User clicks in zoom canvas OR edits X/Y spinbox fields
5. Clicks «Зафиксировать» → saves point and proceeds

**Zoom math:**
- Canvas size: 420×320 px
- Zoom factor: 6 (600%)
- Region shown: 70×53 pixels of screenshot centered at (cur_x, cur_y)
- Click at canvas (cx, cy) → screen coord:
  `new_x = cur_x + (cx - 210) / 6`
  `new_y = cur_y + (cy - 160) / 6`

- [ ] **Step 1: Implement calibration_ui.py**

Create `calibration_ui.py`:

```python
"""
calibration_ui.py — Sequential 2-point calibration with magnifier.

Usage:
    from calibration_ui import run_calibration
    point_a, point_b = run_calibration()  # blocks until user fixes both points
    # Returns None, None if user cancels
"""
import tkinter as tk
from tkinter import ttk
import numpy as np

try:
    import mss
    from PIL import Image, ImageTk, ImageDraw
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

# Default starting positions for the crosshair before user adjusts
from coord_manager import REF_A, REF_B

ZOOM_FACTOR = 6
CANVAS_W = 420
CANVAS_H = 320
REGION_W = CANVAS_W // ZOOM_FACTOR  # 70 px of screen
REGION_H = CANVAS_H // ZOOM_FACTOR  # 53 px of screen


def _grab_full_screen() -> np.ndarray:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        return np.array(sct.grab(monitor))


def _show_red_dot(root: tk.Tk, x: int, y: int) -> tk.Toplevel:
    """Create/return 16×16 red dot Toplevel at (x, y). Caller must destroy old one first."""
    dot = tk.Toplevel(root)
    dot.overrideredirect(True)
    dot.attributes("-topmost", True)
    dot.geometry(f"16x16+{x - 8}+{y - 8}")
    canvas = tk.Canvas(dot, width=16, height=16, bg="red", highlightthickness=0)
    canvas.pack()
    canvas.create_line(0, 8, 16, 8, fill="white", width=1)
    canvas.create_line(8, 0, 8, 16, fill="white", width=1)
    return dot


def _build_zoom_image(screenshot: np.ndarray, cx: int, cy: int) -> Image.Image:
    """Extract region around (cx, cy) and zoom 6×."""
    h, w = screenshot.shape[:2]
    x1 = max(0, cx - REGION_W // 2)
    y1 = max(0, cy - REGION_H // 2)
    x2 = min(w, x1 + REGION_W)
    y2 = min(h, y1 + REGION_H)
    crop = screenshot[y1:y2, x1:x2, :3]  # drop alpha
    img = Image.fromarray(crop[..., ::-1])  # BGR→RGB
    img = img.resize((CANVAS_W, CANVAS_H), Image.NEAREST)
    # Draw crosshair on zoom image
    draw = ImageDraw.Draw(img)
    draw.line([(CANVAS_W // 2, 0), (CANVAS_W // 2, CANVAS_H)], fill="red", width=1)
    draw.line([(0, CANVAS_H // 2), (CANVAS_W, CANVAS_H // 2)], fill="red", width=1)
    return img


def _calibrate_one_point(
    root: tk.Tk,
    screenshot: np.ndarray,
    start_pos: tuple[int, int],
    label_text: str,
) -> tuple[int, int] | None:
    """
    Show magnifier for one anchor point. Blocks until user clicks «Зафиксировать».
    Returns (x, y) or None if cancelled.
    """
    result = [None]
    cur_x = tk.IntVar(value=start_pos[0])
    cur_y = tk.IntVar(value=start_pos[1])
    red_dot = [None]

    win = tk.Toplevel(root)
    win.title(f"Калибровка — {label_text}")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    tk.Label(win, text=label_text, font=("Arial", 12, "bold")).pack(pady=(8, 4))

    canvas = tk.Canvas(win, width=CANVAS_W, height=CANVAS_H, cursor="crosshair")
    canvas.pack(padx=10)

    zoom_img_ref = [None]

    def refresh_zoom():
        img = _build_zoom_image(screenshot, cur_x.get(), cur_y.get())
        photo = ImageTk.PhotoImage(img)
        zoom_img_ref[0] = photo
        canvas.create_image(0, 0, anchor="nw", image=photo)

        # Update red dot
        if red_dot[0]:
            red_dot[0].destroy()
        red_dot[0] = _show_red_dot(root, cur_x.get(), cur_y.get())

    def on_canvas_click(event):
        dx = (event.x - CANVAS_W // 2) / ZOOM_FACTOR
        dy = (event.y - CANVAS_H // 2) / ZOOM_FACTOR
        cur_x.set(int(cur_x.get() + dx))
        cur_y.set(int(cur_y.get() + dy))
        refresh_zoom()

    canvas.bind("<Button-1>", on_canvas_click)

    # X/Y spinboxes
    coord_frame = tk.Frame(win)
    coord_frame.pack(pady=6)
    tk.Label(coord_frame, text="X:").grid(row=0, column=0, padx=4)
    sx = tk.Spinbox(coord_frame, from_=0, to=3840, textvariable=cur_x, width=6,
                    command=refresh_zoom)
    sx.grid(row=0, column=1, padx=4)
    tk.Label(coord_frame, text="Y:").grid(row=0, column=2, padx=4)
    sy = tk.Spinbox(coord_frame, from_=0, to=2160, textvariable=cur_y, width=6,
                    command=refresh_zoom)
    sy.grid(row=0, column=3, padx=4)

    def on_fix():
        result[0] = (cur_x.get(), cur_y.get())
        if red_dot[0]:
            red_dot[0].destroy()
        win.destroy()

    def on_cancel():
        if red_dot[0]:
            red_dot[0].destroy()
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=8)
    tk.Button(btn_frame, text="Зафиксировать", bg="#2d7a2d", fg="white",
              font=("Arial", 11, "bold"), width=16, command=on_fix).pack(side="left", padx=8)
    tk.Button(btn_frame, text="Отмена", command=on_cancel).pack(side="left", padx=8)

    refresh_zoom()
    win.wait_window()
    return result[0]


def run_calibration() -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """
    Run sequential 2-point calibration UI.
    Returns (point_a, point_b). Either can be None if user cancelled.
    """
    if not _DEPS_OK:
        raise ImportError("mss and Pillow are required for calibration UI")

    screenshot = _grab_full_screen()

    root = tk.Tk()
    root.withdraw()  # hide root window

    point_a = _calibrate_one_point(
        root, screenshot, REF_A,
        "Точка А — центр мини-карты (лево-низ)"
    )
    if point_a is None:
        root.destroy()
        return None, None

    point_b = _calibrate_one_point(
        root, screenshot, REF_B,
        "Точка Б — крестик серебра (право-верх)"
    )
    root.destroy()
    return point_a, point_b
```

- [ ] **Step 2: Smoke test (manual — requires display)**

```
cd C:\BattleBot && python -c "
from calibration_ui import run_calibration
a, b = run_calibration()
print('Point A:', a)
print('Point B:', b)
"
```
Expected: Two sequential windows appear. After fixing both points, prints coordinates.

- [ ] **Step 3: Commit**

```bash
cd C:\BattleBot && git add calibration_ui.py
git commit -m "feat: add calibration UI with magnifier and red dot"
```

---

## Task 4: «Калибровка» tab in main.py

**Files:**
- Modify: `main.py`

Add a new tab between existing tabs. The tab contains:
- Profile dropdown (Client / Chrome / Firefox)
- Status line showing current scale_x, scale_y, anchor
- «Загрузить» button
- «Калибровать» button (launches calibration_ui)
- «Сохранить» button

- [ ] **Step 1: Add import and tab setup in main.py**

Find the `__init__` section where tabs are created in `main.py`. Add the new tab and setup method.

At the top of `main.py`, add after existing imports:

```python
import os as _os
from coord_manager import coord_manager
```

- [ ] **Step 2: Add tab to tabview**

Find where `self.tabview` is created in `main.py` (search for `CTkTabview` or `add(`). Add the calibration tab:

```python
self.tab_calibration = self.tabview.add("КАЛИБРОВКА")
```

Add call to setup in `__init__` after other `setup_*_tab()` calls:
```python
self.setup_calibration_tab()
```

- [ ] **Step 3: Implement setup_calibration_tab method**

Add this method to `TotalHunterApp`:

```python
def setup_calibration_tab(self):
    import os
    PROFILES = {
        "Client":  "profiles/profile_client.json",
        "Chrome":  "profiles/profile_chrome.json",
        "Firefox": "profiles/profile_firefox.json",
    }

    ctk.CTkLabel(
        self.tab_calibration,
        text="Калибровка координат",
        font=ctk.CTkFont(size=16, weight="bold")
    ).pack(pady=(16, 4))

    ctk.CTkLabel(
        self.tab_calibration,
        text="Выберите профиль и нажмите «Калибровать».\nЗатем кликните на Точку А (мини-карта) и Точку Б (серебро).",
        font=ctk.CTkFont(size=11),
        text_color="gray",
        justify="center",
    ).pack(pady=(0, 12))

    # Profile dropdown
    profile_frame = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
    profile_frame.pack(fill="x", padx=40, pady=4)
    ctk.CTkLabel(profile_frame, text="Профиль:").pack(side="left")
    self._cal_profile_var = ctk.StringVar(value="Client")
    ctk.CTkOptionMenu(
        profile_frame,
        values=list(PROFILES.keys()),
        variable=self._cal_profile_var,
    ).pack(side="right")

    # Status label
    self._cal_status_label = ctk.CTkLabel(
        self.tab_calibration,
        text="Не откалиброван",
        font=ctk.CTkFont(size=11),
        text_color="orange",
    )
    self._cal_status_label.pack(pady=8)

    def _update_status():
        self._cal_status_label.configure(
            text=f"scale_x={coord_manager.scale_x:.3f}  scale_y={coord_manager.scale_y:.3f}\n"
                 f"anchor=({coord_manager.anchor_x}, {coord_manager.anchor_y})",
            text_color="#45bf45",
        )

    def _load_profile():
        path = PROFILES[self._cal_profile_var.get()]
        if not os.path.exists(path):
            messagebox.showerror("Ошибка", f"Файл не найден: {path}")
            return
        coord_manager.load(path)
        _update_status()

    def _calibrate():
        from calibration_ui import run_calibration
        self.withdraw()  # hide bot window during calibration
        try:
            point_a, point_b = run_calibration()
        finally:
            self.deiconify()
        if point_a and point_b:
            coord_manager.calibrate(point_a, point_b)
            _update_status()

    def _save_profile():
        path = PROFILES[self._cal_profile_var.get()]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        coord_manager.save(path)
        messagebox.showinfo("Сохранено", f"Профиль сохранён:\n{path}")

    # Buttons
    btn_frame = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
    btn_frame.pack(fill="x", padx=40, pady=8)
    ctk.CTkButton(btn_frame, text="Загрузить", command=_load_profile, width=120).pack(
        side="left", padx=4)
    ctk.CTkButton(btn_frame, text="Калибровать", command=_calibrate,
                  fg_color="#2d7a2d", width=140).pack(side="left", padx=4)
    ctk.CTkButton(btn_frame, text="Сохранить", command=_save_profile, width=120).pack(
        side="left", padx=4)

    # Auto-load last profile on startup
    last_profile = self._load_gui_config().get("last_calibration_profile", "Client")
    self._cal_profile_var.set(last_profile)
    default_path = PROFILES.get(last_profile, PROFILES["Client"])
    if os.path.exists(default_path):
        try:
            coord_manager.load(default_path)
            _update_status()
        except Exception:
            pass
```

- [ ] **Step 4: Save last used profile to gui_config.json on selection change**

In `_save_profile()` and `_load_profile()`, after the main action, add:
```python
cfg = self._load_gui_config()
cfg["last_calibration_profile"] = self._cal_profile_var.get()
with open(GUI_CONFIG_PATH, "w") as f:
    json.dump(cfg, f, indent=2)
```

- [ ] **Step 5: Check _load_gui_config exists in main.py**

Search for `_load_gui_config` — if the method doesn't exist, add it to `TotalHunterApp`:
```python
def _load_gui_config(self) -> dict:
    if os.path.exists(GUI_CONFIG_PATH):
        with open(GUI_CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}
```

- [ ] **Step 6: Commit**

```bash
cd C:\BattleBot && git add main.py
git commit -m "feat: add Calibration tab to main GUI"
```

---

## Task 5: Migrate crypt_hunter.py

**Files:**
- Modify: `crypt_hunter.py`

Replace all `window_scaler` usage with `coord_manager`.

- [ ] **Step 1: Replace import in crypt_hunter.py**

Find (around line 28):
```python
from window_scaler import scale_region, scale_coord
```

Replace with:
```python
from coord_manager import coord_manager as _cm
scale_coord  = _cm.to_screen
scale_region = _cm.to_region
```

- [ ] **Step 2: Verify no other window_scaler references remain**

```
cd C:\BattleBot && grep -r "window_scaler" . --include="*.py"
```
Expected: no output (zero matches).

- [ ] **Step 3: Run existing crypt_hunter tests**

```
cd C:\BattleBot && python -m pytest test_crypt_hunter.py -v --tb=short 2>&1 | tail -20
```
Expected: all 62 tests PASS (same as before migration).

- [ ] **Step 4: Commit**

```bash
cd C:\BattleBot && git add crypt_hunter.py
git commit -m "refactor: migrate crypt_hunter from window_scaler to coord_manager"
```

---

## Task 6: Remove window_scaler.py

**Files:**
- Delete: `window_scaler.py`
- Delete: `test_window_scaler.py`

- [ ] **Step 1: Verify no imports remain**

```
cd C:\BattleBot && grep -r "window_scaler" . --include="*.py"
```
Expected: zero matches.

- [ ] **Step 2: Delete files**

```bash
cd C:\BattleBot && git rm window_scaler.py test_window_scaler.py
```

- [ ] **Step 3: Run full test suite**

```
cd C:\BattleBot && python -m pytest test_coord_manager.py test_crypt_hunter.py -v --tb=short 2>&1 | tail -30
```
Expected: all tests PASS, no import errors.

- [ ] **Step 4: Commit**

```bash
cd C:\BattleBot && git commit -m "chore: remove window_scaler.py (replaced by coord_manager)"
```

---

## Self-Review

**Spec coverage:**
- [x] 2-point calibration math (Task 1)
- [x] Separate scale_x / scale_y (Task 1 `calibrate()`)
- [x] REF_A=(90,925), REF_B=(648,47) constants (Task 1)
- [x] Profile save/load — 3 JSON files (Task 2)
- [x] GUI magnifier zoom 600% (Task 3, ZOOM_FACTOR=6)
- [x] Red dot live feedback (Task 3, `_show_red_dot`)
- [x] Click in zoom → repositions point (Task 3, `on_canvas_click`)
- [x] Manual X/Y entry (Task 3, Spinbox)
- [x] «Зафиксировать» button (Task 3)
- [x] Sequential A then B (Task 3, `run_calibration`)
- [x] Калибровка tab in main.py (Task 4)
- [x] Profile dropdown + Load/Calibrate/Save buttons (Task 4)
- [x] Status shows scale_x/scale_y/anchor (Task 4)
- [x] Auto-load last profile on startup (Task 4)
- [x] crypt_hunter migration (Task 5)
- [x] window_scaler removal (Task 6)

**Type consistency check:**
- `coord_manager.to_screen(x, y)` — used as `scale_coord` in Task 5 ✓
- `coord_manager.to_region(x, y, w, h)` — used as `scale_region` in Task 5 ✓
- `coord_manager.calibrate(a_user, b_user)` — called in Task 4 `_calibrate()` ✓
- `run_calibration()` returns `(point_a, point_b)` — consumed in Task 4 ✓

**Note on REF_B:** `(648, 47)` is an estimate for the silver crosshair at 1920×1080. If after running the bot clicks are slightly off at exact 1920×1080, measure the actual pixel in-game and update `REF_B` in `coord_manager.py`. The calibration system will then be accurate for all other resolutions.
