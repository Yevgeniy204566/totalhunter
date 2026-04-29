"""
navigator_beacon.py — CoastalSnakeNavigator extension with visual beacon-guided return.

Extends CoastalSnakeNavigator with RETURNING phase split into three sub-states:
  RETURNING_BLIND  — move toward coast, no beacon scan
  RETURNING_SCAN   — canvas close enough, HSV scan active
  RETURNING_BEACON — beacon found on minimap, vector-homing to it

navigator.py is never modified.
"""
import logging
import numpy as np
import cv2

from navigator import CoastalSnakeNavigator, get_land_water_masks


class CoastalSnakeNavigatorBeacon(CoastalSnakeNavigator):
    """
    Extends CoastalSnakeNavigator with visual beacon-guided return.

    RETURNING phase split into three sub-states:
      RETURNING_BLIND  — move toward coast, no beacon scan
      RETURNING_SCAN   — canvas close enough, HSV scan active
      RETURNING_BEACON — beacon found on minimap, vector-homing to it

    navigator.py is never modified.
    """

    MINIMAP_RADIUS      = 90    # px — half of 180px snapshot
    BEACON_SHIFT_STEPS  = 2     # beacon placed this many shift-steps from dive start
    SCAN_TRIGGER_RATIO  = 1.2   # activate scan when canvas-dist < ratio * MINIMAP_RADIUS
    BEACON_LOST_MAX     = 3     # frames beacon can be missing before fallback to SCAN

    def __init__(self, *args, pixels_per_step: int = 20, **kwargs):
        super().__init__(*args, **kwargs)
        self._pixels_per_step  = pixels_per_step
        self._beacon_grid: tuple[float, float] | None = None
        self._bot_gcx: float   = 0.0   # canvas position in step-space
        self._bot_gcy: float   = 0.0
        self._beacon_lost_streak: int = 0

    def reset(self):
        super().reset()
        self._beacon_grid        = None
        self._bot_gcx            = 0.0
        self._bot_gcy            = 0.0
        self._beacon_lost_streak = 0

    def _click_vec(self, dx: float, dy: float) -> None:
        super()._click_vec(dx, dy)   # pyautogui click + footprint record
        norm = np.hypot(dx, dy)
        if norm > 0:
            self._bot_gcx += dx / norm
            self._bot_gcy += dy / norm

    def _move_perpendicular(self, toward_water: bool) -> None:
        # Zero canvas at start of each new dive (before first inland step)
        if not toward_water and self._inland_steps == 0:
            self._bot_gcx = 0.0
            self._bot_gcy = 0.0
        super()._move_perpendicular(toward_water=toward_water)

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
            logging.warning(
                "_place_dynamic_beacon: land not found in 20 iterations, using default"
            )
            bx = self.BEACON_SHIFT_STEPS * sv[0]
            by = self.BEACON_SHIFT_STEPS * sv[1]

        self._beacon_grid = (bx, by)

    def _grab_minimap(self) -> np.ndarray:
        mm = super()._grab_minimap()   # footprints overlay from parent

        if self._beacon_grid is not None:
            bx, by = self._beacon_grid
            h, w = mm.shape[:2]
            cx, cy = w // 2, h // 2
            rel_x = int((bx - self._bot_gcx) * self._pixels_per_step)
            rel_y = int((by - self._bot_gcy) * self._pixels_per_step)
            px = max(0, min(w - 1, cx + rel_x))
            py = max(0, min(h - 1, cy + rel_y))
            # BGR magenta (255, 0, 255) drawn ON TOP of footprints
            cv2.circle(mm, (px, py), 6, (255, 0, 255), -1)

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
