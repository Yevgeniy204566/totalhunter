"""
TDD: авто-обновление пула сразу после успешного report().
Алгоритм: report() success → get_pool() → on_pool_refresh_callback(pool).
Никаких таймеров, никакого поллинга.
"""

import threading
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 1. roy_client.report() вызывает on_success после успешного ответа
# ---------------------------------------------------------------------------

class TestReportOnSuccess:

    def _make_client(self):
        from roy.roy_client import RoyClient
        return RoyClient(hwid="test-hwid-0000")

    def test_on_success_called_when_server_returns_success(self):
        """on_success вызывается если сервер вернул {"success": true}."""
        client = self._make_client()
        called = threading.Event()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}

        with patch('requests.post', return_value=mock_resp):
            client.report(kingdom=1, x=100, y=200, percent=50,
                          on_success=lambda: called.set())
            called.wait(timeout=2.0)

        assert called.is_set(), "on_success не был вызван при success=True"

    def test_on_success_not_called_when_server_returns_failure(self):
        """on_success НЕ вызывается если сервер вернул {"success": false}."""
        client = self._make_client()
        called = threading.Event()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": False}

        with patch('requests.post', return_value=mock_resp):
            client.report(kingdom=1, x=100, y=200, percent=50,
                          on_success=lambda: called.set())
            called.wait(timeout=0.5)

        assert not called.is_set(), "on_success не должен вызываться при success=False"

    def test_on_success_not_called_on_network_error(self):
        """on_success НЕ вызывается при сетевой ошибке."""
        client = self._make_client()
        called = threading.Event()

        with patch('requests.post', side_effect=Exception("timeout")):
            client.report(kingdom=1, x=100, y=200, percent=50,
                          on_success=lambda: called.set())
            called.wait(timeout=0.5)

        assert not called.is_set(), "on_success не должен вызываться при ошибке сети"

    def test_report_without_on_success_works(self):
        """report() без on_success работает как прежде (обратная совместимость)."""
        client = self._make_client()
        completed = threading.Event()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}

        def _fake_post(*a, **kw):
            completed.set()
            return mock_resp

        with patch('requests.post', side_effect=_fake_post):
            client.report(kingdom=1, x=100, y=200, percent=50)
            completed.wait(timeout=2.0)

        assert completed.is_set(), "report() без on_success не отправил запрос"


# ---------------------------------------------------------------------------
# 2. engine._after_report_success → get_pool() → on_pool_refresh_callback
# ---------------------------------------------------------------------------

class TestAfterReportSuccess:

    def _make_engine(self):
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.on_pool_refresh_callback = None
        eng._roy_client = MagicMock()
        eng._roy_client.get_pool.return_value = [
            {"kingdom": 1, "x": 100, "y": 200, "percent": 30}
        ]
        return eng

    def test_get_pool_called_after_success(self):
        """_after_report_success вызывает get_pool()."""
        eng = self._make_engine()
        eng.on_pool_refresh_callback = lambda pool: None

        eng._after_report_success()

        eng._roy_client.get_pool.assert_called_once_with(consume=False)

    def test_callback_receives_pool_data(self):
        """on_pool_refresh_callback получает список координат."""
        eng = self._make_engine()
        received = []
        eng.on_pool_refresh_callback = lambda pool: received.extend(pool)

        eng._after_report_success()

        assert len(received) == 1
        assert received[0]['kingdom'] == 1
        assert received[0]['x'] == 100

    def test_no_get_pool_when_callback_not_set(self):
        """get_pool() НЕ вызывается если on_pool_refresh_callback = None."""
        eng = self._make_engine()
        eng.on_pool_refresh_callback = None

        eng._after_report_success()

        eng._roy_client.get_pool.assert_not_called()

    def test_exception_in_get_pool_does_not_crash(self):
        """Ошибка в get_pool() не роняет бот."""
        eng = self._make_engine()
        eng.on_pool_refresh_callback = lambda pool: None
        eng._roy_client.get_pool.side_effect = Exception("network error")

        # не должен бросить исключение
        eng._after_report_success()


# ---------------------------------------------------------------------------
# 3. engine._roy_on_found передаёт on_success в report()
# ---------------------------------------------------------------------------

class TestRoyOnFoundPassesCallback:

    def _make_engine_with_roy(self):
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._roy_client = MagicMock()
        eng.on_last_exchange_callback = None
        eng.on_pool_refresh_callback = MagicMock()  # задан → on_success должен прийти
        return eng

    def test_report_called_with_on_success_when_callback_set(self):
        """report() вызывается с on_success если on_pool_refresh_callback задан."""
        eng = self._make_engine_with_roy()
        ocr_result = {"kingdom": 5, "x": 300, "y": 400, "percent": 45}

        with patch('roy.exchange_reader.wait_and_read', return_value=ocr_result):
            eng._roy_on_found()

        call_kwargs = eng._roy_client.report.call_args
        assert call_kwargs is not None, "report() не был вызван"
        on_success = call_kwargs.kwargs.get('on_success') or (
            call_kwargs.args[4] if len(call_kwargs.args) > 4 else None
        )
        assert callable(on_success), "on_success должен быть callable"

    def test_report_called_without_on_success_when_callback_not_set(self):
        """report() вызывается без on_success если on_pool_refresh_callback = None."""
        eng = self._make_engine_with_roy()
        eng.on_pool_refresh_callback = None
        ocr_result = {"kingdom": 5, "x": 300, "y": 400, "percent": 45}

        with patch('roy.exchange_reader.wait_and_read', return_value=ocr_result):
            eng._roy_on_found()

        call_kwargs = eng._roy_client.report.call_args
        assert call_kwargs is not None
        on_success = call_kwargs.kwargs.get('on_success') or (
            call_kwargs.args[4] if len(call_kwargs.args) > 4 else None
        )
        assert on_success is None, "on_success должен быть None если callback не задан"
