"""
Ожидание привязки аккаунта без опроса сервера (владелец 2026-09-28).
Раньше бот слал check_auth раз в 5 с, пока привязка не завершена (720 запросов в час на
«зависшего» игрока), а каждый повторный клик «Войти» добавлял параллельную цепочку.
Теперь сервер сам будит /vault/sync после привязки, а ответ несёт linked=True.
"""
from unittest.mock import MagicMock, patch

import auth
import main as _main_module


# ── auth.balance_sync_step ───────────────────────────────────────────────────

def test_balance_step_reports_linked_state():
    linked = []
    with patch.object(auth, "get_balance_update",
                      return_value={"credits": 1, "ref_credits": 0, "linked": True}):
        auth.balance_sync_step(lambda c: None, on_linked=lambda: linked.append(True))
    assert linked == [True]


def test_balance_step_silent_when_not_linked_or_old_server():
    linked = []
    for data in ({"credits": 1, "linked": False}, {"credits": 1}):
        with patch.object(auth, "get_balance_update", return_value=data):
            auth.balance_sync_step(lambda c: None, on_linked=lambda: linked.append(True))
    assert linked == []


# ── окно бота ────────────────────────────────────────────────────────────────

def _app():
    app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
    app._awaiting_link = False
    app.login_button = MagicMock()
    app.update_license_info = MagicMock()
    app.after = MagicMock()
    return app


def _click_login(app):
    with patch("main.generate_link_code", return_value=("123456", 999)), \
         patch("main.webbrowser"), patch("main.check_license") as check:
        app.handle_login()
    return check


def test_login_click_does_not_poll_server():
    app = _app()
    check = _click_login(app)
    check.assert_not_called()
    app.after.assert_not_called()          # никаких отложенных опросов
    assert app._awaiting_link is True
    assert not hasattr(_main_module.TotalHunterApp, "_poll_link_status")


def test_repeated_login_clicks_create_no_polling_chains():
    app = _app()
    for _ in range(3):
        check = _click_login(app)
        check.assert_not_called()
    app.after.assert_not_called()
    assert app._awaiting_link is True


def test_linked_signal_refreshes_license_once_and_clears_wait():
    app = _app()
    _click_login(app)
    app._on_account_linked()
    app._on_account_linked()               # следующие циклы long-poll тоже несут linked=True
    app.update_license_info.assert_called_once()
    assert app._awaiting_link is False


def test_linked_signal_ignored_when_not_waiting():
    app = _app()                           # уже привязанный бот: linked=True в каждом цикле
    app._on_account_linked()
    app.update_license_info.assert_not_called()
