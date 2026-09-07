"""
TDD: авто-стоп охоты за склепами по количеству и по времени.

Два независимых лимита (crypt_autostop_count / crypt_autostop_seconds).
Срабатывает тот, что достигнут первым. None = «Выкл», лимит не проверяется.
"""
from unittest.mock import MagicMock, patch

import main as _main_module

crypt_autostop_reason = _main_module.crypt_autostop_reason
format_hms = _main_module.format_hms
crypt_count_remaining_text = _main_module.crypt_count_remaining_text
crypt_time_remaining_text = _main_module.crypt_time_remaining_text


class TestCryptCountRemainingText:
    def test_no_limit_is_empty(self):
        assert crypt_count_remaining_text(37, None) == ""

    def test_counts_down_from_limit(self):
        assert crypt_count_remaining_text(37, 50) == "13"

    def test_clamped_to_zero_when_exceeded(self):
        assert crypt_count_remaining_text(51, 50) == "0"

    def test_full_limit_when_nothing_found_yet(self):
        assert crypt_count_remaining_text(0, 50) == "50"


class TestCryptTimeRemainingText:
    def test_no_limit_is_empty(self):
        assert crypt_time_remaining_text(100.0, None) == ""

    def test_counts_down_from_limit(self):
        assert crypt_time_remaining_text(100.0, 3600) == format_hms(3500.0)

    def test_clamped_to_zero_when_exceeded(self):
        assert crypt_time_remaining_text(3700.0, 3600) == "00:00:00"


class TestCryptAutostopReasonPure:
    def test_no_limits_never_stops(self):
        assert crypt_autostop_reason(5, None, 100.0, None) is None

    def test_count_limit_not_reached(self):
        assert crypt_autostop_reason(49, 50, 0.0, None) is None

    def test_count_limit_reached_returns_count(self):
        assert crypt_autostop_reason(50, 50, 0.0, None) == "count"

    def test_count_limit_exceeded_returns_count(self):
        assert crypt_autostop_reason(51, 50, 0.0, None) == "count"

    def test_time_limit_not_reached(self):
        assert crypt_autostop_reason(0, None, 3599.0, 3600) is None

    def test_time_limit_reached_returns_time(self):
        assert crypt_autostop_reason(0, None, 3600.0, 3600) == "time"

    def test_both_limits_set_count_reached_first(self):
        assert crypt_autostop_reason(50, 50, 100.0, 3600) == "count"

    def test_both_limits_set_time_reached_first(self):
        assert crypt_autostop_reason(10, 50, 3600.0, 3600) == "time"


class TestFormatHms:
    def test_zero(self):
        assert format_hms(0) == "00:00:00"

    def test_under_a_minute(self):
        assert format_hms(59) == "00:00:59"

    def test_exact_hour(self):
        assert format_hms(3661) == "01:01:01"

    def test_truncates_fractional_seconds(self):
        assert format_hms(1.9) == "00:00:01"


class TestOnCryptFoundAutostopCount:
    """on_crypt_found уже останавливает бота при low_credits (self.after(0, self.toggle_crypt_bot)) —
    авто-стоп по количеству склепов должен работать тем же способом, независимо от кредитов."""

    def _make_app(self, count_limit, current_found_count, time_limit=None, session_start=None):
        app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
        app.current_lang = "RU"
        app.current_credits = 5
        app._crypt_found_count = current_found_count
        app._crypt_autostop_count = count_limit
        app._crypt_autostop_seconds = time_limit
        app._crypt_session_start = session_start
        app.crypt_status_label = MagicMock()
        app.crypt_count_countdown_label = MagicMock()
        app.after = lambda delay, fn=None, *a, **kw: fn() if fn else None
        app.toggle_crypt_bot = MagicMock()
        app._update_credits_display = MagicMock()
        with patch("auth.spend_credit", return_value={"success": True, "credits": 4}), \
             patch("main.messagebox"), patch("main.webbrowser"):
            app.on_crypt_found("Обычный")
        return app

    def test_stops_when_count_limit_reached(self):
        app = self._make_app(count_limit=10, current_found_count=9)  # → 10 после инкремента
        app.toggle_crypt_bot.assert_called_once()

    def test_updates_count_countdown_label(self):
        app = self._make_app(count_limit=50, current_found_count=36)  # → 37 после инкремента
        text = app.crypt_count_countdown_label.configure.call_args.kwargs.get("text")
        assert text == "13"

    def test_count_countdown_label_empty_when_limit_off(self):
        app = self._make_app(count_limit=None, current_found_count=5)
        text = app.crypt_count_countdown_label.configure.call_args.kwargs.get("text")
        assert text == ""

    def test_does_not_stop_below_count_limit(self):
        app = self._make_app(count_limit=10, current_found_count=3)
        app.toggle_crypt_bot.assert_not_called()

    def test_does_not_stop_when_limit_is_off(self):
        app = self._make_app(count_limit=None, current_found_count=999)
        app.toggle_crypt_bot.assert_not_called()


class TestCryptTickTimerAutostop:
    def _make_app(self, time_limit_sec, elapsed_sec, count_limit=None, found_count=0, running=True):
        import datetime as _dt
        app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
        app.is_crypt_running = running
        app._crypt_found_count = found_count
        app._crypt_autostop_count = count_limit
        app._crypt_autostop_seconds = time_limit_sec
        app._crypt_session_start = _dt.datetime.now() - _dt.timedelta(seconds=elapsed_sec)
        app.crypt_time_countdown_label = MagicMock()
        app.after = MagicMock()
        app.toggle_crypt_bot = MagicMock()
        return app

    def test_stops_when_time_limit_reached(self):
        app = self._make_app(time_limit_sec=3600, elapsed_sec=3601)
        app._crypt_tick_timer()
        app.toggle_crypt_bot.assert_called_once()

    def test_does_not_reschedule_after_stopping(self):
        app = self._make_app(time_limit_sec=3600, elapsed_sec=3601)
        app._crypt_tick_timer()
        app.after.assert_not_called()

    def test_reschedules_when_time_limit_not_reached(self):
        app = self._make_app(time_limit_sec=3600, elapsed_sec=100)
        app._crypt_tick_timer()
        app.toggle_crypt_bot.assert_not_called()
        app.after.assert_called_once()

    def test_does_nothing_when_not_running(self):
        app = self._make_app(time_limit_sec=3600, elapsed_sec=100, running=False)
        app._crypt_tick_timer()
        app.after.assert_not_called()
        app.toggle_crypt_bot.assert_not_called()

    def test_countdown_label_empty_when_no_time_limit(self):
        """Без лимита времени — пусто (не растущий таймер сессии, как раньше)."""
        app = self._make_app(time_limit_sec=None, elapsed_sec=61)
        app._crypt_tick_timer()
        text = app.crypt_time_countdown_label.configure.call_args.kwargs.get("text")
        assert text == ""

    def test_countdown_label_shows_remaining_time(self):
        """datetime.now() зафиксирован — иначе реальный дрейф в миллисекунды
        между вычислением session_start и elapsed делает тест хрупким."""
        import datetime as _dt
        app = self._make_app(time_limit_sec=3600, elapsed_sec=100)
        fixed_now = app._crypt_session_start + _dt.timedelta(seconds=100)
        with patch("main._dt") as mock_dt:
            mock_dt.datetime.now.return_value = fixed_now
            app._crypt_tick_timer()
        text = app.crypt_time_countdown_label.configure.call_args.kwargs.get("text")
        assert text == "00:58:20"
