"""
minimap_reader.py — Minimap analysis for CoastalSnakeNavigator.

Provides:
  detect_coast_angle(minimap_bgr)  → float (radians)
  analyze_forward_zone(minimap_bgr, direction_vec, radius) → dict
  get_minimap_snapshot(center_x, center_y, size) → np.ndarray

Uses get_land_water_masks() from navigator.py for water/land pixel detection.
"""
import numpy as np
import cv2

from navigator import get_land_water_masks

# ── constants ──────────────────────────────────────────────────────────────
BOUNDARY_MIN_POINTS   = 10    # legacy constant (kept for test compat)
MIN_WATER_PX          = 500   # minimum water pixels to trigger ocean check
OCEAN_LAND_RATIO      = 0.03  # land fraction below this → open ocean
MIN_WATER_PX_CENTROID = 50    # minimum water pixels for centroid to be meaningful
CENTROID_MIN_OFFSET   = 5.0   # minimum centroid offset from centre (pixels)


# ── public API ─────────────────────────────────────────────────────────────

def detect_coast_angle(minimap_bgr: np.ndarray) -> float:
    """
    Detect the coastline angle from the centroid of ALL water pixels.

    Algorithm:
      1. Get water mask for the full minimap.
      2. Compute centroid of all water pixels relative to image centre.
      3. water_angle = atan2(row_offset, col_offset)  — direction TOWARD water.
      4. coast_angle = water_angle + π/2  — coastline is ⊥ to water direction.

    In _update_coast_angle:
      inland_vec = perpendicular to coast = AWAY from water centroid.

    Returns 0.0 if:
      - fewer than MIN_WATER_PX_CENTROID water pixels found, OR
      - centroid is within CENTROID_MIN_OFFSET pixels of centre
        (water evenly distributed = no clear coastal direction).
    """
    h, w = minimap_bgr.shape[:2]
    cy, cx = h // 2, w // 2

    _, water_mask = get_land_water_masks(minimap_bgr)
    water_mask = cv2.resize(water_mask, (w, h), interpolation=cv2.INTER_NEAREST)

    pts = np.column_stack(np.where(water_mask > 0)).astype(np.float32)

    if len(pts) < MIN_WATER_PX_CENTROID:
        return 0.0   # fallback — not enough water visible

    centroid_row = float(pts[:, 0].mean()) - cy   # positive = south (down)
    centroid_col = float(pts[:, 1].mean()) - cx   # positive = east  (right)

    mag = float(np.hypot(centroid_row, centroid_col))
    if mag < CENTROID_MIN_OFFSET:
        return 0.0   # water is symmetric around centre — no clear direction

    # Direction from minimap centre toward the water mass
    water_angle = float(np.arctan2(centroid_row, centroid_col))
    # Coastline is perpendicular to the water direction
    return water_angle + np.pi / 2


def analyze_forward_zone(
    minimap_bgr: np.ndarray,
    direction_vec: tuple[float, float],
    radius: int = 60,
    ocean_land_ratio: float = OCEAN_LAND_RATIO,
    min_water_px: int = MIN_WATER_PX,
) -> dict:
    """
    Analyse the area ahead on the minimap in the given direction.

    Builds a cone mask: pixels within `radius` px in a ±45° cone around
    `direction_vec` from the minimap centre.

    Returns:
        water_px  : int   — water pixels in cone
        land_px   : int   — land pixels in cone
        land_ratio: float — land_px / (water_px + land_px)
        is_ocean  : bool  — True if solid water with < 3% land (open ocean)
    """
    h, w = minimap_bgr.shape[:2]
    cy, cx = h // 2, w // 2

    dx, dy = float(direction_vec[0]), float(direction_vec[1])
    norm = np.hypot(dx, dy)
    if norm > 0:
        dx, dy = dx / norm, dy / norm

    # Pixel grid relative to centre
    ys, xs = np.mgrid[0:h, 0:w]
    rel_x = (xs - cx).astype(np.float32)
    rel_y = (ys - cy).astype(np.float32)

    # Projection along direction (forward distance)
    dot   = rel_x * dx + rel_y * dy
    # Perpendicular distance
    cross = rel_x * dy - rel_y * dx

    # Cone: strictly in front, ±45° opening (|cross| ≤ dot), within radius
    cone_mask = (dot > 0) & (np.abs(cross) <= dot) & (dot <= radius)

    land_mask, water_mask = get_land_water_masks(minimap_bgr)
    land_mask  = cv2.resize(land_mask,  (w, h), interpolation=cv2.INTER_NEAREST)
    water_mask = cv2.resize(water_mask, (w, h), interpolation=cv2.INTER_NEAREST)

    water_px   = int(np.sum((water_mask > 0) & cone_mask))
    land_px    = int(np.sum((land_mask  > 0) & cone_mask))
    total      = water_px + land_px + 1           # +1 avoids division by zero
    land_ratio = land_px / total

    is_ocean = (water_px > min_water_px) and (land_ratio < ocean_land_ratio)

    return {
        'water_px'  : water_px,
        'land_px'   : land_px,
        'land_ratio': land_ratio,
        'is_ocean'  : is_ocean,
    }


def analyze_footprint_zone(
    minimap_bgr: np.ndarray,
    direction_vec: tuple[float, float],
    radius: int = 60,
    min_footprint_px: int = 10,
) -> dict:
    """
    Detect red footprint pixels in a cone ahead.

    Footprints are rendered as BGR (0, 0, 255) = red.
    Red is not detected as water or land by get_land_water_masks(), so
    footprint detection is completely independent of coast/ocean analysis.

    Returns:
        footprint_px   : int  — red pixels found in cone
        has_footprint  : bool — True if footprint_px >= min_footprint_px
    """
    h, w = minimap_bgr.shape[:2]
    cy, cx = h // 2, w // 2

    dx, dy = float(direction_vec[0]), float(direction_vec[1])
    norm = np.hypot(dx, dy)
    if norm > 0:
        dx, dy = dx / norm, dy / norm

    ys, xs = np.mgrid[0:h, 0:w]
    rel_x = (xs - cx).astype(np.float32)
    rel_y = (ys - cy).astype(np.float32)

    dot   = rel_x * dx + rel_y * dy
    cross = rel_x * dy - rel_y * dx
    cone_mask = (dot > 0) & (np.abs(cross) <= dot) & (dot <= radius)

    # Red channel dominance: R >> B and R >> G
    b = minimap_bgr[:, :, 0].astype(np.float32)
    g = minimap_bgr[:, :, 1].astype(np.float32)
    r = minimap_bgr[:, :, 2].astype(np.float32)
    red_mask = (r > 150) & (r > b * 2.0) & (r > g * 2.0)

    zone_px      = int(np.sum(cone_mask))
    footprint_px = int(np.sum(red_mask & cone_mask))
    return {
        'footprint_px':  footprint_px,
        'zone_px':       zone_px,
        'has_footprint': footprint_px >= min_footprint_px,
    }


def is_on_beacon(
    minimap_bgr: np.ndarray,
    radius: int = 10,
    min_px: int = 15,
) -> bool:
    """
    True when red beacon pixels are found within `radius` px of minimap centre.

    The beacon is a coast-parallel line drawn by FootprintCanvas.draw_beacon()
    at the landing position (+1 coast step) before each dive.  When the bot
    physically stands on the beacon the stamped cell appears at the minimap
    centre (dx=0, dy=0 in render_overlay), so we check a small circle around
    the centre — not a directional cone.

    Rivers have no beacon pixels → no false stops at rivers.
    """
    h, w = minimap_bgr.shape[:2]
    cy, cx = h // 2, w // 2

    ys, xs = np.mgrid[0:h, 0:w]
    dist_sq = (xs - cx).astype(np.float32) ** 2 + (ys - cy).astype(np.float32) ** 2
    circle_mask = dist_sq <= float(radius ** 2)

    b = minimap_bgr[:, :, 0].astype(np.float32)
    g = minimap_bgr[:, :, 1].astype(np.float32)
    r = minimap_bgr[:, :, 2].astype(np.float32)
    red_mask = (r > 150) & (r > b * 2.0) & (r > g * 2.0)

    return int(np.sum(red_mask & circle_mask)) >= min_px


def get_minimap_snapshot(
    center_x: int = 90,
    center_y: int = 925,
    size: int = 180,
) -> np.ndarray:
    """
    Grab a live minimap screenshot from the game and return as BGR numpy array.
    """
    import pyautogui
    offset = size // 2
    shot = pyautogui.screenshot(region=(center_x - offset, center_y - offset, size, size))
    return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
