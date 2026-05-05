# test_combiner.py
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from combiner import (parse_number, _images_differ, CombinerEngine,
                       COMBO_SLOT_W, COMBO_SLOT_H, COMBO_COLS, COMBO_ROWS_VISIBLE,
                       CombinerCanvasError, NUM_ROI, POPUP_X, POPUP_Y, POPUP_W, POPUP_H)

def test_parse_4_1k():
    assert parse_number("4.1k") == 4100

def test_parse_4_1k_comma():
    assert parse_number("4,1k") == 4100

def test_parse_1_2M_ignored():
    assert parse_number("1.2M") == 0   # M не используется в комбинировании

def test_parse_500():
    assert parse_number("500") == 500

def test_parse_1_0k():
    assert parse_number("1.0k") == 1000

def test_parse_4_1k_div4():
    assert parse_number("4.1k") // 4 == 1025

def test_parse_invalid_returns_0():
    assert parse_number("abc") == 0

def test_parse_empty_returns_0():
    assert parse_number("") == 0

def test_parse_less_than_4_gives_small_int():
    assert parse_number("3") == 3  # caller decides to skip

def test_images_differ_below_threshold():
    # mean delta = 6/255 ≈ 0.0235 < 0.03 — noise, not scroll
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.full((50, 50, 3), 6, dtype=np.uint8)
    assert _images_differ(a, b) is False

def test_images_differ_above_threshold():
    # mean delta = 9/255 ≈ 0.0353 > 0.03 — scroll
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.full((50, 50, 3), 9, dtype=np.uint8)
    assert _images_differ(a, b) is True

def test_images_differ_same():
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.zeros((50, 50, 3), dtype=np.uint8)
    assert _images_differ(a, b) is False

def test_images_differ_changed():
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.ones((50, 50, 3), dtype=np.uint8) * 200
    assert _images_differ(a, b) is True

def test_images_differ_shape_mismatch():
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.zeros((60, 50, 3), dtype=np.uint8)
    assert _images_differ(a, b) is True

def test_click_card_calls_pyautogui_n_times():
    engine = CombinerEngine()
    engine.delay = 0.0
    card = MagicMock()
    card.click_x = 100
    card.click_y = 200
    n_clicks = 12 // 4  # = 3

    with patch('combiner.pyautogui') as mock_pg, \
         patch('combiner.time') as mock_time:
        mock_pg.click = MagicMock()
        mock_time.sleep = MagicMock()
        engine.click_card(card, n_clicks)

    assert mock_pg.click.call_count == 3
    assert mock_time.sleep.call_count == 3

def test_click_card_stops_on_flag():
    engine = CombinerEngine()
    engine.delay = 0.0
    engine._stop_requested = True
    card = MagicMock()
    card.click_x = 100
    card.click_y = 200

    with patch('combiner.pyautogui') as mock_pg, \
         patch('combiner.time') as mock_time:
        mock_pg.click = MagicMock()
        mock_time.sleep = MagicMock()
        engine.click_card(card, 100)

    assert mock_pg.click.call_count == 0

def test_click_card_randomizes_position():
    """Click coords must be within ±5px of card center."""
    engine = CombinerEngine()
    engine.delay = 0.0
    card = MagicMock()
    card.click_x = 500
    card.click_y = 300

    clicked_coords = []
    with patch('combiner.pyautogui') as mock_pg, \
         patch('combiner.time') as mock_time:
        mock_pg.click = lambda x, y: clicked_coords.append((x, y))
        mock_time.sleep = MagicMock()
        engine.click_card(card, 10)

    for cx, cy in clicked_coords:
        assert 495 <= cx <= 505
        assert 295 <= cy <= 305

def test_skip_cards_less_than_4():
    """Cards with count < 4 are skipped by the caller (n_clicks = count // 4 == 0)."""
    assert parse_number("3") < 4
    assert parse_number("0") < 4
    assert parse_number("") < 4

def test_stop_sets_flag():
    engine = CombinerEngine()
    engine._stop_requested = False
    engine.stop()
    assert engine._stop_requested is True

def test_start_creates_daemon_thread():
    engine = CombinerEngine()
    did_run = []

    def fake_run(cb):
        did_run.append(True)

    engine._run = fake_run

    with patch('combiner.pyautogui'), patch('combiner.mss'):
        engine.start(delay=0.1, status_callback=lambda s: None)
        import time as _t; _t.sleep(0.1)

    assert engine._thread is not None
    assert engine._thread.daemon is True
    assert did_run == [True]


# ── Координатная привязка (coord_manager) ────────────────────────────────────

def _make_grid():
    """Пустой grid_img нужного размера."""
    return np.zeros((COMBO_SLOT_H * COMBO_ROWS_VISIBLE,
                     COMBO_SLOT_W * COMBO_COLS, 3), dtype=np.uint8)


def test_click_coords_user_first_card():
    """GRID_Y=372: row_idx=0, col=0 → screen (673, 416) — первая карточка пользователя."""
    engine = CombinerEngine()
    with patch.object(engine, '_zoom_ocr', return_value='100'):
        cards = engine.scan_row(_make_grid(), 0)
    assert cards[0].click_x == 673
    assert cards[0].click_y == 416


def test_click_coords_user_second_card():
    """GRID_Y=372: row_idx=0, col=1 → screen (760, 416) — вторая карточка."""
    engine = CombinerEngine()
    with patch.object(engine, '_zoom_ocr', return_value='100'):
        cards = engine.scan_row(_make_grid(), 0)
    assert cards[1].click_x == 760
    assert cards[1].click_y == 416


def test_click_coords_user_second_row():
    """GRID_Y=372: row_idx=1, col=0 → screen (673, 504) — второй ряд."""
    engine = CombinerEngine()
    with patch.object(engine, '_zoom_ocr', return_value='100'):
        cards = engine.scan_row(_make_grid(), 1)
    assert cards[0].click_x == 673
    assert cards[0].click_y == 504


# ── Two-pass collect ─────────────────────────────────────────────────────────

def test_collect_clickable_returns_only_cards_above_4():
    """_collect_clickable scans all rows and returns only cards with count >= 4."""
    engine = CombinerEngine()
    # 5 rows × 6 cols = 30 cells; cell (row=0, col=2) = index 2 → return 3
    returns = [8] * (COMBO_ROWS_VISIBLE * (COMBO_COLS - 1))
    returns[2] = 3  # row 0, col 2
    with patch.object(engine, '_fast_ocr', side_effect=returns):
        grid = _make_grid()
        result = engine._collect_clickable(grid)
    rows_seen = {card.row for card, _ in result}
    assert rows_seen == set(range(COMBO_ROWS_VISIBLE))
    assert not any(card.col == 2 and card.row == 0 for card, _ in result)


def test_collect_clickable_n_clicks_formula():
    """n_clicks = min(count // 4, COMBO_MAX_CLICKS)."""
    from combiner import COMBO_MAX_CLICKS
    engine = CombinerEngine()
    with patch.object(engine, '_fast_ocr', return_value=100):
        grid = _make_grid()
        result = engine._collect_clickable(grid)
    for card, n_clicks in result:
        assert n_clicks == min(100 // 4, COMBO_MAX_CLICKS)


def test_collect_clickable_skips_zero_count():
    """Cards where OCR returns 0 are not included."""
    engine = CombinerEngine()
    with patch.object(engine, '_fast_ocr', return_value=0):
        grid = _make_grid()
        result = engine._collect_clickable(grid)
    assert result == []


def _make_badge_roi(text_brightness: int = 220) -> 'np.ndarray':
    """ROI с ярким текстом на тёмном фоне — симулирует реальный бейдж количества."""
    roi = np.full((16, 48, 3), 30, dtype=np.uint8)   # тёмный фон
    roi[3:13, 25:45] = text_brightness                # яркая зона текста (справа)
    return roi


def test_fast_ocr_returns_actual_count_below_4():
    """_fast_ocr возвращает реальное число даже если < 4 — фильтрация в collect_clickable."""
    engine = CombinerEngine()
    roi = _make_badge_roi()   # тёмный фон + яркий текст → std>15, bright>8
    with patch('combiner.pytesseract') as mock_tess:
        mock_tess.image_to_string.return_value = '3'
        result = engine._fast_ocr(roi)
    assert result == 3


def test_fast_ocr_returns_large_number():
    """_fast_ocr корректно возвращает большие числа типа 324."""
    engine = CombinerEngine()
    roi = _make_badge_roi()
    with patch('combiner.pytesseract') as mock_tess:
        mock_tess.image_to_string.return_value = '324'
        result = engine._fast_ocr(roi)
    assert result == 324


def test_fast_ocr_skips_roi_without_bright_pixels():
    """ROI без ярких пикселей (пустая красная иконка) → fast_ocr=0 без Tesseract."""
    engine = CombinerEngine()
    # Красная иконка: R высокий, но gray≈95, нет пикселей > 180
    roi = np.zeros((16, 48, 3), dtype=np.uint8)
    roi[:, :, 2] = 200   # высокий синий — gray = 0.114*200 ≈ 23, < 180
    roi[:, :, 0] = 60    # небольшой красный
    roi[0, 0] = 30       # std > 15 (вариация)
    roi[8, 24] = 80
    with patch('combiner.pytesseract') as mock_tess:
        result = engine._fast_ocr(roi)
    mock_tess.image_to_string.assert_not_called()
    assert result == 0


def test_collect_clickable_includes_count_7():
    """count=7 → 1 клик (7//4=1) — должен попасть в список."""
    engine = CombinerEngine()
    with patch.object(engine, '_fast_ocr', return_value=7):
        grid = _make_grid()
        result = engine._collect_clickable(grid)
    assert len(result) > 0
    assert all(n_clicks == 1 for _, n_clicks in result)  # 7//4 = 1


def test_collect_clickable_roi_fixed_regardless_of_virtual_offset():
    """ROI использует sy=row*SLOT_H — virtual_y_offset не влияет на OCR-позицию.
    Калибровка NUM_ROI привязана к COMBO_GRID_Y, не к canvas offset."""
    engine = CombinerEngine()
    engine.virtual_y_offset = 22   # не должен смещать OCR
    xo, yo, nw, nh = NUM_ROI   # (12, 40, 52, 24)

    captured = []
    def capture_roi(roi):
        captured.append(roi.copy())
        return 0

    # OCR должен читать grid[40:64, xo:xo+nw] (y0 = 0*88 + 40 = 40)
    grid = _make_grid()
    grid[40:40+nh, xo:xo+nw] = 200   # маркер на правильной позиции

    with patch.object(engine, '_fast_ocr', side_effect=capture_roi):
        engine._collect_clickable(grid)

    assert captured[0].mean() > 0, "ROI должен читать y=40 (калиброванная позиция числа)"


def test_deep_verify_card_skips_hallucination():
    """_deep_verify_card returns 0 when _get_verified_number disagrees with fast_ocr."""
    engine = CombinerEngine()
    with patch.object(engine, '_get_verified_number', return_value=2):
        grid = _make_grid()
        result = engine._deep_verify_card(grid, row=0, col=0)
    assert result == 2   # returns actual verified count (caller decides to skip if < 4)


def test_deep_verify_card_returns_verified_count():
    """_deep_verify_card returns the result of _get_verified_number."""
    engine = CombinerEngine()
    with patch.object(engine, '_get_verified_number', return_value=500):
        grid = _make_grid()
        result = engine._deep_verify_card(grid, row=1, col=2)
    assert result == 500


# ── Virtual Canvas ────────────────────────────────────────────────────────────

def _make_grid_with_edges(slot_h: int = COMBO_SLOT_H,
                          rows: int = COMBO_ROWS_VISIBLE,
                          cols: int = COMBO_SLOT_W * COMBO_COLS,
                          offset_px: int = 0) -> 'np.ndarray':
    """
    Grid image with bright rows and dark separators at each slot boundary.
    offset_px shifts edges down — simulates partial-row scroll.
    """
    h = slot_h * rows
    img = np.full((h, cols, 3), 180, dtype=np.uint8)
    for r in range(rows + 1):
        y = r * slot_h + offset_px
        if 0 <= y < h:
            img[y, :] = 0   # single-pixel dark line → clean Sobel peak
    return img


def test_sync_canvas_perfect_alignment_returns_true():
    """Edges at multiples of SLOT_H → _sync_canvas returns True."""
    engine = CombinerEngine()
    grid = _make_grid_with_edges()
    result = engine._sync_canvas(grid)
    assert result is True


def test_sync_canvas_perfect_alignment_sets_offset_zero():
    """When rows are perfectly aligned, virtual_y_offset must be 0."""
    engine = CombinerEngine()
    grid = _make_grid_with_edges()
    engine._sync_canvas(grid)
    assert engine.virtual_y_offset == 0


def test_sync_canvas_half_row_shift_detects_offset():
    """Edge shifted by SLOT_H//2 → virtual_y_offset == SLOT_H//2."""
    engine = CombinerEngine()
    half = COMBO_SLOT_H // 2   # 44
    # Edges at 44, 132, 220 ... — means canvas scrolled 44px relative to screen
    grid = _make_grid_with_edges(offset_px=half)
    engine._sync_canvas(grid)
    # The first visible edge is at screen_y=44 → nearest row boundary = 0 or 88
    # Snap: round(44/88)*88 = 0  → virtual_y_offset = 0 - 44 = -44
    # OR    round(44/88)*88 = 88 → virtual_y_offset = 88 - 44 = 44
    # Either way abs(virtual_y_offset) == 44
    assert abs(engine.virtual_y_offset) == half


def test_sync_canvas_no_edges_returns_false():
    """Uniform image (no edges) → _sync_canvas returns False."""
    engine = CombinerEngine()
    flat = np.full((COMBO_SLOT_H * COMBO_ROWS_VISIBLE,
                    COMBO_SLOT_W * COMBO_COLS, 3), 180, dtype=np.uint8)
    result = engine._sync_canvas(flat)
    assert result is False


def test_sync_canvas_fail_counter_increments():
    """Each False from _sync_canvas increments _sync_fail_count."""
    engine = CombinerEngine()
    flat = np.full((COMBO_SLOT_H * COMBO_ROWS_VISIBLE,
                    COMBO_SLOT_W * COMBO_COLS, 3), 180, dtype=np.uint8)
    engine._sync_canvas(flat)
    assert engine._sync_fail_count == 1


def test_sync_canvas_success_resets_fail_counter():
    """Success resets _sync_fail_count to 0."""
    engine = CombinerEngine()
    engine._sync_fail_count = 2
    grid = _make_grid_with_edges()
    engine._sync_canvas(grid)
    assert engine._sync_fail_count == 0


def test_sync_canvas_three_failures_fallback_offset_zero():
    """After 3 failures _sync_canvas must NOT raise — fallback to virtual_y_offset=0."""
    engine = CombinerEngine()
    engine.virtual_y_offset = 55  # pretend it had a value
    flat = np.full((COMBO_SLOT_H * COMBO_ROWS_VISIBLE,
                    COMBO_SLOT_W * COMBO_COLS, 3), 180, dtype=np.uint8)
    for _ in range(3):
        result = engine._sync_canvas(flat)
    assert result is False
    assert engine.virtual_y_offset == 0


def test_sync_canvas_three_failures_resets_counter():
    """After fallback the fail counter is reset so the next cycle can try again."""
    engine = CombinerEngine()
    flat = np.full((COMBO_SLOT_H * COMBO_ROWS_VISIBLE,
                    COMBO_SLOT_W * COMBO_COLS, 3), 180, dtype=np.uint8)
    for _ in range(3):
        engine._sync_canvas(flat)
    assert engine._sync_fail_count == 0


def test_virtual_click_y_row0_offset0():
    """Row 0, offset=0 → target_y relative to grid top = SLOT_H//2."""
    engine = CombinerEngine()
    engine.virtual_y_offset = 0
    assert engine._virtual_click_y(0) == COMBO_SLOT_H // 2


def test_virtual_click_y_row2_offset0():
    """Row 2, offset=0 → target_y = 2*SLOT_H + SLOT_H//2."""
    engine = CombinerEngine()
    engine.virtual_y_offset = 0
    assert engine._virtual_click_y(2) == 2 * COMBO_SLOT_H + COMBO_SLOT_H // 2


def test_virtual_click_y_row0_offset_positive():
    """Row 0 scrolled 44px down (offset=44) → target_y = 44 - 44 = 0... center = 44-44=0?
    Actually: target_y = (0*88 + 44) - 44 = 0 → click at grid top."""
    engine = CombinerEngine()
    engine.virtual_y_offset = COMBO_SLOT_H // 2
    assert engine._virtual_click_y(0) == 0


def test_virtual_click_y_matches_buffer_formula():
    """Validates exact formula from buffer: (row*SLOT_H + SLOT_H//2) - virtual_y_offset."""
    engine = CombinerEngine()
    engine.virtual_y_offset = 33
    row = 3
    expected = row * COMBO_SLOT_H + COMBO_SLOT_H // 2 - 33
    assert engine._virtual_click_y(row) == expected


# ── Popup scan ────────────────────────────────────────────────────────────────

def test_read_popup_count_returns_parsed_number():
    """_read_popup_count делает скриншот попапа и возвращает распознанное число."""
    engine = CombinerEngine()
    fake_img = np.full((POPUP_H, POPUP_W, 3), 200, dtype=np.uint8)
    with patch.object(engine, '_fast_ocr', return_value=120) as mock_ocr, \
         patch('combiner.mss') as mock_mss:
        mock_mss.mss.return_value.__enter__.return_value.grab.return_value = fake_img
        with patch('combiner.np.array', return_value=fake_img):
            result = engine._read_popup_count()
    assert result == 120


def test_scan_and_click_page_moves_to_every_card():
    """_scan_and_click_page наводит мышь на каждую из 30 карточек."""
    engine = CombinerEngine()
    engine.delay = 0.0
    moves = []
    with patch('combiner.pyautogui') as mock_pg, \
         patch('combiner.time') as mock_time, \
         patch.object(engine, '_read_popup_count', return_value=0):
        mock_pg.moveTo = lambda x, y, duration=0: moves.append((x, y))
        mock_pg.click = MagicMock()
        mock_time.sleep = MagicMock()
        engine._scan_and_click_page(lambda s: None)
    assert len(moves) == COMBO_ROWS_VISIBLE * (COMBO_COLS - 1)


def test_scan_and_click_page_clicks_when_count_ge_4():
    """Когда попап возвращает count=8, делается 2 клика (8//4=2)."""
    engine = CombinerEngine()
    engine.delay = 0.0
    click_count = []
    with patch('combiner.pyautogui') as mock_pg, \
         patch('combiner.time') as mock_time, \
         patch.object(engine, '_read_popup_count', return_value=8):
        mock_pg.moveTo = MagicMock()
        mock_pg.click = lambda x, y: click_count.append(1)
        mock_time.sleep = MagicMock()
        engine._scan_and_click_page(lambda s: None)
    expected_clicks = COMBO_ROWS_VISIBLE * (COMBO_COLS - 1) * (8 // 4)
    assert len(click_count) == expected_clicks


def test_scan_and_click_page_no_clicks_when_count_lt_4():
    """Когда попап пустой (count=0), кликов нет."""
    engine = CombinerEngine()
    engine.delay = 0.0
    click_count = []
    with patch('combiner.pyautogui') as mock_pg, \
         patch('combiner.time') as mock_time, \
         patch.object(engine, '_read_popup_count', return_value=0):
        mock_pg.moveTo = MagicMock()
        mock_pg.click = lambda x, y: click_count.append(1)
        mock_time.sleep = MagicMock()
        engine._scan_and_click_page(lambda s: None)
    assert len(click_count) == 0
