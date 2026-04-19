"""
button_finder.py — Finds UI buttons by color (HSV) in a screen region.
Language-independent: matches button color/shape, not text.

Usage:
    from button_finder import find_colored_button
    pos = find_colored_button((900, 85, 500, 60), color='purple', pick='largest')
    # pos = (cx, cy) absolute screen coords, or None

Demo:
    python button_finder.py
    (switch to game window first — takes screenshot after 2s)
"""
import numpy as np
import cv2

try:
    import mss as _mss
    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False

# ── HSV colour ranges ──────────────────────────────────────────────────────
# Calibrated from targets_2/ screenshots (Total Battle game buttons).
# OpenCV HSV: H 0-179, S 0-255, V 0-255.
# Green buttons  ≈ H 35-85  (dark game green with gold border)
# Purple «Ускорить» ≈ H 125-160 (violet/magenta on Carter bar)
HSV_RANGES: dict[str, tuple[tuple, tuple]] = {
    'green':  ((35, 40, 40),  (85, 255, 200)),
    'purple': ((125, 50, 50), (160, 255, 255)),
}

MIN_AREA = 800   # px² — ignore specks smaller than this


def _apply_color_mask(img_bgr: np.ndarray, color: str) -> np.ndarray:
    """
    Apply HSV color mask to BGR image.
    Returns binary mask (uint8). Returns all-zeros for unknown color.
    """
    if color not in HSV_RANGES:
        return np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    lo, hi = HSV_RANGES[color]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8))


def _pick_contour(
    contours: list,
    pick: str,
    region_x: int,
    region_y: int,
) -> tuple[int, int] | None:
    """
    Filter contours by size/shape, pick by rule, return absolute (cx, cy).
    pick: 'rightmost' | 'leftmost' | 'topmost' | 'largest'
    """
    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if w <= h:               # buttons must be wider than tall
            continue
        cx = region_x + x + w // 2
        cy = region_y + y + h // 2
        candidates.append((cx, cy, area))

    if not candidates:
        return None

    if pick == 'rightmost':
        return max(candidates, key=lambda c: c[0])[:2]
    if pick == 'leftmost':
        return min(candidates, key=lambda c: c[0])[:2]
    if pick == 'topmost':
        return min(candidates, key=lambda c: c[1])[:2]
    # default: largest
    return max(candidates, key=lambda c: c[2])[:2]


def _screenshot_region(region: tuple[int, int, int, int]) -> np.ndarray:
    """Grab screen region (x, y, w, h). Returns BGR numpy array."""
    x, y, w, h = region
    with _mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        raw = sct.grab(monitor)
    img = np.array(raw)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def find_colored_button(
    region: tuple[int, int, int, int],
    color: str = 'green',
    pick: str = 'largest',
) -> tuple[int, int] | None:
    """
    Find a button in a screen region by color.

    Args:
        region: (x, y, w, h) absolute screen coordinates
        color:  'green' or 'purple'
        pick:   'rightmost' | 'leftmost' | 'topmost' | 'largest'

    Returns:
        (cx, cy) absolute screen coordinates of button centre, or None.
    """
    try:
        img = _screenshot_region(region)
        mask = _apply_color_mask(img, color)
        # Close small gaps in the button area
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return _pick_contour(contours, pick, region[0], region[1])
    except Exception:
        return None


# ── Demo CLI ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    """
    python button_finder.py
    Takes a screenshot and draws found buttons for visual calibration.
    Saves result to button_finder_demo.png — open it to verify regions/detections.
    """
    import time

    print("Скриншот через 2 секунды — переключись на окно игры...")
    time.sleep(2)

    with _mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
    full = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR)

    # (label, ref_region 1920×1080, color, pick)
    searches = [
        ("Study/Исследовать", (850, 720, 450, 120), 'green',  'rightmost'),
        ("Open/Открыть",      (750, 720, 350, 120), 'green',  'leftmost'),
        ("Accelerate/Ускорить",(900, 85,  500,  60), 'purple', 'largest'),
        ("Use/Использовать",  (900, 380, 450, 250), 'green',  'topmost'),
    ]

    from coord_manager import coord_manager as _cm; scale_region = _cm.to_region
    colour_map = {'green': (0, 200, 0), 'purple': (200, 0, 200)}

    for label, ref_region, color, pick in searches:
        region = scale_region(*ref_region)
        pos = find_colored_button(region, color, pick)
        rx, ry, rw, rh = region
        # Draw search region in yellow
        cv2.rectangle(full, (rx, ry), (rx + rw, ry + rh), (0, 200, 200), 2)
        if pos:
            cx, cy = pos
            c = colour_map[color]
            cv2.circle(full, (cx, cy), 14, c, -1)
            cv2.putText(full, label, (cx - 20, cy - 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, 2)
            print(f"  {label}: найдено ({cx}, {cy})")
        else:
            print(f"  {label}: НЕ НАЙДЕНО")

    out = "button_finder_demo.png"
    cv2.imwrite(out, full)
    print(f"\nСохранено: {out}")
    print("Жёлтые прямоугольники = зоны поиска")
    print("Цветные круги = найденные кнопки")
