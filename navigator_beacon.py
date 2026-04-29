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
