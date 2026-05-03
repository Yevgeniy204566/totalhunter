import time
import numpy as np
import cv2
import pyautogui
from mss import mss as _mss

from coord_manager import REF_A, REF_B

_SEARCH_RADIUS = 150
_DIFF_THRESHOLD = 30
_DIFF_MIN_PX = 100
_HOVER_WAIT = 0.4
_CONTOUR_MIN_AREA = 500


def _grab_region(cx: int, cy: int, radius: int = _SEARCH_RADIUS) -> np.ndarray:
    """Capture a square region of the screen centered on (cx, cy). Returns BGR ndarray."""
    x1 = max(0, cx - radius)
    y1 = max(0, cy - radius)
    with _mss() as sct:
        mon = {"left": x1, "top": y1, "width": radius * 2, "height": radius * 2}
        shot = sct.grab(mon)
    return np.array(shot)[:, :, :3]


def scale_ref(ref: tuple[int, int], screen_w: int, screen_h: int) -> tuple[int, int]:
    """Scale a reference coordinate from 1920x1080 to actual screen resolution."""
    return (int(ref[0] * screen_w / 1920), int(ref[1] * screen_h / 1080))


def detect_point_a_in_region(img: np.ndarray) -> tuple[int, int] | None:
    """
    Find center of white rectangular contour in img (BGR).
    Returns (x, y) in image coordinates, or None if not found.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
        if cv2.contourArea(cnt) < _CONTOUR_MIN_AREA:
            break
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(cnt)
            return (x + w // 2, y + h // 2)
    return None


def detect_point_b_from_diff(
    baseline: np.ndarray, hover: np.ndarray
) -> tuple[int, int] | None:
    """
    Find center of newly appeared pixels (the game's + crosshair on silver hover).
    Returns (x, y) in image coordinates, or None if nothing significant appeared.
    """
    diff = cv2.absdiff(baseline, hover)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, _DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    if cv2.countNonZero(mask) < _DIFF_MIN_PX:
        return None
    pts = cv2.findNonZero(mask)
    x, y, w, h = cv2.boundingRect(pts)
    return (x + w // 2, y + h // 2)


def auto_detect_points(
    screen_w: int, screen_h: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Auto-detect Point A (minimap joystick white rect) and Point B (silver + crosshair).
    Always returns coordinates: detected position or scaled REF as fallback.
    """
    r = _SEARCH_RADIUS

    # ── Point A — white rectangle of joystick ────────────────────────────
    a_cx, a_cy = scale_ref(REF_A, screen_w, screen_h)
    img_a = _grab_region(a_cx, a_cy)
    found_a = detect_point_a_in_region(img_a)
    if found_a is not None:
        point_a = (a_cx - r + found_a[0], a_cy - r + found_a[1])
    else:
        point_a = (a_cx, a_cy)

    # ── Point B — hover-diff yellow-green crosshair ───────────────────────
    b_cx, b_cy = scale_ref(REF_B, screen_w, screen_h)
    baseline = _grab_region(b_cx, b_cy)
    pyautogui.moveTo(b_cx, b_cy, duration=0.15)
    time.sleep(_HOVER_WAIT)
    hover_img = _grab_region(b_cx, b_cy)
    found_b = detect_point_b_from_diff(baseline, hover_img)
    if found_b is not None:
        point_b = (b_cx - r + found_b[0], b_cy - r + found_b[1])
    else:
        point_b = (b_cx, b_cy)

    return point_a, point_b
