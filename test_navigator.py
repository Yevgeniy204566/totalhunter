"""
TDD tests for navigator.py
Run: python -m pytest test_navigator.py -v
"""
import pytest
from unittest.mock import patch, MagicMock, call
import numpy as np
import cv2


# ─────────────────────────────────────────────
# PositionReader — OCR координат с экрана
# ─────────────────────────────────────────────

class TestPositionReader:

    def test_parse_coordinates_from_ocr_text(self):
        from navigator import PositionReader
        reader = PositionReader(crop_box=(0, 1000, 250, 1080))
        result = reader._parse_ocr("K: 228   X: 908   Y: 874")
        assert result == (908, 874)

    def test_parse_returns_none_on_bad_text(self):
        from navigator import PositionReader
        reader = PositionReader(crop_box=(0, 1000, 250, 1080))
        result = reader._parse_ocr("no coordinates here")
        assert result is None

    def test_parse_handles_ocr_noise(self):
        from navigator import PositionReader
        reader = PositionReader(crop_box=(0, 1000, 250, 1080))
        result = reader._parse_ocr("K: 228 X: 90B Y: B74")
        # Should return None or a tuple — must not crash
        assert result is None or isinstance(result, tuple)


# ─────────────────────────────────────────────
# PacmanJoystick — pixel-based minimap nav
# ─────────────────────────────────────────────

def _make_land_frame(size=180):
    """BGR frame that is all green land (HSV H≈40 → land range 5-95)."""
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:] = (30, 140, 50)  # BGR: green-ish land
    return frame


def _make_water_frame(size=180):
    """BGR frame that is all blue water (HSV H≈115 → water range 100-140)."""
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:] = (180, 60, 20)  # BGR: blue dominant
    return frame


# TestPacmanJoystick удалён 2026-09-26: класс PacmanJoystick убран из navigator.py (джойстик
# теперь CoastalSnakeNavigator, его тесты — test_coastal_snake*.py); тесты проверяли
# несуществующий класс и его «холст памяти».


class TestPacmanEngine:

    def test_engine_stops_when_exchange_found(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        engine.is_running = True
        engine._on_exchange_found()
        assert engine.is_running is False

    def test_engine_plays_sound_when_exchange_found(self):
        from navigator import PacmanEngine
        engine = PacmanEngine(sound_path='Logo_exchange.wav')
        with patch('winsound.PlaySound') as mock_sound:
            engine._on_exchange_found()
            mock_sound.assert_called_once()

    def test_engine_calls_callback_when_exchange_found(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        cb = MagicMock()
        engine.on_found_callback = cb
        with patch('winsound.PlaySound'):
            engine._on_exchange_found()
        cb.assert_called_once()

    def test_engine_start_sets_is_running(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        with patch('threading.Thread') as mock_thread:
            mock_thread.return_value.start = MagicMock()
            engine.start()
        assert engine.is_running is True

    def test_engine_stop_clears_is_running(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        engine.is_running = True
        engine.stop()
        assert engine.is_running is False

