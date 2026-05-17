"""
TDD tests for YOLO detection guard and last_exchange callback.
Run: python -m pytest test_exchange_guard.py -v
"""
import time
from unittest.mock import patch, MagicMock
import pytest


class TestPacmanYoloGuard:
    """PacmanEngine блокирует YOLO на N сек после любой детекции."""

    def test_yolo_blocked_starts_false(self):
        """_yolo_blocked по умолчанию False."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._yolo_blocked = False
        assert eng._yolo_blocked is False

    def test_trigger_sets_blocked_true(self):
        """_trigger_yolo_block() немедленно выставляет флаг в True."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._yolo_blocked = False
        eng._trigger_yolo_block(block_seconds=60)   # длинный — не сбросится в тесте
        assert eng._yolo_blocked is True

    def test_flag_resets_after_timeout(self):
        """Флаг сбрасывается в False автоматически после block_seconds."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._yolo_blocked = False
        eng._trigger_yolo_block(block_seconds=0.05)
        assert eng._yolo_blocked is True
        time.sleep(0.2)
        assert eng._yolo_blocked is False


class TestHuntEngineCallback:
    """HuntEngine._roy_on_found: callback и ROY-отчёт только при реальной бирже."""

    def test_on_last_exchange_callback_default_none(self):
        """on_last_exchange_callback = None по умолчанию."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.on_last_exchange_callback = None
        assert eng.on_last_exchange_callback is None

    def test_callback_fires_on_successful_ocr(self):
        """Callback вызывается с результатом когда OCR успешен."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        calls = []
        eng.on_last_exchange_callback = calls.append

        ocr = {'kingdom': 3, 'x': 145, 'y': 72, 'percent': 50}
        with patch('roy.exchange_reader.wait_and_read', return_value=ocr):
            eng._roy_on_found()

        assert len(calls) == 1
        assert calls[0]['kingdom'] == 3
        assert calls[0]['x'] == 145
        assert calls[0]['y'] == 72

    def test_callback_not_fired_on_ocr_failure(self):
        """Callback НЕ вызывается при ложной детекции (OCR вернул None)."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        calls = []
        eng.on_last_exchange_callback = calls.append

        with patch('roy.exchange_reader.wait_and_read', return_value=None):
            eng._roy_on_found()

        assert len(calls) == 0

    def test_roy_report_called_on_success(self):
        """roy_client.report вызывается при успешном OCR."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        eng.on_last_exchange_callback = None

        ocr = {'kingdom': 3, 'x': 145, 'y': 72, 'percent': 50}
        with patch('roy.exchange_reader.wait_and_read', return_value=ocr):
            eng._roy_on_found()

        eng._roy_client.report.assert_called_once_with(
            kingdom=3, x=145, y=72, percent=50
        )

    def test_roy_report_not_called_on_false_detection(self):
        """roy_client.report НЕ вызывается при ложной детекции."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        eng.on_last_exchange_callback = None

        with patch('roy.exchange_reader.wait_and_read', return_value=None):
            eng._roy_on_found()

        eng._roy_client.report.assert_not_called()
