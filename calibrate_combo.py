"""
calibrate_combo.py -- Auto-calibration for CombinerEngine grid constants.

Detection algorithm (verified on combination_1..4.png):
  1. Autocorrelation on Sobel gradient projections -> slot period (px)
  2. Sobel X peak scan -> vertical separator positions -> GRID_X, SLOT_W
  3. Row brightness jump -> GRID_Y
  4. Count columns / rows from image geometry
  5. NUM_ROI = top-right corner of card (number badge position)
  6. SCROLL_PT / HEADER_PT derived from grid bounds

Usage:
  python calibrate_combo.py --from-screenshot combination_1.png [--patch]
  python calibrate_combo.py --from-screenshot c1.png c2.png c3.png [--patch]
  python calibrate_combo.py --live [--patch]
"""

import argparse
import sys
import os
import re

try:
    import cv2
    import numpy as np
except ImportError:
    print("ERROR: cv2/numpy not found.  pip install opencv-python numpy")
    sys.exit(1)


COMBINER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "combiner.py")


# ══════════════════════════════════════════════════════════════
#  DETECTION HELPERS
# ══════════════════════════════════════════════════════════════

def _autocorr_period(signal: np.ndarray, min_p: int = 60, max_p: int = 130) -> int:
    """Return dominant period of signal using autocorrelation."""
    n = len(signal)
    norm = signal - signal.mean()
    corr = np.correlate(norm, norm, mode='full')[n - 1:]
    corr /= (corr[0] + 1e-9)
    best_lag, best_val = min_p, -1.0
    for lag in range(min_p, min(max_p + 1, n // 2)):
        if corr[lag] > best_val:
            best_val = corr[lag]
            best_lag = lag
    return best_lag


def _find_separators(edge_proj: np.ndarray, period: int,
                     threshold_ratio: float = 1.3,
                     min_gap: int = None) -> list:
    """
    Find positions of card-boundary peaks in a 1-D edge projection.
    Returns sorted list of peak positions.
    """
    if min_gap is None:
        min_gap = int(period * 0.7)

    threshold = edge_proj.mean() * threshold_ratio
    peaks = []
    prev = -min_gap
    for i in range(len(edge_proj)):
        if edge_proj[i] > threshold and i - prev >= min_gap:
            lo = max(0, i - 5)
            hi = min(len(edge_proj), i + 6)
            if edge_proj[i] == edge_proj[lo:hi].max():
                peaks.append(i)
                prev = i
    return peaks


def _find_grid_top(gray: np.ndarray, search_range: tuple = (0, 200)) -> int:
    """
    Find the Y coordinate where the card grid begins.
    Uses a jump in row mean brightness (dialog header -> bright card area).
    """
    row_mean = gray.mean(axis=1)
    y0, y1 = search_range
    for y in range(y1, y0 - 1, -1):
        if row_mean[y] < 60:   # dark row = border before grid
            return y + 1
    # Fallback: look for a big brightness jump
    for y in range(y0, y1):
        if row_mean[y] > 150 and (y == 0 or row_mean[y - 1] < 80):
            return y
    return y0


# ══════════════════════════════════════════════════════════════
#  MAIN DETECTION
# ══════════════════════════════════════════════════════════════

FULLSCREEN_THRESHOLD = 1400   # width above this → treat as full 1920×1080 screen

# Search window inside full screen: combining popup is always roughly centred.
# These margins leave a 900×670 crop that always contains the window.
FS_CROP_X1, FS_CROP_Y1 = 490,  30
FS_CROP_X2, FS_CROP_Y2 = 1450, 700


def find_grid(img: np.ndarray, debug_path: str = "combo_grid_debug.png") -> dict:
    """
    Detect combining window grid in screenshot.
    Returns dict with all combiner.py constants.

    For a full 1920×1080 screenshot the function first crops the centre region
    where Total Battle always places the combining popup, runs detection on the
    crop, then adds the crop offset so every constant is an absolute screen
    coordinate.  Pass a pre-cropped screenshot and the raw pixel values are
    returned as-is.
    """
    h, w = img.shape[:2]
    print(f"  Image: {w} x {h}")

    # Detect full-screen and crop to the centre where the popup lives
    crop_offset_x = 0
    crop_offset_y = 0
    if w >= FULLSCREEN_THRESHOLD:
        x1, y1 = FS_CROP_X1, FS_CROP_Y1
        x2, y2 = min(FS_CROP_X2, w), min(FS_CROP_Y2, h)
        img = img[y1:y2, x1:x2]
        crop_offset_x, crop_offset_y = x1, y1
        h, w = img.shape[:2]
        print(f"  Full-screen detected -> cropped to [{x1}:{x2}, {y1}:{y2}]  ({w}x{h})")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    debug = img.copy()

    # ── 1. Slot period from autocorrelation ───────────────────
    sobelx = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    col_edge = np.abs(sobelx).mean(axis=0)
    row_edge = np.abs(sobely).mean(axis=1)

    period_x = _autocorr_period(col_edge, 60, 130)
    period_y = _autocorr_period(row_edge, 60, 130)
    slot_w = period_x
    slot_h = period_y
    print(f"  Slot period: W={slot_w}  H={slot_h}")

    # ── 2. Vertical separator positions -> grid left edge ─────
    sep_x = _find_separators(col_edge, slot_w, threshold_ratio=1.3)
    print(f"  X separators: {sep_x}")

    # First separator is left edge of first card
    grid_x = sep_x[0] if sep_x else 0
    n_cols = len(sep_x)   # number of separator lines = number of cells
    # Verify: last sep + slot_w should not exceed image width by much
    # If it does, the last sep is the right border of the last card, not a separator
    if sep_x and sep_x[-1] + slot_w > w + slot_w * 0.3:
        n_cols = len(sep_x) - 1

    print(f"  COMBO_GRID_X = {grid_x}   COMBO_COLS = {n_cols}")

    # ── 3. Grid top edge -> GRID_Y ────────────────────────────
    # Find the dark-to-bright transition near the top of the image
    grid_y = _find_grid_top(gray, search_range=(0, min(150, h // 3)))
    print(f"  COMBO_GRID_Y = {grid_y}")

    # ── 4. Row count ──────────────────────────────────────────
    # Count how many full slots fit below grid_y
    usable_height = h - grid_y
    n_rows = usable_height // slot_h
    print(f"  COMBO_ROWS_VISIBLE = {n_rows}")

    # ── 5. NUM_ROI: number badge is top-right corner of card ──
    # Verified empirically: badge at x_off=50..87, y_off=0..30
    num_x_off = int(slot_w * 0.57)  # ~57% from left = right portion
    num_y_off = 0
    num_w     = slot_w - num_x_off
    num_h     = int(slot_h * 0.35)
    num_roi   = (num_x_off, num_y_off, num_w, num_h)
    print(f"  NUM_ROI = {num_roi}")

    # ── 6. Scroll / header points ─────────────────────────────
    scroll_x = grid_x + (n_cols * slot_w) // 2
    scroll_y = grid_y + (n_rows * slot_h) // 2
    header_x = w // 2
    header_y = grid_y // 2   # middle of title bar
    scroll_pt = (scroll_x, scroll_y)
    header_pt = (header_x, header_y)
    print(f"  COMBO_SCROLL_PT = {scroll_pt}  (crop-relative)")
    print(f"  COMBO_HEADER_PT = {header_pt}  (crop-relative)")

    # ── 7. Draw debug grid ────────────────────────────────────
    for ri in range(n_rows):
        for ci in range(n_cols):
            rx = grid_x + ci * slot_w
            ry = grid_y + ri * slot_h
            # Card rectangle
            cv2.rectangle(debug, (rx, ry), (rx + slot_w, ry + slot_h), (0, 0, 255), 2)
            # Number badge region
            nx = rx + num_x_off
            ny = ry + num_y_off
            cv2.rectangle(debug, (nx, ny), (nx + num_w, ny + num_h), (0, 255, 255), 1)
            # Label
            cv2.putText(debug, f"{ri},{ci}", (rx + 2, ry + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 0), 1)

    # Grid origin marker
    cv2.circle(debug, (grid_x, grid_y), 6, (0, 255, 0), -1)
    # Scroll point
    cv2.circle(debug, scroll_pt, 5, (255, 0, 255), -1)
    # Header point
    cv2.circle(debug, header_pt, 5, (255, 128, 0), -1)

    cv2.imwrite(debug_path, debug)
    print(f"  Debug: {debug_path}")

    # ── 8. Add crop offset for full-screen coordinates ────────
    abs_grid_x    = grid_x    + crop_offset_x
    abs_grid_y    = grid_y    + crop_offset_y
    abs_scroll_pt = (scroll_x + crop_offset_x, scroll_y + crop_offset_y)
    abs_header_pt = (header_x + crop_offset_x, header_y + crop_offset_y)

    if crop_offset_x or crop_offset_y:
        print(f"  After full-screen offset (+{crop_offset_x}, +{crop_offset_y}):")
        print(f"    COMBO_GRID_X = {abs_grid_x}   COMBO_GRID_Y = {abs_grid_y}")
        print(f"    COMBO_SCROLL_PT = {abs_scroll_pt}")
        print(f"    COMBO_HEADER_PT = {abs_header_pt}")

    return {
        "COMBO_GRID_X":       abs_grid_x,
        "COMBO_GRID_Y":       abs_grid_y,
        "COMBO_SLOT_W":       slot_w,
        "COMBO_SLOT_H":       slot_h,
        "COMBO_COLS":         n_cols,
        "COMBO_ROWS_VISIBLE": n_rows,
        "NUM_ROI":            num_roi,
        "COMBO_SCROLL_PT":    abs_scroll_pt,
        "COMBO_HEADER_PT":    abs_header_pt,
    }


# ══════════════════════════════════════════════════════════════
#  CONSENSUS
# ══════════════════════════════════════════════════════════════

def consensus(results: list) -> dict:
    """Median-average numeric constants over multiple detections."""
    if len(results) == 1:
        return results[0]

    def med_int(key):
        return int(round(np.median([r[key] for r in results])))

    def med_tuple2(key):
        return (int(round(np.median([r[key][0] for r in results]))),
                int(round(np.median([r[key][1] for r in results]))))

    def med_tuple4(key):
        return tuple(int(round(np.median([r[key][i] for r in results])))
                     for i in range(4))

    return {
        "COMBO_GRID_X":       med_int("COMBO_GRID_X"),
        "COMBO_GRID_Y":       med_int("COMBO_GRID_Y"),
        "COMBO_SLOT_W":       med_int("COMBO_SLOT_W"),
        "COMBO_SLOT_H":       med_int("COMBO_SLOT_H"),
        "COMBO_COLS":         med_int("COMBO_COLS"),
        "COMBO_ROWS_VISIBLE": med_int("COMBO_ROWS_VISIBLE"),
        "NUM_ROI":            med_tuple4("NUM_ROI"),
        "COMBO_SCROLL_PT":    med_tuple2("COMBO_SCROLL_PT"),
        "COMBO_HEADER_PT":    med_tuple2("COMBO_HEADER_PT"),
    }


# ══════════════════════════════════════════════════════════════
#  PATCH combiner.py
# ══════════════════════════════════════════════════════════════

def patch_combiner(constants: dict) -> bool:
    if not os.path.exists(COMBINER_PATH):
        print(f"ERROR: combiner.py not found at {COMBINER_PATH}")
        return False

    with open(COMBINER_PATH, "r", encoding="utf-8") as f:
        src = f.read()

    nr = constants["NUM_ROI"]
    sc = constants["COMBO_SCROLL_PT"]
    hd = constants["COMBO_HEADER_PT"]

    patterns = {
        r"(COMBO_GRID_X\s*=\s*)\d+":             str(constants["COMBO_GRID_X"]),
        r"(COMBO_GRID_Y\s*=\s*)\d+":             str(constants["COMBO_GRID_Y"]),
        r"(COMBO_SLOT_W\s*=\s*)\d+":             str(constants["COMBO_SLOT_W"]),
        r"(COMBO_SLOT_H\s*=\s*)\d+":             str(constants["COMBO_SLOT_H"]),
        r"(COMBO_COLS\s*=\s*)\d+":               str(constants["COMBO_COLS"]),
        r"(COMBO_ROWS_VISIBLE\s*=\s*)\d+":       str(constants["COMBO_ROWS_VISIBLE"]),
        r"(NUM_ROI\s*=\s*)\([^)]+\)":            f"({nr[0]}, {nr[1]}, {nr[2]}, {nr[3]})",
        r"(COMBO_SCROLL_PT\s*=\s*)\([^)]+\)":    f"({sc[0]}, {sc[1]})",
        r"(COMBO_HEADER_PT\s*=\s*)\([^)]+\)":    f"({hd[0]}, {hd[1]})",
    }

    new_src = src
    changed = 0
    for pat, val in patterns.items():
        def _repl(m, v=val):
            return m.group(1) + v
        new_src2 = re.sub(pat, _repl, new_src)
        if new_src2 != new_src:
            changed += 1
        new_src = new_src2

    if changed == 0:
        print("  WARNING: no patterns matched — nothing patched")
        return False

    with open(COMBINER_PATH, "w", encoding="utf-8") as f:
        f.write(new_src)

    print(f"  Patched {changed} constants into {COMBINER_PATH}")
    return True


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BattleBot combining-window grid calibration"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--from-screenshot", metavar="FILE", nargs="+",
        help="Analyze one or more PNG screenshots"
    )
    group.add_argument(
        "--live", action="store_true",
        help="Capture live screenshot with MSS then analyze"
    )
    parser.add_argument(
        "--patch", action="store_true",
        help="Patch detected constants into combiner.py"
    )
    parser.add_argument(
        "--debug-out", default="combo_grid_debug.png", metavar="FILE",
        help="Output path for debug image (default: combo_grid_debug.png)"
    )
    parser.add_argument(
        "--delay", type=int, default=5, metavar="SEC",
        help="Seconds to wait before screenshot (default: 5)"
    )
    args = parser.parse_args()

    results = []

    if args.live:
        try:
            import mss, time as _time
        except ImportError:
            print("ERROR: mss not installed.  pip install mss")
            sys.exit(1)
        print(f"Switching to game in {args.delay} seconds — open the Combining window NOW!")
        for i in range(args.delay, 0, -1):
            print(f"  {i}...", end="\r", flush=True)
            _time.sleep(1)
        print("Taking screenshot!          ")
        with mss.mss() as sct:
            mon = sct.monitors[1]
            raw = sct.grab(mon)
            img = np.array(raw)[:, :, :3]
        print("Analyzing...")
        r = find_grid(img, args.debug_out)
        if r:
            results.append(r)
    else:
        for i, fpath in enumerate(args.from_screenshot):
            fpath = os.path.abspath(fpath)
            print(f"\n[{i+1}/{len(args.from_screenshot)}] {fpath}")
            img = cv2.imread(fpath)
            if img is None:
                print(f"  ERROR: cannot load {fpath}")
                continue
            dbg = args.debug_out if i == 0 else args.debug_out.replace(".png", f"_{i+1}.png")
            r = find_grid(img, dbg)
            if r:
                results.append(r)

    if not results:
        print("\nERROR: detection failed on all inputs")
        sys.exit(1)

    final = consensus(results)

    print("\n" + "=" * 58)
    print("  CALIBRATED CONSTANTS")
    print("=" * 58)
    print(f"  COMBO_GRID_X       = {final['COMBO_GRID_X']}")
    print(f"  COMBO_GRID_Y       = {final['COMBO_GRID_Y']}")
    print(f"  COMBO_SLOT_W       = {final['COMBO_SLOT_W']}")
    print(f"  COMBO_SLOT_H       = {final['COMBO_SLOT_H']}")
    print(f"  COMBO_COLS         = {final['COMBO_COLS']}")
    print(f"  COMBO_ROWS_VISIBLE = {final['COMBO_ROWS_VISIBLE']}")
    print(f"  NUM_ROI            = {final['NUM_ROI']}")
    print(f"  COMBO_SCROLL_PT    = {final['COMBO_SCROLL_PT']}")
    print(f"  COMBO_HEADER_PT    = {final['COMBO_HEADER_PT']}")
    print("=" * 58)

    if args.patch:
        print()
        ok = patch_combiner(final)
        if ok:
            print("  combiner.py patched successfully.")
        else:
            print("  PATCH FAILED.")
            sys.exit(1)
    else:
        print("\n  (Pass --patch to update combiner.py)")


if __name__ == "__main__":
    main()
