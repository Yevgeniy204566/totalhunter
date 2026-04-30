# test_combiner.py
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from combiner import parse_number, _images_differ, CombinerEngine

def test_parse_4_1k():
    assert parse_number("4.1k") == 4100

def test_parse_4_1k_comma():
    assert parse_number("4,1k") == 4100

def test_parse_1_2M():
    assert parse_number("1.2M") == 1_200_000

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
