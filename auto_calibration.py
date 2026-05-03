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

# Point B uses a taller rectangle — browsers can push the resource bar down 200+ px
_SEARCH_B_X = 200   # horizontal half-width
_SEARCH_B_Y_UP = 50    # pixels to search ABOVE scaled REF_B
_SEARCH_B_Y_DOWN = 350  # pixels to search BELOW scaled REF_B


def _grab_region(
    cx: int, cy: int,
    radius: int = _SEARCH_RADIUS,
    radius_x: int | None = None,
    radius_y_up: int | None = None,
    radius_y_down: int | None = None,
) -> tuple[np.ndarray, int, int]:
    """
    Capture screen region centered on (cx, cy).
    If radius_x/radius_y_up/radius_y_down provided, uses rectangular region.
    Returns (BGR ndarray, x1, y1).
    """
    rx = radius_x if radius_x is not None else radius
    ry_up = radius_y_up if radius_y_up is not None else radius
    ry_down = radius_y_down if radius_y_down is not None else radius
    x1 = max(0, cx - rx)
    y1 = max(0, cy - ry_up)
    x2 = cx + rx
    y2 = cy + ry_down
    with _mss() as sct:
        mon = {"left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1}
        shot = sct.grab(mon)
    return np.array(shot)[:, :, :3], x1, y1


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
    # ── Point A — white rectangle of joystick ────────────────────────────
    a_cx, a_cy = scale_ref(REF_A, screen_w, screen_h)
    img_a, ax1, ay1 = _grab_region(a_cx, a_cy)
    found_a = detect_point_a_in_region(img_a)
    if found_a is not None:
        point_a = (ax1 + found_a[0], ay1 + found_a[1])
    else:
        point_a = (a_cx, a_cy)

    # ── Point B — rectangular search (tall to handle browser chrome offset) ──
    b_cx, b_cy = scale_ref(REF_B, screen_w, screen_h)
    baseline, bx1, by1 = _grab_region(
        b_cx, b_cy,
        radius_x=_SEARCH_B_X,
        radius_y_up=_SEARCH_B_Y_UP,
        radius_y_down=_SEARCH_B_Y_DOWN,
    )
    pyautogui.moveTo(b_cx, b_cy, duration=0.15)
    time.sleep(_HOVER_WAIT)
    hover_img, _, _ = _grab_region(
        b_cx, b_cy,
        radius_x=_SEARCH_B_X,
        radius_y_up=_SEARCH_B_Y_UP,
        radius_y_down=_SEARCH_B_Y_DOWN,
    )
    found_b = detect_point_b_from_diff(baseline, hover_img)
    if found_b is not None:
        point_b = (bx1 + found_b[0], by1 + found_b[1])
    else:
        point_b = (b_cx, b_cy)

    return point_a, point_b
