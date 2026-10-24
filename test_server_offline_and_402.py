"""
Владелец 2026-10-24: при недоступном сервере бот не должен писать «0 алмазов / привяжите устройство» —
баланс не получен, а не нулевой. И при 402 на сундуках показывать «нужно N, у вас M» из ответа сервера.
Серверная экономика и правило «всё или ничего» (неотправленное остаётся в очереди) не затронуты.
"""
from unittest.mock import MagicMock, patch

import requests

import auth
import chest_reader
import main as _main_module
from main import LANGS, chest_low_credits_text


def _resp(status, body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body if body is not None else {}
    return r


# ── auth.check_license ───────────────────────────────────────────────────────────────

def test_check_license_marks_network_failure_as_offline():
    with patch("auth.requests.post", side_effect=requests.ConnectionError("down")), \
         patch("auth.log_error_to_server"):
        data = auth.check_license()

    assert data["offline"] is True
    assert not data.get("server_error")


def test_check_license_marks_5xx_as_server_error():
    with patch("auth.requests.post", return_value=_resp(502)):
        data = auth.check_license()

    assert data["offline"] is True
    assert data["server_error"] is True


def test_check_license_success_is_returned_untouched():
    body = {"authorized": True, "credits": 0, "email": "a@b.c"}
    with patch("auth.requests.post", return_value=_resp(200, body)):
        data = auth.check_license()

    assert data == body                 # настоящий ноль из успешного ответа — без пометки offline
    assert "offline" not in data


# ── GUI: update_license_info / старт ─────────────────────────────────────────────────

def _app():
    app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
    app.current_lang = "RU"
    app.current_credits = 40
    app._balance_known = True
    app._server_offline = None
    app.credits_label = MagicMock()
    app.crypt_credits_label = MagicMock()
    app.broadcast_frame = MagicMock()
    app.broadcast_label = MagicMock()
    app.info_banner = MagicMock()
    app._update_credits_display = MagicMock()
    app.after = MagicMock()
    return app


def test_offline_keeps_last_known_balance_and_says_no_connection():
    app = _app()
    with patch("main.check_license", return_value={"authorized": False, "credits": 0, "offline": True}):
        app.update_license_info()

    app._update_credits_display.assert_not_called()           # 40 ◆ не затирается нулём
    assert app._server_offline == "offline"
    assert app.broadcast_label.configure.call_args.kwargs["text"] == "⚠ " + LANGS["RU"]["server_offline_retry"]
    app.credits_label.configure.assert_not_called()           # баланс был известен — «—» не рисуем


def test_server_error_says_server_error():
    app = _app()
    with patch("main.check_license",
               return_value={"authorized": False, "credits": 0, "offline": True, "server_error": True}):
        app.update_license_info()

    assert app._server_offline == "server_error"
    assert "Ошибка сервера" in app.broadcast_label.configure.call_args.kwargs["text"]


def test_offline_before_first_balance_shows_dash_not_zero():
    app = _app()
    app._balance_known = False
    app.current_credits = 0
    with patch("main.check_license", return_value={"authorized": False, "credits": 0, "offline": True}):
        app.update_license_info()

    assert app.credits_label.configure.call_args.kwargs["text"] == "—"
    assert app.crypt_credits_label.configure.call_args.kwargs["text"] == "—"


def test_real_zero_balance_from_successful_answer_works_as_before():
    app = _app()
    app.user_email = None
    for name in ("label_email", "login_button", "trial_button", "ref_entry", "ref_btn", "friend_code_lb",
                 "my_code_val", "ref_link_val", "ref_balance_label", "ref_l1_label", "ref_l2_label",
                 "ref_l3_label"):
        setattr(app, name, MagicMock())
    with patch("main.check_license", return_value={"authorized": True, "credits": 0}):
        app.update_license_info()

    app._update_credits_display.assert_called_with(0)
    assert app._server_offline is None


def test_start_without_balance_while_offline_warns_about_connection_not_diamonds():
    app = _app()
    app._server_offline = "offline"
    with patch("main.messagebox") as mb:
        app._warn_no_credits()

    shown = mb.showwarning.call_args.args[1]
    assert shown == LANGS["RU"]["server_offline_retry"]
    assert shown != LANGS["RU"]["no_credits"]


def test_start_with_real_zero_still_shows_no_credits():
    app = _app()
    with patch("main.messagebox") as mb:
        app._warn_no_credits()

    assert mb.showwarning.call_args.args[1] == LANGS["RU"]["no_credits"]


def test_balance_from_long_poll_clears_offline_and_refreshes_license():
    app = _app()
    app._server_offline = "offline"
    app._on_server_balance(55)

    app._update_credits_display.assert_called_with(55)
    assert app._server_offline is None
    app.after.assert_called_once()                            # баннер перерисует повторный check_license


# ── 402 при отправке сундуков ────────────────────────────────────────────────────────

def test_export_to_api_402_carries_required_and_credits():
    body = {"detail": {"message": "Недостаточно кредитов. Пополни баланс.", "credits": 7, "required": 10}}
    with patch("chest_reader.requests.post", return_value=_resp(402, body)), \
         patch("chest_reader.get_hwid", return_value="H"):
        result = chest_reader.export_to_api("229", "Феникс", [{"chest_type": "T", "sender": "P",
                                                               "timestamp": "2026-10-24T10:00:00"}])

    assert result == {"success": False, "low_credits": True, "required": 10, "credits": 7}


def test_export_to_api_402_without_numbers_still_low_credits():
    resp = _resp(402)
    resp.json.side_effect = ValueError("not json")
    with patch("chest_reader.requests.post", return_value=resp), \
         patch("chest_reader.get_hwid", return_value="H"):
        result = chest_reader.export_to_api("229", "Феникс", [{"chest_type": "T", "sender": "P",
                                                               "timestamp": "2026-10-24T10:00:00"}])

    assert result == {"success": False, "low_credits": True}


def test_chest_low_credits_text_uses_numbers_from_server():
    text = chest_low_credits_text(LANGS["RU"], {"low_credits": True, "required": 10, "credits": 7})
    assert text == "Не хватает алмазов для отправки: нужно 10, у вас 7"


def test_chest_low_credits_text_without_numbers_has_no_link_device_wording():
    text = chest_low_credits_text(LANGS["RU"], {"low_credits": True})
    assert text == "Не хватает алмазов для отправки"
    assert "Привяжите" not in text


def test_failed_402_keeps_whole_batch_in_queue():
    """Всё или ничего: при 402 ни одна запись не удаляется из локальной очереди."""
    app = _app()
    conn = MagicMock()
    groups = [(("229", "Феникс"), [(i, "P", "T", "2026-10-24T10:00:00") for i in range(3)])]
    with patch("chest_reader.init_db", return_value=conn), \
         patch("chest_reader.get_unsynced_by_pair", return_value=groups), \
         patch("chest_reader.export_to_api",
               return_value={"success": False, "low_credits": True, "required": 10, "credits": 7}), \
         patch("chest_reader.delete_sent") as delete_sent:
        result = app._send_chest_batch("229", "Феникс")

    delete_sent.assert_not_called()
    assert result["low_credits"] is True and result["sent"] == 0


def test_every_language_has_new_messages():
    for code in LANGS:
        for key in ("server_offline_retry", "server_error_retry", "chest_not_enough_plain"):
            assert LANGS[code][key].strip(), (code, key)
        text = LANGS[code]["chest_not_enough"]
        assert "{need}" in text and "{have}" in text, code
        text.format(need=10, have=7)              # шаблон валиден
