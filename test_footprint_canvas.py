import time
import numpy as np
import pytest
import cv2


def test_record_moves_position():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.record(1.0, 0.0)
    assert fc._cx == FootprintCanvas.CENTER + 1
    assert fc._cy == FootprintCanvas.CENTER


def test_record_does_not_stamp_grid():
    """record() only tracks position — grid is stamped by draw_ray(), not record()."""
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.record(0.0, 0.0)
    assert fc._grid[fc._cy, fc._cx] == 0.0, \
        "record() must not write a timestamp — only draw_ray() stamps the grid"


def test_draw_ray_stamps_cells():
    """draw_ray() must write recent timestamps along the ray."""
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    before = time.time()
    fc.draw_ray(inland_vec=(0.0, 1.0), coast_vec=(1.0, 0.0), ray_half_length=3)
    after = time.time()
    # At least some cells in the grid should have been stamped
    stamped = fc._grid[fc._grid > 0]
    assert len(stamped) > 0, "draw_ray() must stamp grid cells"
    assert stamped.min() >= before - 0.01
    assert stamped.max() <= after + 0.01


def test_render_overlay_shape():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.draw_ray(inland_vec=(0.0, 1.0), coast_vec=(1.0, 0.0), ray_half_length=3)
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    assert overlay.shape == (180, 180, 3)


def test_render_overlay_red_pixels():
    """Footprint color is RED (BGR: low B, low G, high R)."""
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    # Stamp center cell directly for a known location
    fc._grid[fc._cy, fc._cx] = time.time()
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    # Find any non-zero pixel
    ys, xs = np.where(overlay.any(axis=2))
    assert len(ys) > 0, "Expected at least one colored pixel in overlay"
    py, px = ys[0], xs[0]
    blue  = int(overlay[py, px, 0])
    green = int(overlay[py, px, 1])
    red   = int(overlay[py, px, 2])
    assert red > 150, f"Expected RED pixel, got BGR=({blue},{green},{red})"
    assert red > blue * 2.0, f"Red should dominate blue: BGR=({blue},{green},{red})"
    assert red > green * 2.0, f"Red should dominate green: BGR=({blue},{green},{red})"


def test_render_overlay_expired():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc._grid[fc._cy, fc._cx] = time.time() - 999.0
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    assert overlay.sum() == 0, "Expired footprint should not render"


def test_reset_clears_grid():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    fc.draw_ray(inland_vec=(1.0, 0.0), coast_vec=(0.0, 1.0), ray_half_length=3)
    fc.reset()
    assert fc._grid.sum() == 0
    assert fc._cx == FootprintCanvas.CENTER
    assert fc._cy == FootprintCanvas.CENTER


def test_grid_clamp():
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    for _ in range(300):
        fc.record(1.0, 0.0)
    assert fc._cx == FootprintCanvas.GRID_SIZE - 1


def test_draw_ray_mirror_wall():
    """extra_coast_steps=2 places the mirror wall 1 step ahead (right wall)."""
    from navigator import FootprintCanvas
    fc = FootprintCanvas()
    coast_vec = (1, 0)   # coast goes right
    inland_vec = (0, 1)  # dive goes down

    # Left wall: at (CENTER-1, CENTER) — 1 step behind in coast_vec
    # Right wall: at (CENTER+1, CENTER) — 1 step ahead (extra=2: -1+2=+1)
    fc.draw_ray(inland_vec, coast_vec, ray_half_length=2)
    fc.draw_ray(inland_vec, coast_vec, ray_half_length=2, extra_coast_steps=2)

    stamped_cols = np.unique(np.where(fc._grid > 0)[1])
    assert len(stamped_cols) >= 2, \
        "Two separate wall columns expected (left + right wall)"
    col_span = stamped_cols.max() - stamped_cols.min()
    assert col_span >= 2, \
        f"Left and right walls should be separated by ≥2 columns, got span={col_span}"


def test_overlay_not_detected_as_water():
    """RED footprint pixels must NOT be mistaken for water by get_land_water_masks."""
    from navigator import FootprintCanvas, get_land_water_masks
    fc = FootprintCanvas()
    fc._grid[fc._cy, fc._cx] = time.time()
    overlay = fc.render_overlay((180, 180, 3), ttl_sec=120.0)
    _, water_mask = get_land_water_masks(overlay)
    # Red pixels should not trigger blue-water detection
    assert water_mask.sum() == 0, \
        "Red footprint pixels must NOT be detected as water (water detector is blue-biased)"
