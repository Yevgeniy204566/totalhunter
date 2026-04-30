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

def _clamp_vec(v_new: tuple, v_prev: tuple, max_delta: float) -> tuple:
    """Clamp rotation of v_new relative to v_prev to max_delta radians.
    Prevents inland_vec from flipping 180° at coast corners (π-ambiguity).
    """
    dot   = max(-1.0, min(1.0, v_prev[0]*v_new[0] + v_prev[1]*v_new[1]))
    angle = math.acos(dot)
    if angle <= max_delta:
        return v_new
    cross = v_prev[0]*v_new[1] - v_prev[1]*v_new[0]
    theta = math.copysign(max_delta, cross)
    c, s  = math.cos(theta), math.sin(theta)
    return (v_prev[0]*c - v_prev[1]*s, v_prev[0]*s + v_prev[1]*c)


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

    def __init__(self):
        self._grid  = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.float64)
        self._cx    = float(self.CENTER)
        self._cy    = float(self.CENTER)
        self._cx_i  = self.CENTER   # integer grid index (for stamping)
        self._cy_i  = self.CENTER

    def record(self, dx: float, dy: float) -> None:
        """Track position with float accumulation — avoids rounding error on diagonal steps."""
        self._cx = max(0.0, min(float(self.GRID_SIZE - 1), self._cx + dx))
        self._cy = max(0.0, min(float(self.GRID_SIZE - 1), self._cy + dy))
        self._cx_i = int(round(self._cx))
        self._cy_i = int(round(self._cy))

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
        rcx = max(0, min(self.GRID_SIZE - 1,
                         self._cx_i - coast_dx + extra_coast_steps * coast_dx))
        rcy = max(0, min(self.GRID_SIZE - 1,
                         self._cy_i - coast_dy + extra_coast_steps * coast_dy))

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

        for dy in range(-half_y, half_y + 1):
            for dx in range(-half_x, half_x + 1):
                gx = self._cx_i + dx
                gy = self._cy_i + dy
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
        self._cx   = float(self.CENTER)
        self._cy   = float(self.CENTER)
        self._cx_i = self.CENTER
        self._cy_i = self.CENTER


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
        footprint_ttl: float    = 120.0,
        footprint_enabled: bool = True,
        pixels_per_step: int    = 20,
        force_shift_after: int  = 0,   # 0 = disabled; N = force shift every N non-shift steps
        diagonal_blind_coeff: float = 0.5,  # 0=no reduction, 1=fully blind at 45°
        coast_detect_radius: int = 50,  # конус детекции берега при возврате (px на мини-карте)
        return_delta_px: int    = 0,   # pixels of rightward bias added to every RETURNING click
        max_pitch_delta: float  = 15.0, # degrees; max inland_vec rotation per dive (0 = disabled)
    ):
        self.center_x         = center_x
        self.center_y         = center_y

        sw, sh = pyautogui.size()
        aspect = sw / sh
        self.p_range_y = step
        self.p_range_x = max(1, round(step * aspect))

        self.max_inland_steps       = max_inland_steps
        self.ocean_land_ratio       = ocean_land_ratio
        self.min_water_px           = min_water_px
        self.homing_max_steps       = homing_max_steps
        self.coast_ema_alpha        = coast_ema_alpha
        self.diagonal_blind_coeff   = diagonal_blind_coeff
        self.coast_detect_radius    = coast_detect_radius
        self.return_delta_px        = return_delta_px
        self._max_pitch_delta   = math.radians(max_pitch_delta)
        self._prev_inland_vec   = None

        self._state              = 'HOMING'
        self._inland_steps       = 0
        self._homing_steps       = 0
        self._return_steps       = 0
        self._return_blind_steps = 0
        self._coast_angle        = 0.0
        self._inland_vec         = (1.0, 0.0)
        self._coast_vec          = (0.0, 1.0)
        self._angle_init         = False
        # Fixed shift direction — locked at first coast contact, never changes
        self._shift_vec     = (0.0, 1.0)
        self._shift_vec_set = False

        self._footprint_ttl     = footprint_ttl
        self._footprint_enabled = footprint_enabled
        self._pixels_per_step   = pixels_per_step
        self._footprint         = FootprintCanvas()

        self._force_shift_after = force_shift_after
        self._steps_since_shift = 0

    def reset(self):
        self._state         = 'HOMING'
        self._inland_steps  = 0
        self._homing_steps  = 0
        self._return_steps       = 0
        self._return_blind_steps = 0
        self._angle_init         = False
        self._inland_vec         = (1.0, 0.0)
        self._coast_vec          = (0.0, 1.0)
        self._coast_angle        = 0.0
        self._shift_vec          = (0.0, 1.0)
        self._shift_vec_set      = False
        self._steps_since_shift  = 0
        self._prev_inland_vec    = None
        self._footprint.reset()

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
        return mm

    def _click_vec(self, dx: float, dy: float, extra_shift_px: int = 0):
        """Click joystick in direction (dx, dy). extra_shift_px offsets the
        click in shift_vec direction (used for return_delta_px during RETURNING)."""
        norm = np.hypot(dx, dy)
        if norm == 0:
            return
        ndx, ndy = dx / norm, dy / norm
        cx = int(self.center_x + ndx * self.p_range_x)
        cy = int(self.center_y + ndy * self.p_range_y)
        if extra_shift_px > 0 and self._shift_vec_set:
            sv = self._shift_vec
            sv_n = float(np.hypot(sv[0], sv[1]))
            if sv_n > 0:
                cx += int(sv[0] / sv_n * extra_shift_px)
                cy += int(sv[1] / sv_n * extra_shift_px)
        pyautogui.click(cx, cy)
        if self._footprint_enabled:
            self._footprint.record(ndx, ndy)

    def _soft_shift(self, fraction: float) -> None:
        """
        Fractional lateral correction — pushes bot away from left wall.

        fraction=0.5 → closest, 1/6 → farthest detectable.
        Clicks at center + sv * fraction * p_range (sub-step position).
        Only fires when footprint canvas has data (no false trigger at session start).
        """
        import pyautogui as _pag
        sv = self._shift_vec if self._shift_vec_set else (-self._inland_vec[1], self._inland_vec[0])
        norm = np.hypot(sv[0], sv[1])
        if norm == 0 or fraction <= 0:
            return
        ndx, ndy = sv[0] / norm, sv[1] / norm
        x = int(self.center_x + ndx * self.p_range_x * fraction)
        y = int(self.center_y + ndy * self.p_range_y * fraction)
        _pag.click(x, y)
        if self._footprint_enabled:
            self._footprint.record(ndx * fraction, ndy * fraction)

    def _shift_click(self) -> None:
        """
        Lateral shift — uses locked _shift_vec (AP-37). Always exactly 1 click.

        Diagonal shift has a seaward Y-component: multiple clicks amplify it
        and push the bot into the ocean. 1 click keeps displacement small enough
        for the return phase to compensate.
        """
        if self._shift_vec_set:
            sv = self._shift_vec
        else:
            iv = self._inland_vec
            sv = (-iv[1], iv[0])
            self._shift_vec = sv

        self._click_vec(*sv)
        self._steps_since_shift = 0

    def _move_perpendicular(self, toward_water: bool, return_delta_px: int = 0) -> None:
        """
        ЗАПРЕТ на движение вдоль берега.
        Единственный метод, который двигает бота в HOMING-фазе.
        Всегда движется строго по ±inland_vec — только перпендикулярно берегу.

        toward_water=True  → клик в сторону воды  (-inland_vec = seaward)
        toward_water=False → клик вглубь суши      (+inland_vec = inland)

        return_delta_px: when >0, the click is physically offset by this many pixels
        in the shift_vec direction on the joystick — applies during RETURNING only.
        """
        iv = self._inland_vec
        if toward_water:
            self._click_vec(-iv[0], -iv[1], extra_shift_px=return_delta_px)
        else:
            self._click_vec(iv[0], iv[1])
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

        # Store shift direction = 90° CCW from inland_vec.
        # Locked at first real coast detection so it never drifts with EMA angle noise.
        if not self._shift_vec_set:
            iv = self._inland_vec
            self._shift_vec = (-iv[1], iv[0])


    def _validate_inland_direction(self, mm) -> None:
        """
        Ensure _inland_vec points toward land, not ocean.

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
            # Hysteresis: flip only when opposite side has ≥2× more land pixels.
            # Prevents minimap noise at the coast edge from oscillating inland_vec.
            dot = (self._inland_vec[0] * perp1[0] + self._inland_vec[1] * perp1[1])
            current_is_perp1 = dot > 0   # same hemisphere as perp1
            if current_is_perp1:
                if z2 > z1 * 2:
                    self._inland_vec = perp2
            else:
                if z1 > z2 * 2:
                    self._inland_vec = perp1


    def _is_at_coast_now(self) -> bool:
        """
        Check for water in the seaward direction using the FROZEN inland_vec.
        Does NOT update coast_angle or inland_vec — safe to call from RETURNING.
        """
        from minimap_reader import analyze_forward_zone
        mm = self._grab_minimap()
        seaward = (-self._inland_vec[0], -self._inland_vec[1])
        z = analyze_forward_zone(mm, seaward, radius=self.coast_detect_radius)
        return z['water_px'] > 50 and z['land_ratio'] < 0.5

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
        coast_zone  = analyze_forward_zone(mm, seaward_vec, radius=50)
        is_at_coast = (
            coast_zone['water_px'] > 50 and
            coast_zone['land_ratio'] < 0.5
        )

        # Footprint wall check — use locked shift direction (same as _shift_click).
        if self._shift_vec_set:
            sv_fp = self._shift_vec
        else:
            iv = self._inland_vec
            sv_fp = (-iv[1], iv[0])
        has_footprint_ahead = (
            self._footprint_enabled and
            analyze_footprint_zone(mm, sv_fp, radius=60)['has_footprint']
        )

        # Soft left-wall repulsion: measure proximity via footprint in -sv direction.
        # Returns fraction of a step to nudge right (0 = no wall nearby).
        # Fractions: 1/2 closest … 1/6 farthest. Only fires when canvas has data.
        wall_repulsion_frac = 0.0
        if self._footprint_enabled and self._shift_vec_set:
            neg_sv = (-sv_fp[0], -sv_fp[1])
            pps = self._pixels_per_step
            _LEVELS = [
                (pps * 0.5, 0.5  ),   # within 0.5 steps → push 1/2
                (pps * 1.0, 1/3  ),   # within 1 step    → push 1/3
                (pps * 2.0, 0.25 ),   # within 2 steps   → push 1/4
                (pps * 3.0, 0.2  ),   # within 3 steps   → push 1/5
                (pps * 4.0, 1/6  ),   # within 4 steps   → push 1/6
            ]
            for radius_f, frac in _LEVELS:
                fp = analyze_footprint_zone(mm, neg_sv, radius=max(5, int(radius_f)))
                if fp['has_footprint']:
                    wall_repulsion_frac = frac
                    break

        return {
            'coast_angle':         self._coast_angle,
            'inland_vec':          self._inland_vec,
            'coast_vec':           self._coast_vec,
            'fwd':                 fwd,
            'is_at_coast':         is_at_coast,
            'has_footprint_ahead': has_footprint_ahead,
            'wall_repulsion_frac': wall_repulsion_frac,
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
            info = self._read_minimap()   # angle/direction update happens here

            if info['is_at_coast']:
                # [WALL DISABLED] — footprint wall check commented out.
                # if info.get('has_footprint_ahead', False):
                #     self._shift_click()
                #     return True

                # Fallback: if detect_coast_angle never returned a real angle,
                # set shift_vec from whatever coast_vec we have now.
                if not self._shift_vec_set:
                    iv = self._inland_vec
                    self._shift_vec     = (-iv[1], iv[0])
                    self._shift_vec_set = True
                # Angular damper: clamp inland_vec rotation vs previous dive.
                # Prevents 180° flip at coast corners (PCA π-ambiguity).
                if self._prev_inland_vec is not None and self._max_pitch_delta > 0:
                    self._inland_vec = _clamp_vec(
                        self._inland_vec, self._prev_inland_vec, self._max_pitch_delta
                    )
                self._prev_inland_vec   = self._inland_vec
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                # fall through to DIVING in same call

            elif self._homing_steps >= self.homing_max_steps:
                if info['fwd']['is_ocean']:
                    # Open ocean — reverse back toward land
                    self._state        = 'RETURNING'
                    self._return_steps = self.homing_max_steps
                    self._homing_steps = 0
                    return True
                # Land visible but max steps reached — start diving from here
                if not self._shift_vec_set:
                    self._shift_vec     = tuple(self._coast_vec)
                    self._shift_vec_set = True
                if self._prev_inland_vec is not None and self._max_pitch_delta > 0:
                    self._inland_vec = _clamp_vec(
                        self._inland_vec, self._prev_inland_vec, self._max_pitch_delta
                    )
                self._prev_inland_vec   = self._inland_vec
                self._state             = 'DIVING'
                self._inland_steps      = 0
                self._homing_steps      = 0
                self._steps_since_shift = 0
                # fall through to DIVING in same call

            else:
                # Wall repulsion: blend rightward component into the click direction.
                # Wall correction disabled — use return_delta_px instead.
                if info['fwd']['is_ocean']:
                    self._move_perpendicular(toward_water=False)
                else:
                    self._move_perpendicular(toward_water=True)
                self._homing_steps += 1
                return True

        if self._state == 'DIVING':
            # Safety wall: force lateral shift if stuck too long without sideways advance
            if self._force_shift_after > 0 and self._steps_since_shift >= self._force_shift_after:
                self._shift_click()
                return True

            if self._inland_steps >= self.max_inland_steps:
                # Max depth: shift ⊥ to dive, then return.
                self._shift_click()
                self._state             = 'RETURNING'
                self._return_steps      = self.max_inland_steps + 15
                self._steps_since_shift = 0
                # Soft angle dependency: diagonal coast → shorter blind phase.
                # angle_ratio: 0.0 = cardinal, 1.0 = 45° diagonal
                vx = abs(self._inland_vec[0])
                vy = abs(self._inland_vec[1])
                mx = max(vx, vy)
                angle_ratio  = (min(vx, vy) / mx) if mx > 0 else 0.0
                blind_factor = 1.0 - angle_ratio * self.diagonal_blind_coeff
                self._return_blind_steps = max(
                    0, round((self.max_inland_steps - 3) * blind_factor)
                )
                return True
            self._move_perpendicular(toward_water=False)   # нырок вглубь суши
            self._inland_steps += 1
            return True

        if self._state == 'RETURNING':
            # Safety wall: force lateral shift if stuck too long without sideways advance
            if self._force_shift_after > 0 and self._steps_since_shift >= self._force_shift_after:
                self._shift_click()
                return True

            # Blind phase: ignore rivers deep inland, no coast detection.
            # Only the last (return_steps - blind_steps) steps use vision.
            if self._return_blind_steps > 0:
                self._return_blind_steps -= 1
                self._return_steps       -= 1
                self._move_perpendicular(toward_water=True,
                                         return_delta_px=self.return_delta_px)
                return True

            # Check for coast WITHOUT calling _read_minimap — inland_vec must
            # stay frozen so the bot returns on the exact same vector it dived.
            at_coast = self._is_at_coast_now()
            cap_hit  = self._return_steps <= 0
            if at_coast or cap_hit:
                self._shift_click()
                self._state        = 'HOMING'
                self._inland_steps = 0
                self._homing_steps = 0
                return True
            self._return_steps -= 1
            self._move_perpendicular(toward_water=True,
                                     return_delta_px=self.return_delta_px)
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
        footprint_ttl: float    = 120.0,
        force_shift_after: int  = 0,
        diagonal_blind_coeff: float = 0.5,
        coast_detect_radius: int = 50,
        return_delta_px: int    = 0,
        max_pitch_delta: float  = 15.0,
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
            footprint_ttl=footprint_ttl,
            force_shift_after=force_shift_after,
            diagonal_blind_coeff=diagonal_blind_coeff,
            coast_detect_radius=coast_detect_radius,
            return_delta_px=return_delta_px,
            max_pitch_delta=max_pitch_delta,
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
