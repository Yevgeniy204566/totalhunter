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
        """_yolo_unblock_time=0 по умолчанию — YOLO разблокирован."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._yolo_unblock_time = 0.0
        assert time.time() >= eng._yolo_unblock_time  # YOLO активен

    def test_trigger_sets_blocked_true(self):
        """_trigger_yolo_block() немедленно выставляет unblock_time в будущее."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._yolo_unblock_time = 0.0
        eng._trigger_yolo_block(block_seconds=60)   # длинный — точно в будущем
        assert time.time() < eng._yolo_unblock_time  # YOLO заблокирован

    def test_flag_resets_after_timeout(self):
        """После block_seconds timestamp уже в прошлом — YOLO разблокирован."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._yolo_unblock_time = 0.0
        eng._trigger_yolo_block(block_seconds=0.05)
        assert time.time() < eng._yolo_unblock_time  # сразу — заблокирован
        time.sleep(0.2)
        assert time.time() >= eng._yolo_unblock_time  # после — разблокирован


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
        """roy_client.report вызывается при успешном OCR, РОЙ включён и ивент активен."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        eng.on_last_exchange_callback = None
        eng.on_pool_refresh_callback = None
        eng.roy_enabled = True
        eng.event_active = True

        ocr = {'kingdom': 3, 'x': 145, 'y': 72, 'percent': 50}
        with patch('roy.exchange_reader.wait_and_read', return_value=ocr):
            eng._roy_on_found()

        eng._roy_client.report.assert_called_once_with(
            kingdom=3, x=145, y=72, percent=50,
            on_success=None
        )

    def test_roy_report_not_called_on_false_detection(self):
        """roy_client.report НЕ вызывается при ложной детекции."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        eng.on_last_exchange_callback = None
        eng.roy_enabled = True
        eng.event_active = True

        with patch('roy.exchange_reader.wait_and_read', return_value=None):
            eng._roy_on_found()

        eng._roy_client.report.assert_not_called()

    def test_roy_report_not_called_when_event_not_active(self):
        """roy_client.report НЕ вызывается если ивент «Торговые Пути» не активен,
        даже при успешном OCR и включённом тумблере РОЙ."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        eng.on_last_exchange_callback = None
        eng.on_pool_refresh_callback = None
        eng.roy_enabled = True
        eng.event_active = False

        ocr = {'kingdom': 3, 'x': 145, 'y': 72, 'percent': 50}
        with patch('roy.exchange_reader.wait_and_read', return_value=ocr):
            eng._roy_on_found()

        eng._roy_client.report.assert_not_called()

    def test_roy_report_not_called_when_roy_disabled(self):
        """roy_client.report НЕ вызывается если тумблер РОЙ выключен,
        даже при успешном OCR и активном ивенте."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        eng.on_last_exchange_callback = None
        eng.on_pool_refresh_callback = None
        eng.roy_enabled = False
        eng.event_active = True

        ocr = {'kingdom': 3, 'x': 145, 'y': 72, 'percent': 50}
        with patch('roy.exchange_reader.wait_and_read', return_value=ocr):
            eng._roy_on_found()

        eng._roy_client.report.assert_not_called()


class TestRoyFoundWrapper:
    """B2: _build_roy_wrapper изолирует original_cb — _roy_on_found вызывается всегда."""

    def test_on_found_called_despite_original_cb_raising(self):
        """_roy_on_found вызывается даже если original_cb бросает исключение."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)

        on_found_calls = []
        eng._roy_on_found = lambda: on_found_calls.append(True)

        crashing_cb = MagicMock(side_effect=RuntimeError("GUI crash"))
        wrapper = eng._build_roy_wrapper(crashing_cb)  # метод ещё не существует → RED
        wrapper()

        assert len(on_found_calls) == 1
        crashing_cb.assert_called_once()

    def test_on_found_called_when_no_original_cb(self):
        """_roy_on_found вызывается если original_cb = None."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)

        on_found_calls = []
        eng._roy_on_found = lambda: on_found_calls.append(True)

        wrapper = eng._build_roy_wrapper(None)
        wrapper()

        assert len(on_found_calls) == 1

    def test_original_cb_receives_args_when_no_exception(self):
        """original_cb получает все аргументы без изменений."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_on_found = lambda: None

        normal_cb = MagicMock()
        wrapper = eng._build_roy_wrapper(normal_cb)
        wrapper("pos_arg", kw="val")

        normal_cb.assert_called_once_with("pos_arg", kw="val")
