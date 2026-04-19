# Button Finder — Design Spec
**Date:** 2026-04-06  
**Status:** Approved

## Problem

`crypt_hunter.py` uses hardcoded pixel coordinates calibrated for 1920×1080 + Windows client + Russian language. Other resolutions, browser client, or other languages shift button positions, causing misclicks.

## Solution: Color + Region Detection

No new neural network. Two new modules:

1. **`window_scaler.py`** — finds the game window, computes scale vs 1920×1080
2. **`button_finder.py`** — finds buttons by color (HSV) within a search region

Templates in `targets_2/` are used only for HSV calibration reference, not for matching.

## Button Palette

| Button | Color | Pick rule | Dialog |
|--------|-------|-----------|--------|
| «Перейти» | Green | rightmost | Watchtower menu list |
| «Исследовать» | Green | rightmost | Crypt action dialog (2 green buttons) |
| «Открыть» | Green | leftmost | Crypt action dialog (R-type only) |
| «Ускорить» | **Purple** | largest | Carter march bar (top of screen) |
| «Использовать» | Green | topmost | Speed-up dialog (2 green buttons) |

## `window_scaler.py`

```
get_game_rect() → Rect(left, top, width, height) | None
    Finds game window by process name ("TotalBattle.exe") or window title substring.
    Falls back to full screen monitor if window not found.

get_scale() → (scale_x, scale_y)
    Returns (window.width / 1920, window.height / 1080).
    Returns (1.0, 1.0) if game window not found (safe fallback).

scale_coord(x, y) → (int, int)
    Applies scale + window offset. Converts reference coords to actual screen coords.

scale_region(x, y, w, h) → (int, int, int, int)
    Same for regions.
```

## `button_finder.py`

```
find_colored_button(
    region: tuple(x, y, w, h),
    color: Literal['green', 'purple'],
    pick: Literal['rightmost', 'leftmost', 'topmost', 'largest'] = 'largest',
    min_area: int = 800,
) → (cx, cy) | None

    1. Screenshot of region
    2. Convert to HSV
    3. Apply color mask (see HSV ranges below)
    4. Find contours above min_area
    5. Filter by aspect ratio (buttons are wide: w > h)
    6. Pick by rule: rightmost=max(cx), leftmost=min(cx), topmost=min(cy), largest=max(area)
    7. Return absolute screen coords (region.x + local_cx, region.y + local_cy)
    8. Return None if no contour found
```

### HSV Ranges (calibrated from targets_2/ screenshots)

```python
HSV_GREEN  = ((40, 50, 50),  (85, 255, 255))   # game's green buttons
HSV_PURPLE = ((125, 50, 50), (155, 255, 255))   # «Ускорить» on Carter bar
```

## Changes to `crypt_hunter.py`

New helper method `_find_button(color, pick, region_ref)`:
- Calls `scale_region()` on reference region
- Calls `find_colored_button()`
- Falls back to `scale_coord(*hardcoded_fallback)` if not found
- Logs which path was taken

Replace 5 hardcoded clicks:

| Method | Region reference (1920×1080) | color | pick | fallback |
|--------|------------------------------|-------|------|----------|
| `_send_captain` → Study | (850, 720, 400, 100) | green | rightmost | CRYPT_STUDY_BTN |
| `_send_captain` → Open | (750, 720, 300, 100) | green | leftmost | CRYPT_OPEN_BTN |
| `_click_captain_event` | (900, 90, 400, 50) | purple | largest | CARTER_EVENT_BAR |
| `_accelerate` → Use | (900, 400, 400, 200) | green | topmost | ACCEL_USE_BTN |
| `_scroll_and_find` → Goto | (1100, 240, 200, 580) | green | — (per row, use cy from YOLO box) | WT_GOTO_BTN_X |

Note: «Перейти» button keeps X from `find_colored_button` but Y from the YOLO-detected crypt row.

## Error Handling

- `find_colored_button` always returns `None` on any exception (never raises)
- `_find_button` always falls back to hardcoded coords — zero regression
- Window not found → scale = 1.0 → original coords used unchanged

## Testing

- Unit tests for `parse_hsv_mask`, `pick_contour` (pure functions, no screen)
- Integration: `python -m button_finder --demo` → draws rectangles on live screen
- `window_scaler` tested with mock window rect

## Out of Scope

- Browser client window detection (added later if needed)
- Template matching (not needed given color+region approach)
- Other dialogs beyond crypt flow
