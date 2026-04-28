"""
navigator.py — Comb/roller coastal navigator for Total Battle Exchange Hunter.

Navigation pattern (CompassNavigator):
  DIVE 'dive_depth' screens inland → SHIFT 1 click along coast →
  RETURN same number of steps → SHIFT 1 click → repeat forever.

Coast direction is auto-detected from minimap water distribution on first step.
Shift distance = 1 joystick click (overlap controlled by step/p_range setting).
"""
import re
import math
import random
import time
import winsound
import threading
import numpy as np
import cv2
import pyautogui

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def _clamp_vec(v_new: tuple, v_prev: tuple, max_delta: float) -> tuple:
    """
    Clamp rotation of v_new relative to v_prev to max_delta radians.
    Returns unit vector. Used by angular damper in CoastalSnakeNavigator.
    """
    dot   = max(-1.0, min(1.0, v_prev[0]*v_new[0] + v_prev[1]*v_new[1]))
    angle = math.acos(dot)
    if angle <= max_delta:
        return v_new
    cross = v_prev[0]*v_new[1] - v_prev[1]*v_new[0]
    theta = math.copysign(max_delta, cross)
    c, s  = math.cos(theta), math.sin(theta)
    return (v_prev[0]*c - v_prev[1]*s, v_prev[0]*s + v_prev[1]*c)


# ─────────────────────────────────────────────
# PositionReader — OCR coordinates
# ─────────────────────────────────────────────

class PositionReader:
    def __init__(self, crop_box: tuple[int, int, int, int] = (0, 1000, 250, 1080)):
        self.crop_box = crop_box
        self._pattern = re.compile(r'X\s*[:]\s*(\d+)\s+Y\s*[:]\s*(\d+)', re.IGNORECASE)

    def _preprocess(self, img):
        arr = np.array(img.convert('RGB'))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        from PIL import Image as PILImage
        return PILImage.fromarray(thresh)

    def _parse_ocr(self, text: str) -> tuple[int, int] | None:
        m = self._pattern.search(text)
        if not m:
            return None
        try:
            return (int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None

    def read(self, screenshot_np: np.ndarray) -> tuple[int, int] | None:
        try:
            from PIL import Image
            img = Image.fromarray(screenshot_np)
            h, w = screenshot_np.shape[:2]
            x1, y1, x2, y2 = self.crop_box
            crops = [
                (x1, y1,      x2,      y2),
                (x1, y1 - 15, x2 + 50, y2),
                (x1, y1 - 30, x2 + 80, y2 + 10),
                (x1, h - 100, x2 + 80, h),
            ]
            for cx1, cy1, cx2, cy2 in crops:
                cy1 = max(0, cy1); cy2 = min(h, cy2); cx2 = min(w, cx2)
                crop = img.crop((cx1, cy1, cx2, cy2))
                scaled = crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST)
                for proc in [scaled, self._preprocess(scaled)]:
                    for cfg in ['--psm 12', '--psm 11', '--psm 6']:
                        result = self._parse_ocr(pytesseract.image_to_string(proc, config=cfg))
                        if result:
                            return result
            return None
        except Exception:
            return None


# ─────────────────────────────────────────────
# Minimap preprocessing
# ─────────────────────────────────────────────

MINIMAP_ZOOM      = 3
SCAN_AREA         = 180
MIN_COAST_STEPS   = 3   # ignore water for first N steps (cross small rivers)
WATER_STREAK_STOP = 2   # consecutive water frames = real coast
MAX_STEPS_SAFETY  = 80  # hard safety cap per dive/return leg

LAND_HSV  = [(5,  40,  40), (95,  255, 255)]
WATER_HSV = [(100, 60,  50), (140, 255, 255)]


# ─────────────────────────────────────────────
# FootprintCanvas — visited-cell memory
# ─────────────────────────────────────────────

class FootprintCanvas:
    """
    Step-space grid that records visit timestamps.
    draw_ray() stamps a vertical line of cells at each dive entry so the
    bot sees a red "wall" on the minimap and avoids previously covered coast.
    render_overlay() paints stamped cells as RED pixels (BGR 0,0,255).
    Red is neutral to get_land_water_masks() — neither water nor land —
    so water/coast detection is unaffected; only analyze_footprint_zone()
    reads the red channel.
    """

    GRID_SIZE       = 401          # 200 steps in any direction from center
    CENTER          = 200          # starting cell index
    FOOTPRINT_COLOR = (0, 0, 255)  # BGR: Red — does NOT trigger water detection
    BEACON_COLOR    = (255, 0, 255) # BGR: Magenta — H=150, outside land[5-95] & water[100-140]

    def __init__(self):
        self._grid      = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.float64)
        self._cx: float = float(self.CENTER)
        self._cy: float = float(self.CENTER)
        self._beacon_cx: int | None = None
        self._beacon_cy: int | None = None

    def draw_beacon(self, coast_vec: tuple, offset_coast_steps: int = 1) -> None:
        """Ставит маяк на 1 шаг вправо (перпендикулярно нырку) от текущей позиции."""
        norm = np.hypot(coast_vec[0], coast_vec[1])
        if norm == 0:
            return
        cdx, cdy = coast_vec[0] / norm, coast_vec[1] / norm
        self._beacon_cx = max(0, min(self.GRID_SIZE - 1,
                                     int(round(self._cx + offset_coast_steps * cdx))))
        self._beacon_cy = max(0, min(self.GRID_SIZE - 1,
                                     int(round(self._cy + offset_coast_steps * cdy))))

    def is_beyond_beacon_line(self, inland_vec: tuple, tolerance: float = 1.0) -> bool:
        """True когда бот подошёл к Лучу Маяка или пересёк его (Gemini: за 1 шаг ДО).
        Луч Маяка — линия через маяк параллельно берегу (⊥ inland_vec).
        tolerance=1.0 → стоп за 1 шаг до линии."""
        if self._beacon_cx is None:
            return False
        dcx = self._cx - self._beacon_cx
        dcy = self._cy - self._beacon_cy
        # проекция на seaward = -inland_vec; tolerance сдвигает порог ближе к боту
        return (dcx * (-inland_vec[0]) + dcy * (-inland_vec[1])) >= -tolerance

    def record(self, dx: float, dy: float) -> None:
        """Track current grid position (called on every step). Accepts fractional steps."""
        self._cx = max(0.0, min(float(self.GRID_SIZE - 1), self._cx + dx))
        self._cy = max(0.0, min(float(self.GRID_SIZE - 1), self._cy + dy))

    def draw_ray(
        self,
        inland_vec: tuple,
        coast_vec: tuple,
        ray_half_length: int = 7,
        extra_coast_steps: int = 0,
    ) -> None:
        """
        Stamp a ray of cells along inland_vec direction.

        Base position: 1 step behind current pos in -coast_vec direction.
        extra_coast_steps: additional offset in +coast_vec direction.
          0 = left (entry) wall — 1 step behind
          2 = right (mirror) wall — 1 step ahead, forming a 1-screen corridor
        """
        coast_dx = int(round(coast_vec[0]))
        coast_dy = int(round(coast_vec[1]))
        icx = int(round(self._cx))
        icy = int(round(self._cy))
        rcx = max(0, min(self.GRID_SIZE - 1,
                         icx - coast_dx + extra_coast_steps * coast_dx))
        rcy = max(0, min(self.GRID_SIZE - 1,
                         icy - coast_dy + extra_coast_steps * coast_dy))

        norm = np.hypot(inland_vec[0], inland_vec[1])
        if norm == 0:
            return
        idx, idy = inland_vec[0] / norm, inland_vec[1] / norm

        now = time.time()
        for k in range(-ray_half_length, ray_half_length + 1):
            gx = max(0, min(self.GRID_SIZE - 1, rcx + int(round(k * idx))))
            gy = max(0, min(self.GRID_SIZE - 1, rcy + int(round(k * idy))))
            self._grid[gy, gx] = now

    def render_overlay(
        self,
        minimap_shape: tuple,
        ttl_sec: float,
        pixels_per_step: int = 20,
    ) -> np.ndarray:
        """
        Return a BGR image (same size as minimap_shape) with recent footprint
        cells painted as FOOTPRINT_COLOR circles. Cells older than ttl_sec
        are transparent (black).
        """
        h, w    = minimap_shape[:2]
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        now     = time.time()
        half_x  = w // (2 * pixels_per_step) + 1
        half_y  = h // (2 * pixels_per_step) + 1
        radius  = max(2, pixels_per_step // 2)
        icx     = int(round(self._cx))
        icy     = int(round(self._cy))

        for dy in range(-half_y, half_y + 1):
            for dx in range(-half_x, half_x + 1):
                gx = icx + dx
                gy = icy + dy
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
        self._cx        = float(self.CENTER)
        self._cy        = float(self.CENTER)
        self._beacon_cx = None
        self._beacon_cy = None

    def render_beacon_overlay(self, minimap_shape: tuple, pixels_per_step: int = 20) -> np.ndarray:
        """Return BGR image with magenta beacon circle.
        Always drawn: clamped to minimap edge when beyond bounds so the bot
        always has a visible direction target regardless of dive depth."""
        h, w = minimap_shape[:2]
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        if self._beacon_cx is None:
            return overlay
        dx = self._beacon_cx - self._cx
        dy = self._beacon_cy - self._cy
        px_f = w // 2 + dx * pixels_per_step
        py_f = h // 2 + dy * pixels_per_step
        margin = 14   # keep circle fully inside edge
        # Clamp to minimap interior — edge position still points correct direction
        px = int(round(max(margin, min(w - 1 - margin, px_f))))
        py = int(round(max(margin, min(h - 1 - margin, py_f))))
        cv2.circle(overlay, (px, py), 12, self.BEACON_COLOR, -1)
        return overlay


def _prepare_minimap(frame_bgr: np.ndarray) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    zoomed = cv2.resize(frame_bgr, (w * MINIMAP_ZOOM, h * MINIMAP_ZOOM),
                        interpolation=cv2.INTER_LINEAR)
    hsv = cv2.cvtColor(zoomed, cv2.COLOR_BGR2HSV)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    hsv[:, :, 2] = clahe.apply(hsv[:, :, 2])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def get_land_water_masks(minimap_bgr: np.ndarray):
    """Returns (land_mask, water_mask) on the ZOOMED minimap."""
    prepared = _prepare_minimap(minimap_bgr)
    hsv = cv2.cvtColor(prepared, cv2.COLOR_BGR2HSV)

    land  = cv2.inRange(hsv, np.array(LAND_HSV[0]),  np.array(LAND_HSV[1]))
    water = cv2.inRange(hsv, np.array(WATER_HSV[0]), np.array(WATER_HSV[1]))

    b = prepared[:, :, 0].astype(np.float32)
    g = prepared[:, :, 1].astype(np.float32)
    r = prepared[:, :, 2].astype(np.float32)
    water_bgr = np.where((b > g * 1.25) & (b > r * 1.25),
                         np.uint8(255), np.uint8(0)).astype(np.uint8)
    water = cv2.bitwise_or(water, water_bgr)

    return land, water


def is_water_center_screen(frame_bgr: np.ndarray, radius: int = 120) -> bool:
    """True if the centre of the full game screen looks like water."""
    h, w = frame_bgr.shape[:2]
    cy, cx = h // 2, w // 2
    crop = frame_bgr[max(0, cy - radius):cy + radius,
                     max(0, cx - radius):cx + radius]
    if crop.size == 0:
        return False
    avg = crop.mean(axis=(0, 1))
    b, g, r = float(avg[0]), float(avg[1]), float(avg[2])
    return b > g * 1.2 and b > r * 1.2


# ─────────────────────────────────────────────
# CompassNavigator
# ─────────────────────────────────────────────

class CompassNavigator:
    """
    Comb/roller pattern navigator. No memory canvas, no traps.

    Each step() call makes exactly one joystick click:

    States:
      INIT     — detect coast direction from minimap, then transition to DIVING
      DIVING   — click dive_dir; after dive_depth steps (or water) → click shift, go RETURNING
      RETURNING— click -dive_dir; after all steps returned → click shift, go DIVING

    Shift distance = 1 joystick click (p_range pixels).
    Overlap between adjacent dives is controlled by the p_range (step) setting in GUI.
    """

    _DIRS = {'RIGHT': (1, 0), 'LEFT': (-1, 0), 'UP': (0, -1), 'DOWN': (0, 1)}

    def __init__(
        self,
        center_x: int  = 90,
        center_y: int  = 925,
        step: int      = 13,
        # legacy compat (unused):
        dive_depth: int | None = None,
        max_depth: int | None = None,
        inertia: float | None = None,
        random_w: float | None = None,
        magnet: float | None = None,
    ):
        self.center_x = center_x
        self.center_y = center_y

        # Aspect-ratio correction: same step → different game-unit coverage
        # per axis on a 16:9 screen.  Horizontal screen = wider → needs more
        # pixels to shift the same game distance as a vertical step.
        sw, sh = pyautogui.size()
        aspect = sw / sh                          # 1920/1080 ≈ 1.778
        self.p_range_y = step                     # vertical step (pixels)
        self.p_range_x = max(1, round(step * aspect))  # horizontal step (pixels)

        self._state          = 'INIT'
        self._dive_dir       = (0, 1)   # default: dive DOWN
        self._shift_dir      = (1, 0)   # default: shift RIGHT
        self._steps_in_state = 0        # steps taken since last state transition
        self._water_streak   = 0        # consecutive water detections

    def reset(self):
        """Restart state machine — re-detects coast direction on next step."""
        self._state          = 'INIT'
        self._steps_in_state = 0
        self._water_streak   = 0

    # ── calibration helper (same API as old PacmanJoystick) ──────────
    def move(self, direction: str):
        """Single cardinal click — used by calibration.py."""
        dx, dy = self._DIRS[direction]
        pyautogui.click(self.center_x + dx * self.p_range_x,
                        self.center_y + dy * self.p_range_y)

    # ── internal helpers ──────────────────────────────────────────────
    def _click(self, dx: int, dy: int):
        pyautogui.click(
            self.center_x + dx * self.p_range_x,
            self.center_y + dy * self.p_range_y,
        )

    def _detect_coast_dirs(self) -> tuple:
        """
        Grab minimap, count water pixels in each half.
        Returns (dive_dir, shift_dir) as (dx, dy) tuples.
        More water on top  → dive DOWN  (0, 1), shift RIGHT (1, 0)
        More water on left → dive RIGHT (1, 0), shift DOWN  (0, 1)
        etc.
        """
        offset = SCAN_AREA // 2
        shot = pyautogui.screenshot(region=(
            self.center_x - offset, self.center_y - offset,
            SCAN_AREA, SCAN_AREA,
        ))
        minimap = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

        _, water_z = get_land_water_masks(minimap)
        water = cv2.resize(water_z, (SCAN_AREA, SCAN_AREA),
                           interpolation=cv2.INTER_NEAREST)

        h, w = water.shape
        cy, cx = h // 2, w // 2

        top   = float(water[:cy, :].sum())
        bot   = float(water[cy:, :].sum())
        left  = float(water[:, :cx].sum())
        right = float(water[:, cx:].sum())

        # No water visible — keep defaults
        if top + bot + left + right == 0:
            return (0, 1), (1, 0)

        vert  = top - bot       # +: more water on top  → dive DOWN
        horiz = left - right    # +: more water on left → dive RIGHT

        if abs(vert) >= abs(horiz):
            dive  = (0, 1) if vert > 0 else (0, -1)
            shift = (1, 0)
        else:
            dive  = (1, 0) if horiz > 0 else (-1, 0)
            shift = (0, 1)

        return dive, shift

    # ── main navigation step ──────────────────────────────────────────
    def step(self, is_water: bool = False) -> bool:
        """
        Ricochet navigator: dive until coast → shift → return until coast → shift → repeat.

        Small rivers are crossed because:
          - Water is ignored for the first MIN_COAST_STEPS steps of each leg.
          - After that, WATER_STREAK_STOP consecutive water frames confirms real coast.

        is_water: True if current screen centre looks like water.
        Returns True always (a click is always made).
        """
        if self._state == 'INIT':
            self._dive_dir, self._shift_dir = self._detect_coast_dirs()
            self._state          = 'DIVING'
            self._steps_in_state = 0
            self._water_streak   = 0

        if self._state == 'DIVING':
            self._steps_in_state += 1

            # Update streak — only after minimum steps (ignore rivers)
            if self._steps_in_state > MIN_COAST_STEPS and is_water:
                self._water_streak += 1
            else:
                self._water_streak = 0

            coast_reached = (
                self._water_streak >= WATER_STREAK_STOP or
                self._steps_in_state >= MAX_STEPS_SAFETY
            )

            if coast_reached:
                self._water_streak   = 0
                self._steps_in_state = 0
                self._click(*self._shift_dir)
                self._state = 'RETURNING'
            else:
                self._click(*self._dive_dir)
            return True

        if self._state == 'RETURNING':
            self._steps_in_state += 1

            if self._steps_in_state > MIN_COAST_STEPS and is_water:
                self._water_streak += 1
            else:
                self._water_streak = 0

            coast_reached = (
                self._water_streak >= WATER_STREAK_STOP or
                self._steps_in_state >= MAX_STEPS_SAFETY
            )

            if coast_reached:
                self._water_streak   = 0
                self._steps_in_state = 0
                self._click(*self._shift_dir)
                self._state = 'DIVING'
            else:
                dx, dy = self._dive_dir
                self._click(-dx, -dy)
            return True

        return False


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
        footprint_ttl: float    = 3600.0,   # 1 час — стена жив��т всю сессию
        footprint_enabled: bool = True,
        pixels_per_step: int | None = None,   # None = use step (joystick step = canvas scale)
        force_shift_after: int  = 0,   # 0 = disabled; N = force shift every N non-shift steps
        coast_detect_radius: int = 50,  # конус детекции берега при возврате (px на мини-карте)
        max_pitch_delta: float  = 15.0,  # degrees; 0 = disabled
        max_footprint_overlap: float = 0.3,  # 0.0-1.0; skip column if overlap >= this
        scan_dir: int = 1,   # Gemini: +1 или -1, задаёт сторону сдвига (вправо/влево)
    ):
        self.center_x         = center_x
        self.center_y         = center_y
        self.scan_dir         = scan_dir   # направление сканирования

        sw, sh = pyautogui.size()
        aspect = sw / sh
        self.p_range_y = step
        self.p_range_x = max(1, round(step * aspect))

        self.max_inland_steps       = max_inland_steps
        self.ocean_land_ratio       = ocean_land_ratio
        self.min_water_px           = min_water_px
        self.homing_max_steps       = homing_max_steps
        self.coast_ema_alpha        = coast_ema_alpha
        self.coast_detect_radius    = coast_detect_radius
        self._max_pitch_delta       = math.radians(max_pitch_delta)
        self._max_footprint_overlap = max_footprint_overlap
        self._prev_inland_vec   = None


        self._state              = 'HOMING'
        self._inland_steps       = 0
        self._homing_steps       = 0
        self._return_steps: float = 0.0
        self._dive_distance: float = 0.0
        self._ocean_streak: int   = 0    # Gemini: гистерезис осцилляции

        self._coast_angle        = 0.0
        self._inland_vec         = (1.0, 0.0)
        self._coast_vec          = (0.0, 1.0)
        self._angle_init         = False
        # Fixed shift direction — locked at first coast contact, never changes
        self._shift_vec     = (0.0, 1.0)
        self._shift_vec_set = False

        self._footprint_ttl     = footprint_ttl
        self._footprint_enabled = footprint_enabled
        self._pixels_per_step   = pixels_per_step if pixels_per_step is not None else step
        self._footprint         = FootprintCanvas()

        self._force_shift_after = force_shift_after
        self._steps_since_shift = 0

    def reset(self):
        self._state         = 'HOMING'
        self._inland_steps  = 0
        self._homing_steps  = 0
        self._return_steps  = 0
        self._ocean_streak  = 0

        self._angle_init         = False
        self._inland_vec         = (1.0, 0.0)
        self._coast_vec          = (0.0, 1.0)
        self._coast_angle        = 0.0
        self._shift_vec          = (0.0, 1.0)
        self._shift_vec_set      = False
        self._steps_since_shift  = 0
        self._dive_distance      = 0.0
        self._footprint.reset()
        self._prev_inland_vec = None

    # ── calibration helper (same API as CompassNavigator) ────────────────
    def move(self, direction: str):
        _DIRS = {'RIGHT': (1, 0), 'LEFT': (-1, 0), 'UP': (0, -1), 'DOWN': (0, 1)}
        dx, dy = _DIRS[direction]
        pyautogui.click(self.center_x + dx * self.p_range_x,
                        self.center_y + dy * self.p_range_y)

    # ── internal helpers ─────────────────────────────────────────────────
    def _grab_minimap(self) -> np.ndarray:
        from minimap_reader import get_minimap_snapshot
        mm = get_minimap_snapshot(self.center_x, self.center_y)
        if self._footprint_enabled:
            overlay = self._footprint.render_overlay(
                mm.shape, self._footprint_ttl, self._pixels_per_step)
            mask = overlay.any(axis=2)
            mm[mask] = overlay[mask]
            # Beacon layer on top of walls (magenta dot — visual target for RETURNING)
            beacon_ov = self._footprint.render_beacon_overlay(mm.shape, self._pixels_per_step)
            b_mask = beacon_ov.any(axis=2)
            mm[b_mask] = beacon_ov[b_mask]
        return mm

    def _click_vec(self, dx: float, dy: float, multiplier: float = 1.0, record: bool = True):
        """Click joystick in direction (dx, dy) with optional step multiplier."""
        norm = np.hypot(dx, dy)
        if norm == 0:
            return
        ndx, ndy = dx / norm, dy / norm
        pyautogui.click(
            int(self.center_x + ndx * self.p_range_x * multiplier),
            int(self.center_y + ndy * self.p_range_y * multiplier),
        )
        if self._footprint_enabled and record:
            self._footprint.record(ndx * multiplier, ndy * multiplier)

    def _shift_click(self) -> None:
        """
        Lateral shift — НАМЕРТВО perpendicular to inland_vec.

        Gemini: sv кешируется после первого вычисления.
        Обновляется только если inland_vec изменился > 45° (cos < 0.707).
        """
        iv  = self._inland_vec
        m   = self.scan_dir
        sv  = (-iv[1] * m, iv[0] * m)
        if not self._shift_vec_set:
            self._shift_vec     = sv
            self._shift_vec_set = True
        else:
            dot = self._shift_vec[0]*sv[0] + self._shift_vec[1]*sv[1]
            if dot < 0.707:   # угол > 45° → обновляем кеш
                self._shift_vec = sv
        self._click_vec(*self._shift_vec)
        self._steps_since_shift = 0

    def _move_perpendicular(self, toward_water: bool, multiplier: float = 1.0) -> None:
        """
        ЗАПРЕТ на движение вдоль берега.
        Всегда движется строго по ±inland_vec — только перпендикулярно берегу.

        toward_water=True  → клик в сторону воды  (-inland_vec = seaward)
        toward_water=False → клик вглубь суши      (+inland_vec = inland)
        multiplier         → масштаб шага (1.0 норм, 1.5/2.0 перепрыгнуть воду)
        """
        iv = self._inland_vec
        if toward_water:
            self._click_vec(-iv[0], -iv[1], multiplier)
        else:
            self._click_vec(iv[0], iv[1], multiplier)
        self._steps_since_shift += 1

    def _update_coast_angle(self, new_angle: float):
        """EMA smoothing of coast angle to handle noisy minimap readings.

        PCA eigenvector direction is ambiguous — it can return angle OR angle+π
        for the same coastline.  We fix this by flipping new_angle by π whenever
        it differs from the current angle by more than 90°, so the EMA never
        rotates the coast_vec through a 180° flip.
        """
        if not self._angle_init:
            self._coast_angle = new_angle
            self._angle_init  = True
        else:
            a    = self._coast_angle
            # Correct for PCA π-ambiguity before EMA
            diff_raw = (new_angle - a + np.pi) % (2 * np.pi) - np.pi
            if abs(diff_raw) > np.pi / 2:
                # PCA returned the opposite end of the same line — flip it
                new_angle = new_angle + np.pi
                diff_raw  = (new_angle - a + np.pi) % (2 * np.pi) - np.pi
            self._coast_angle = (a + self.coast_ema_alpha * diff_raw) % (2 * np.pi)

        ca = self._coast_angle
        self._coast_vec  = (float(np.cos(ca)),           float(np.sin(ca)))
        self._inland_vec = (float(np.cos(ca + np.pi/2)), float(np.sin(ca + np.pi/2)))

        # FIX: sync shift_vec = coast_vec while not locked — prevents shift_vec == inland_vec
        # when PCA returns 0.0 fallback (the root cause of "no shift" bug).
        if not self._shift_vec_set:
            self._shift_vec = tuple(self._coast_vec)


    def _validate_inland_direction(self, mm) -> None:
        """
        Fix 2: Ensure _inland_vec points toward land, not ocean.

        After EMA updates _inland_vec to one of the two perpendiculars,
        we check both and pick the one with more land pixels.
        If neither has land (open ocean), we keep the current direction.
        """
        from minimap_reader import analyze_forward_zone

        ca    = self._coast_angle
        perp1 = (float(np.cos(ca + np.pi/2)), float(np.sin(ca + np.pi/2)))
        perp2 = (-perp1[0], -perp1[1])

        z1 = analyze_forward_zone(mm, perp1, radius=50,
                                   ocean_land_ratio=self.ocean_land_ratio,
                                   min_water_px=self.min_water_px)['land_px']
        z2 = analyze_forward_zone(mm, perp2, radius=50,
                                   ocean_land_ratio=self.ocean_land_ratio,
                                   min_water_px=self.min_water_px)['land_px']

        if z1 > 0 or z2 > 0:          # at least one side has visible land
            self._inland_vec = perp1 if z1 >= z2 else perp2

    def _peek_step(self, direction_vec: tuple) -> float | None:
        """
        Read minimap in direction_vec at 3 depths (1/2/3 screens = radius 30/60/90px).
        Returns step multiplier to jump over water, or None if ocean/coast boundary.
        """
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

    def _is_at_coast_now(self) -> bool:
        """ТОЛЬКО линия маяка. Маяк всегда установлен перед RETURNING.
        Никаких визуальных проверок воды — маяк единственная точка остановки."""
        if self._footprint_enabled and self._footprint._beacon_cx is not None:
            return self._footprint.is_beyond_beacon_line(self._inland_vec, tolerance=0.5)
        return False

    def _find_beacon_on_minimap(self, mm: np.ndarray):
        """Detect magenta beacon dot on minimap via HSV moments.
        Returns (dx, dy, dist) from minimap center, or None if not found."""
        try:
            hsv  = cv2.cvtColor(mm, cv2.COLOR_BGR2HSV)
            # Magenta: H≈150 (H=140-165), S>150, V>150
            mask = cv2.inRange(hsv, np.array([140, 150, 150]), np.array([165, 255, 255]))
            M    = cv2.moments(mask)
            if M['m00'] < 50:
                return None
            bx   = M['m10'] / M['m00']
            by_  = M['m01'] / M['m00']
            h, w = mm.shape[:2]
            dx   = bx - w / 2
            dy   = by_ - h / 2
            return (dx, dy, math.hypot(dx, dy))
        except Exception:
            return None

    def _read_minimap(self) -> dict:
        """
        Grab minimap, update coast angle/direction, return navigation info.
        Called only from HOMING state — vectors are frozen for DIVING/RETURNING.

        Wide snapshot (coast_snap_size) for PCA smoothing; standard 180px
        snapshot for zone analysis.
        """
        from minimap_reader import detect_coast_angle, analyze_forward_zone, analyze_footprint_zone

        mm = self._grab_minimap()  # 180px standard snapshot + red footprint overlay

        raw_angle = detect_coast_angle(mm)
        if raw_angle != 0.0 or not self._angle_init:
            self._update_coast_angle(raw_angle)

        # Lock shift direction only from a REAL coast detection (raw_angle ≠ 0 means
        # PCA found enough boundary pixels — not the fallback 0.0).
        # This prevents locking shift_vec from a fallback angle and then
        # shifting in the wrong direction forever.
        # Lock on first REAL detection (raw_angle ≠ 0.0 = PCA found real boundary pixels).
        # _shift_vec is already kept = coast_vec via _update_coast_angle.
        if raw_angle != 0.0 and not self._shift_vec_set:
            self._shift_vec_set = True

        self._validate_inland_direction(mm)

        fwd = analyze_forward_zone(
            mm, self._inland_vec,
            radius=60,
            ocean_land_ratio=self.ocean_land_ratio,
            min_water_px=self.min_water_px,
        )

        seaward_vec = (-self._inland_vec[0], -self._inland_vec[1])
        coast_zone  = analyze_forward_zone(mm, seaward_vec, radius=25,   # Gemini: 25px
                                           ocean_land_ratio=self.ocean_land_ratio,
                                           min_water_px=self.min_water_px)
        is_at_coast = (
            coast_zone['water_px'] > 50 and
            coast_zone['land_ratio'] < 0.7   # Gemini: 0.7 — ловит узкие мысы
        )

        fwd_fp = analyze_footprint_zone(mm, self._inland_vec, radius=60)

        return {
            'coast_angle':    self._coast_angle,
            'inland_vec':     self._inland_vec,
            'coast_vec':      self._coast_vec,
            'fwd':            fwd,
            'is_at_coast':    is_at_coast,
            'fwd_footprint':  fwd_fp,
        }

    # ── main navigation step ─────────────────────────────────────────────
    def step(self, is_water: bool = False) -> bool:
        """
        One navigation step — hard-corridor lawnmower.

        HOMING   — read minimap, move toward coast until boundary visible.
        DIVING   — count inland steps strictly (no minimap reads).
                   At max depth: 1 shift click → RETURNING.
        RETURNING — count steps back toward coast (same count as dive).
                   At zero: 1 shift click → HOMING.

        _shift_vec is locked from _coast_vec at first coast contact and
        never changes — guarantees consistent strip direction all session.
        Walls (left + mirror) are drawn at each HOMING→DIVING transition.
        """
        if self._state == 'HOMING':
            # Gemini: is_water — самый первый приоритет, до любых других проверок
            if is_water:
                self._move_perpendicular(toward_water=False)
                self._homing_steps += 1
                return True

            info = self._read_minimap()   # angle/direction update happens here

            if info['is_at_coast']:
                fwd = info['fwd']
                if fwd['land_px'] == 0 and fwd['water_px'] > self.min_water_px:
                    self._shift_click()   # чистый океан → пропустить колонку
                    return True           # остаёмся в HOMING
                if self._footprint_enabled and self._max_footprint_overlap < 1.0:
                    fp      = info['fwd_footprint']
                    zone_px = fp.get('zone_px', 1)
                    if zone_px > 0 and fp['footprint_px'] / zone_px >= self._max_footprint_overlap:
                        self._shift_click()   # превышен порог перекрытия → пропустить
                        return True
                if not self._shift_vec_set:
                    self._shift_vec     = tuple(self._coast_vec)
                    self._shift_vec_set = True
                if self._footprint_enabled:
                    iv = self._inland_vec
                    sv = (-iv[1], iv[0])
                    self._footprint.draw_ray(iv, sv)
                    self._footprint.draw_ray(iv, sv, extra_coast_steps=2)
                    self._footprint.draw_beacon(sv, offset_coast_steps=2)   # Gemini: offset=2
                if self._prev_inland_vec is not None and self._max_pitch_delta > 0:
                    self._inland_vec = _clamp_vec(
                        self._inland_vec, self._prev_inland_vec, self._max_pitch_delta
                    )
                self._prev_inland_vec   = self._inland_vec
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                self._dive_distance     = 0.0
                # fall through to DIVING in same call

            elif self._homing_steps >= self.homing_max_steps:
                if info['fwd']['is_ocean']:
                    self._shift_click()   # Gemini fix: океан → сдвиг, не уход в воду
                    self._homing_steps = 0
                    return True
                # Land visible but max steps reached — start diving from here
                if not self._shift_vec_set:
                    self._shift_vec     = tuple(self._coast_vec)
                    self._shift_vec_set = True
                if self._footprint_enabled:
                    iv = self._inland_vec
                    sv = (-iv[1], iv[0])
                    self._footprint.draw_ray(iv, sv)
                    self._footprint.draw_ray(iv, sv, extra_coast_steps=2)
                    self._footprint.draw_beacon(sv, offset_coast_steps=2)   # маяк 2 шага вправо
                if self._prev_inland_vec is not None and self._max_pitch_delta > 0:
                    self._inland_vec = _clamp_vec(
                        self._inland_vec, self._prev_inland_vec, self._max_pitch_delta
                    )
                self._prev_inland_vec   = self._inland_vec
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                self._dive_distance     = 0.0
                # fall through to DIVING in same call

            else:
                # Gemini: гистерезис — менять направление только при 2 шагах подряд
                seaward_vec = (-self._inland_vec[0], -self._inland_vec[1])
                is_serious_ocean = (
                    info['fwd']['is_ocean'] and
                    self._peek_step(seaward_vec) is None
                )
                if is_serious_ocean:
                    self._ocean_streak += 1
                else:
                    self._ocean_streak = 0

                if self._ocean_streak >= 2:
                    self._move_perpendicular(toward_water=False)   # подтверждённый океан
                else:
                    self._move_perpendicular(toward_water=True)    # к берегу
                self._homing_steps += 1
                return True

        if self._state == 'DIVING':
            # Gemini: если бот в воде во время нырка — аварийный возврат в HOMING
            if is_water:
                self._state        = 'HOMING'
                self._inland_steps = 0
                self._homing_steps = 0
                return True
            # Safety wall: force lateral shift if stuck too long without sideways advance
            if self._force_shift_after > 0 and self._steps_since_shift >= self._force_shift_after:
                self._shift_click()
                return True

            if self._inland_steps >= self.max_inland_steps:
                self._shift_click()
                self._state             = 'RETURNING'
                # Backstop = actual physical distance dived + generous margin for diagonal visual approach
                self._return_steps      = int(math.ceil(self._dive_distance)) + 10
                self._dive_distance     = 0.0
                self._steps_since_shift = 0
                return True
            mult = self._peek_step(self._inland_vec)
            if mult is None:
                if self._inland_steps == 0:
                    # N=0: океан на первом шаге → пропустить колонку, остаться в HOMING
                    self._shift_click()
                    self._state        = 'HOMING'
                    self._inland_steps = 0
                    self._homing_steps = 0
                    return True
                # Нырнули N>0 шагов, потом океан → нормальный аборт
                self._shift_click()
                self._state             = 'RETURNING'
                self._return_steps      = int(math.ceil(self._dive_distance)) + 10
                self._dive_distance     = 0.0
                self._steps_since_shift = 0
                return True
            self._move_perpendicular(toward_water=False, multiplier=mult)
            self._inland_steps    += 1
            self._dive_distance   += mult
            return True

        if self._state == 'RETURNING':
            if self._force_shift_after > 0 and self._steps_since_shift >= self._force_shift_after:
                self._shift_click()
                return True

            # ── СТОП: проверяется ВСЕГДА, до любой навигации ──────────────
            # beacon_line ИЛИ визуальная вода в сеаворд направлении (OR)
            cap_hit  = self._return_steps <= 0
            at_coast = self._is_at_coast_now()
            if cap_hit or at_coast:
                self._shift_click()
                self._state        = 'HOMING'
                self._inland_steps = 0
                self._homing_steps = 0
                return True

            # ── НАВИГАЦИЯ: визуальный маяк если виден, иначе слепой сеаворд ──
            if self._footprint_enabled and self._footprint._beacon_cx is not None:
                mm     = self._grab_minimap()
                beacon = self._find_beacon_on_minimap(mm)
                if beacon is not None:
                    dx, dy, dist = beacon
                    step_px = float(self._pixels_per_step)
                    if dist < step_px * 0.5:
                        # Визуально в точке маяка
                        self._shift_click()
                        self._state        = 'HOMING'
                        self._inland_steps = 0
                        self._homing_steps = 0
                        return True
                    frac = min(1.0, dist / step_px)
                    # Физический клик к маяку — НЕ пишем боковой компонент в canvas
                    # Только seaward компонент записывается чтобы не было дрейфа
                    self._click_vec(dx, dy, frac, record=False)
                    seaward = (-self._inland_vec[0], -self._inland_vec[1])
                    norm = math.hypot(dx, dy)
                    if norm > 0:
                        ndx, ndy = dx / norm, dy / norm
                        sw_proj = max(0.0, ndx * seaward[0] + ndy * seaward[1])
                        self._footprint.record(sw_proj * frac * seaward[0],
                                               sw_proj * frac * seaward[1])
                    self._return_steps -= 1
                    return True

            # Слепой сеаворд (маяк не виден на миникарте)
            self._return_steps -= 1
            self._move_perpendicular(toward_water=True)
            return True

        return True


# ─────────────────────────────────────────────
# PacmanEngine — main loop
# ─────────────────────────────────────────────

class PacmanEngine:
    def __init__(
        self,
        center_x: int       = 90,
        center_y: int       = 925,
        step: int           = 13,
        dive_depth: int     = 5,
        conf: float         = 0.7,
        scan_interval: float = 0.6,
        sound_path: str     = 'Logo_exchange.wav',
        yolo_model          = None,
        move_wait: float    = 2.0,
        navigation_enabled: bool = True,
        max_inland_steps: int   = 5,
        ocean_land_ratio: float = 0.03,
        min_water_px: int       = 500,
        footprint_ttl: float    = 3600.0,   # 1 час
        force_shift_after: int  = 0,
        coast_detect_radius: int = 50,
        max_pitch_delta: float  = 15.0,
        max_footprint_overlap: float = 0.2,
        scan_dir: int = 1,                    # +1 вправо, -1 влево
        pixels_per_step: int | None = None,   # None = use step; set from nav_pps calibration
        # legacy params (ignored):
        diagonal_blind_coeff: float = 0.5,
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
            footprint_ttl=footprint_ttl,
            force_shift_after=force_shift_after,
            coast_detect_radius=coast_detect_radius,
            max_pitch_delta=max_pitch_delta,
            max_footprint_overlap=max_footprint_overlap,
            scan_dir=scan_dir,
            pixels_per_step=pixels_per_step,
        )
        self.conf               = conf
        self.scan_interval      = scan_interval
        self.yolo_model         = yolo_model
        self.sound_path         = sound_path
        self.move_wait          = move_wait
        self.navigation_enabled = navigation_enabled
        self.is_running         = False
        self.on_found_callback  = None
        self._thread: threading.Thread | None = None

    def start(self):
        self.joystick.reset()
        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False

    def _run(self):
        from mss import mss

        last_scan  = 0.0

        with mss() as sct:
            monitor = sct.monitors[1]
            screen  = np.array(sct.grab(monitor))
            frame   = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

            while self.is_running:
                # Check current position before moving
                is_water = is_water_center_screen(frame, radius=120)

                # YOLO scan — throttled by scan_interval
                now = time.time()
                if self.yolo_model is not None and (now - last_scan) >= self.scan_interval:
                    results = self.yolo_model.predict(
                        frame, conf=self.conf, imgsz=1280, verbose=False)
                    last_scan = now
                    for r in results:
                        if len(r.boxes) > 0:
                            self._on_exchange_found()
                            return

                # Navigate (skip if manual mode)
                if self.navigation_enabled:
                    self.joystick.step(is_water=is_water)
                    time.sleep(self.move_wait + random.uniform(0.1, 0.4))
                else:
                    time.sleep(self.scan_interval * 0.5)

                # Grab next frame
                screen = np.array(sct.grab(monitor))
                frame  = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

        self.is_running = False

    def _on_exchange_found(self):
        self.is_running = False
        try:
            winsound.PlaySound(self.sound_path,
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            winsound.Beep(1000, 500)
        if self.on_found_callback:
            self.on_found_callback()
