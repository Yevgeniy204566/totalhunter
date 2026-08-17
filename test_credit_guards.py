"""
TDD: закрываем брешь бесплатного фарма при обнулении баланса или блокировке доступа
к сети только для процесса TotalHunter.exe (firewall block по одному процессу, пока
игра и остальной интернет работают нормально).

on_crypt_found (склепы) раньше игнорировал low_credits/сетевые ошибки от spend_credit()
и просто клэмпил отображаемый баланс до 0, не останавливая бота — в отличие от биржевой
ветки (_process_found), где 402 уже останавливал бота. Теперь обе ветки должны
останавливаться в двух случаях:
  - low_credits (сервер ответил 402)                → бот стопается
  - N секунд без успешного контакта сервера (offline) → бот стопается (auth.HEARTBEAT_TIMEOUT)
"""
from unittest.mock import MagicMock, patch

import main as _main_module


def _make_crypt_app(spend_result, current_credits=5):
    app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
    app.current_lang = "RU"
    app.current_credits = current_credits
    app._crypt_found_count = 0
    app.crypt_status_label = MagicMock()
    app.after = lambda delay, fn=None, *a, **kw: fn() if fn else None
    app.toggle_crypt_bot = MagicMock()
    app._update_credits_display = MagicMock()
    with patch("auth.spend_credit", return_value=spend_result):
        app.on_crypt_found("Обычный")
    return app


def _make_exchange_app(spend_result, current_credits=50):
    app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
    app.current_lang = "RU"
    app.current_credits = current_credits
    app.toggle_bot = MagicMock()
    app._update_credits_display = MagicMock()
    with patch("main.spend_credit", return_value=spend_result), \
         patch("main.webbrowser") as mock_browser, \
         patch("main.messagebox") as mock_box:
        app._process_found()
    return app, mock_browser, mock_box


class TestCryptFoundStopsOnLowCredits:
    def test_stops_bot_when_server_reports_low_credits(self):
        app = _make_crypt_app({"success": False, "low_credits": True})
        app.toggle_crypt_bot.assert_called_once()

    def test_does_not_stop_bot_on_successful_spend(self):
        app = _make_crypt_app({"success": True, "credits": 4})
        app.toggle_crypt_bot.assert_not_called()


class TestCryptFoundOfflineGuard:
    def test_stops_bot_when_offline_longer_than_heartbeat_timeout(self):
        import auth
        with patch.object(auth, "last_successful_contact", 0):
            app = _make_crypt_app({"success": False})
        app.toggle_crypt_bot.assert_called_once()

    def test_does_not_stop_bot_on_fresh_transient_failure(self):
        import auth
        with patch.object(auth, "last_successful_contact", auth.time.time()):
            app = _make_crypt_app({"success": False})
        app.toggle_crypt_bot.assert_not_called()


class TestExchangeProcessFoundOfflineGuard:
    def test_stops_bot_when_offline_longer_than_heartbeat_timeout(self):
        import auth
        with patch.object(auth, "last_successful_contact", 0):
            app, _, mock_box = _make_exchange_app({"success": False})
        app.toggle_bot.assert_called_once()
        mock_box.showwarning.assert_called_once()

    def test_does_not_stop_bot_on_fresh_transient_failure(self):
        import auth
        with patch.object(auth, "last_successful_contact", auth.time.time()):
            app, _, _ = _make_exchange_app({"success": False})
        app.toggle_bot.assert_not_called()

    def test_still_stops_and_opens_browser_on_low_credits(self):
        app, mock_browser, _ = _make_exchange_app({"success": False, "low_credits": True})
        app.toggle_bot.assert_called_once()
        mock_browser.open.assert_called_once()
