"""
navigator_beacon.py — CoastalSnakeNavigator extension with visual beacon-guided return.

Extends CoastalSnakeNavigator with RETURNING phase split into three sub-states:
  RETURNING_BLIND  — move toward coast, no beacon scan
  RETURNING_SCAN   — canvas close enough, HSV scan active
  RETURNING_BEACON — beacon found on minimap, vector-homing to it

navigator.py is never modified.
"""
import logging
import os
import numpy as np
import cv2

from navigator import CoastalSnakeNavigator, get_land_water_masks

# ── Логирование в файл beacon_debug.log ──────────────────────────────────
_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beacon_debug.log')
_beacon_logger = logging.getLogger('beacon')
if not _beacon_logger.handlers:
    _fh = logging.FileHandler(_log_path, encoding='utf-8')
    _fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    _beacon_logger.addHandler(_fh)
    _beacon_logger.setLevel(logging.DEBUG)


class CoastalSnakeNavigatorBeacon(CoastalSnakeNavigator):
    """
    Extends CoastalSnakeNavigator with visual beacon-guided return.

    RETURNING phase split into three sub-states:
      RETURNING_BLIND  — move toward coast, no beacon scan
      RETURNING_SCAN   — canvas close enough, HSV scan active
      RETURNING_BEACON — beacon found on minimap, vector-homing to it

    navigator.py is never modified.
    """

    MINIMAP_RADIUS     = 90   # px — half of 180px snapshot
    BEACON_SHIFT_STEPS = 2    # beacon placed this many shift-steps from dive start
    SCAN_TRIGGER_RATIO = 1.2  # activate scan when canvas-dist < ratio * MINIMAP_RADIUS

    # ЗОЛОТОЕ ПРАВИЛО: маяк рисуем МЫ — мы ОБЯЗАНЫ его найти.
    # «Маяк не найден» = БАГ, не кейс. Никаких движений к воде при потере маяка.

    def __init__(self, *args, pixels_per_step: int = 20, **kwargs):
        super().__init__(*args, **kwargs)
        self._pixels_per_step = pixels_per_step
        self._beacon_grid: tuple[float, float] | None = None
        self._bot_gcx: float  = 0.0   # canvas position in step-space
        self._bot_gcy: float  = 0.0

    def reset(self):
        super().reset()
        self._beacon_grid = None
        self._bot_gcx     = 0.0
        self._bot_gcy     = 0.0

    def _click_vec(self, dx: float, dy: float, extra_shift_px: int = 0) -> None:
        super()._click_vec(dx, dy, extra_shift_px=extra_shift_px)
        norm = np.hypot(dx, dy)
        if norm > 0:
            self._bot_gcx += dx / norm
            self._bot_gcy += dy / norm

    def _move_perpendicular(self, toward_water: bool, return_delta_px: int = 0) -> None:
        # Zero canvas at start of each new dive (before first inland step)
        if not toward_water and self._inland_steps == 0:
            self._bot_gcx = 0.0
            self._bot_gcy = 0.0
        super()._move_perpendicular(toward_water=toward_water, return_delta_px=return_delta_px)

    def _is_land_at(self, mm: np.ndarray, px: int, py: int) -> bool:
        h, w = mm.shape[:2]
        if not (0 <= px < w and 0 <= py < h):
            return False
        land_mask, _ = get_land_water_masks(mm)
        land_resized  = cv2.resize(land_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return bool(land_resized[py, px] > 0)

    def _place_dynamic_beacon(self) -> None:
        sv     = self._shift_vec
        iv     = self._inland_vec
        depth  = self._inland_steps   # bot is this many steps inland right now

        # Beacon is at coast level (0 inland) + 2 shift steps — FIXED
        bx = self.BEACON_SHIFT_STEPS * sv[0]
        by = self.BEACON_SHIFT_STEPS * sv[1]

        mm = self._grab_minimap()   # use self so tests can mock it
        h, w = mm.shape[:2]
        cx, cy = w // 2, h // 2

        found = False
        for i in range(20):
            # Convert beacon step-pos to minimap pixel relative to bot
            rel_x = (bx - depth * iv[0]) * self._pixels_per_step
            rel_y = (by - depth * iv[1]) * self._pixels_per_step
            px = int(cx + rel_x)
            py = int(cy + rel_y)
            if self._is_land_at(mm, px, py):
                found = True
                break
            # Ping-pong Y search: +5px, -5px, +10px, -10px, ...
            sign   = 1 if i % 2 == 0 else -1
            offset = (i // 2 + 1) * 5 / self._pixels_per_step
            by     = self.BEACON_SHIFT_STEPS * sv[1] + sign * offset

        if not found:
            _beacon_logger.warning(
                "_place_dynamic_beacon: land not found in 20 iterations, using default"
            )
            bx = self.BEACON_SHIFT_STEPS * sv[0]
            by = self.BEACON_SHIFT_STEPS * sv[1]

        self._beacon_grid = (bx, by)
        # Диагностика: показываем где маяк на миникарте и на суше ли он
        rel_x = int(cx + (bx - depth * iv[0]) * self._pixels_per_step)
        rel_y = int(cy + (by - depth * iv[1]) * self._pixels_per_step)
        _beacon_logger.info(
            f"BEACON_PLACE: grid=({bx:.2f},{by:.2f}) "
            f"minimap_px=({rel_x},{rel_y}) "
            f"depth={depth} pps={self._pixels_per_step} "
            f"land={found}"
        )

    def _grab_minimap(self) -> np.ndarray:
        mm = super()._grab_minimap()   # footprints overlay from parent
        h, w = mm.shape[:2]
        cx, cy = w // 2, h // 2

        # ── Двухцветная схема берег/вода ─────────────────────────────────
        # Земля → зелёный, вода → синий.
        # Overlay рисуем ДО маяка — маяк поверх всего.
        land_mask, water_mask = get_land_water_masks(mm)
        land_r  = cv2.resize(land_mask,  (w, h), interpolation=cv2.INTER_NEAREST)
        water_r = cv2.resize(water_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        overlay = mm.copy()
        overlay[land_r  > 0] = (40,  180,  40)   # BGR зелёный = суша
        overlay[water_r > 0] = (180,  60,  20)   # BGR синий   = вода
        mm = cv2.addWeighted(mm, 0.5, overlay, 0.5, 0)

        # ── Magenta маяк поверх всего ─────────────────────────────────────
        if self._beacon_grid is not None:
            bx, by = self._beacon_grid
            rel_x = int((bx - self._bot_gcx) * self._pixels_per_step)
            rel_y = int((by - self._bot_gcy) * self._pixels_per_step)
            px = max(0, min(w - 1, cx + rel_x))
            py = max(0, min(h - 1, cy + rel_y))
            cv2.circle(mm, (px, py), 8, (255, 0, 255), -1)   # magenta, чуть крупнее

        return mm

    def _find_beacon_on_minimap(
        self, mm: np.ndarray
    ) -> tuple[int, int] | None:
        """Detect magenta beacon; returns (x, y) centroid or None."""
        hsv  = cv2.cvtColor(mm, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array([140, 150, 100]),
            np.array([170, 255, 255]),
        )
        pts = np.column_stack(np.where(mask > 0))
        if len(pts) < 5:
            return None
        return (int(pts[:, 1].mean()), int(pts[:, 0].mean()))   # (x, y)

    def _canvas_dist_to_beacon(self) -> float:
        if self._beacon_grid is None:
            return float('inf')
        bx, by = self._beacon_grid
        return float(np.hypot(bx - self._bot_gcx, by - self._bot_gcy))

    # ── RETURNING sub-state logic ────────────────────────────────────────────

    def _scan_triggered(self) -> bool:
        """True when canvas distance to beacon is within SCAN_TRIGGER_RATIO * MINIMAP_RADIUS px."""
        dist_px = self._canvas_dist_to_beacon() * self._pixels_per_step
        return dist_px < self.MINIMAP_RADIUS * self.SCAN_TRIGGER_RATIO

    def _step_returning_blind(self) -> bool:
        if self._force_shift_after > 0 and self._steps_since_shift >= self._force_shift_after:
            self._shift_click()
            self._state       = 'HOMING'
            self._beacon_grid = None
            return True

        if self._return_steps <= 0:
            self._shift_click()
            self._state        = 'HOMING'
            self._inland_steps = 0
            self._homing_steps = 0
            self._beacon_grid  = None
            return True

        if self._scan_triggered():
            self._state = 'RETURNING_SCAN'
            return self._step_returning_scan()

        self._return_steps -= 1
        self._move_perpendicular(toward_water=True, return_delta_px=self.return_delta_px)
        return True

    def _step_returning_scan(self) -> bool:
        if self._force_shift_after > 0 and self._steps_since_shift >= self._force_shift_after:
            self._shift_click()
            self._state       = 'HOMING'
            self._beacon_grid = None
            return True

        if self._return_steps <= 0:
            self._shift_click()
            self._state        = 'HOMING'
            self._inland_steps = 0
            self._homing_steps = 0
            self._beacon_grid  = None
            return True

        mm         = self._grab_minimap()
        beacon_pos = self._find_beacon_on_minimap(mm)
        _beacon_logger.info(f"BEACON_SCAN: found={beacon_pos} return_steps={self._return_steps}")

        if beacon_pos is not None:
            self._state = 'RETURNING_BEACON'
            return self._step_returning_beacon()

        # Маяк не найден → стоять и сканировать следующий шаг. НЕ ДВИГАТЬСЯ.
        # Это баг: мы сами нарисовали маяк — должны найти его всегда.
        _beacon_logger.warning(
            f"BEACON_SCAN: НЕ НАЙДЕН! "
            f"beacon_grid={self._beacon_grid} "
            f"bot_gcx={self._bot_gcx:.2f} bot_gcy={self._bot_gcy:.2f} "
            f"pps={self._pixels_per_step}"
        )
        return True

    def _step_returning_beacon(self) -> bool:
        if self._force_shift_after > 0 and self._steps_since_shift >= self._force_shift_after:
            self._shift_click()
            self._state       = 'HOMING'
            self._beacon_grid = None
            return True

        if self._return_steps <= 0:
            self._shift_click()
            self._state        = 'HOMING'
            self._inland_steps = 0
            self._homing_steps = 0
            self._beacon_grid  = None
            return True

        mm         = self._grab_minimap()
        beacon_pos = self._find_beacon_on_minimap(mm)

        if beacon_pos is None:
            # Маяк не найден → назад в SCAN. НЕ ДВИГАТЬСЯ.
            _beacon_logger.warning(
                f"BEACON_HOME: маяк потерян! "
                f"beacon_grid={self._beacon_grid} "
                f"bot=({self._bot_gcx:.2f},{self._bot_gcy:.2f})"
            )
            self._state = 'RETURNING_SCAN'
            return True

        h, w = mm.shape[:2]
        px, py = beacon_pos
        dx = float(px - w // 2)
        dy = float(py - h // 2)
        dist = np.hypot(dx, dy)
        _beacon_logger.info(f"BEACON_HOME: pos=({px},{py}) dist={dist:.1f}px dx={dx:.0f} dy={dy:.0f}")

        if dist < 5.0:
            _beacon_logger.info("BEACON_HOME: ПРИЗЕМЛИЛСЯ на маяк → shift → HOMING")
            self._shift_click()
            self._state        = 'HOMING'
            self._inland_steps = 0
            self._homing_steps = 0
            self._beacon_grid  = None
            return True

        self._click_vec(dx, dy)
        self._steps_since_shift += 1
        self._return_steps -= 1
        return True

    def step(self, is_water: bool = False) -> bool:
        # Dispatch our sub-states first
        if self._state == 'RETURNING_BLIND':
            return self._step_returning_blind()
        if self._state == 'RETURNING_SCAN':
            return self._step_returning_scan()
        if self._state == 'RETURNING_BEACON':
            return self._step_returning_beacon()

        # DIVING at max depth: place beacon, then let parent do shift
        if self._state == 'DIVING' and self._inland_steps >= self.max_inland_steps:
            self._place_dynamic_beacon()
            super().step(is_water=is_water)           # parent: shift + sets RETURNING
            if self._state == 'RETURNING':
                self._state = 'RETURNING_BLIND'
            return True

        # All other states (HOMING, DIVING not at max): parent handles
        result = super().step(is_water=is_water)
        # Edge case: HOMING ocean-fallback sets state='RETURNING' directly.
        # Intercept it so beacon's sub-states handle the return.
        if self._state == 'RETURNING':
            self._state = 'RETURNING_BLIND'
        return result
