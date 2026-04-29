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
