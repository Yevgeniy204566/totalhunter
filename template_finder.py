"""
template_finder.py — Find UI elements by template matching (cv2).

Works on any window size/position/platform (browser, standalone client).
Templates are in targets_2/ folder.

Usage:
    from template_finder import find_at_ref, find_in_screen_region

    # Search around a known reference coordinate (1920×1080 space)
    pos = find_at_ref('transition.png', ref_cx=1208, ref_cy=500, rw=350, rh=80)

    # Search in an already-computed screen region
    pos = find_in_screen_region('transition.png', screen_region=(1050, 470, 350, 80))
"""

import os
import numpy as np
import cv2

try:
    import mss as _mss
    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False

try:
    from coord_manager import coord_manager as _cm
    scale_region = _cm.to_region
    _SCALER_AVAILABLE = True
except ImportError:
    _SCALER_AVAILABLE = False

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_DIR  = os.path.join(_SCRIPT_DIR, 'targets_2')

# Scale steps for multi-scale matching.
# Covers window sizes from 70 % to 130 % of the reference 1920×1080.
_SCALES = [0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30]


def _grab_region(region: tuple) -> np.ndarray:
    """Capture (x, y, w, h) screen region → BGR numpy array."""
    x, y, w, h = region
    with _mss.mss() as sct:
        raw = sct.grab({"left": x, "top": y, "width": w, "height": h})
    img = np.array(raw)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def _load_template(name: str) -> np.ndarray | None:
    """Load template from targets_2/ by filename or absolute path."""
    path = name if os.path.isabs(name) else os.path.join(TARGETS_DIR, name)
    tmpl = cv2.imread(path)
    return tmpl  # None if not found


def _match(img_bgr: np.ndarray, tmpl_bgr: np.ndarray,
           threshold: float, offset_x: int, offset_y: int
           ) -> tuple[int, int] | None:
    """
    Multi-scale template matching.
    Returns absolute screen (cx, cy) of best match or None.
    """
    th, tw = tmpl_bgr.shape[:2]
    ih, iw = img_bgr.shape[:2]

    best_val  = -1.0
    best_loc  = None
    best_tw   = tw
    best_th   = th

    for scale in _SCALES:
        stw = max(1, int(tw * scale))
        sth = max(1, int(th * scale))
        if stw > iw or sth > ih:
            continue
        resized = cv2.resize(tmpl_bgr, (stw, sth), interpolation=cv2.INTER_AREA)
        result  = cv2.matchTemplate(img_bgr, resized, cv2.TM_CCOEFF_NORMED)
        _, val, _, loc = cv2.minMaxLoc(result)
        if val > best_val:
            best_val = val
            best_loc = loc
            best_tw  = stw
            best_th  = sth

    if best_val < threshold or best_loc is None:
        return None

    cx = offset_x + best_loc[0] + best_tw // 2
    cy = offset_y + best_loc[1] + best_th // 2
    return (cx, cy)


def find_in_screen_region(
    template_name: str,
    screen_region: tuple[int, int, int, int],
    threshold: float = 0.75,
) -> tuple[int, int] | None:
    """
    Find template inside an already-computed screen region.

    Args:
        template_name: filename in targets_2/ (e.g. 'transition.png')
        screen_region: (x, y, w, h) in actual screen pixels
        threshold:     match confidence 0–1

    Returns:
        (cx, cy) absolute screen coords, or None.
    """
    tmpl = _load_template(template_name)
    if tmpl is None:
        return None
    x, y, w, h = screen_region
    if w <= 0 or h <= 0:
        return None
    img = _grab_region(screen_region)
    return _match(img, tmpl, threshold, x, y)


def find_at_ref(
    template_name: str,
    ref_cx: int,
    ref_cy: int,
    rw: int = 300,
    rh: int = 300,
    threshold: float = 0.75,
) -> tuple[int, int] | None:
    """
    Find template in a region centred on a 1920×1080 reference coordinate.
    Region is automatically scaled to the actual game window size/position.

    Args:
        template_name: filename in targets_2/
        ref_cx, ref_cy: centre of search area in 1920×1080 reference pixels
        rw, rh:        search area size in reference pixels (default 300×300)
        threshold:     match confidence 0–1

    Returns:
        (cx, cy) absolute screen coords, or None.
    """
    ref_x = ref_cx - rw // 2
    ref_y = ref_cy - rh // 2

    if _SCALER_AVAILABLE:
        screen_region = scale_region(ref_x, ref_y, rw, rh)
    else:
        screen_region = (ref_x, ref_y, rw, rh)

    return find_in_screen_region(template_name, screen_region, threshold)
