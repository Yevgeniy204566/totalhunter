"""
«Отправлено: N» под кнопкой СТАРТ в Сундуках (владелец 2026-09-28): сколько сундуков ушло на
сервер в последнем батче — и при авто-, и при ручной отправке.
"""
from unittest.mock import MagicMock, patch

import main as _main_module
from main import LANGS


def _app():
    app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
    app.current_lang = "RU"
    app._chest_last_sent = None
    app.chest_sent_label = MagicMock()
    return app


def _send(groups, results):
    app = _app()
    conn = MagicMock()
    with patch("chest_reader.init_db", return_value=conn), \
         patch("chest_reader.get_unsynced_by_pair", return_value=groups), \
         patch("chest_reader.export_to_api", side_effect=results), \
         patch("chest_reader.delete_sent"):
        return app._send_chest_batch("229", "Феникс")


def _rows(n):
    return [(i, "P", "T", "2026-09-28T10:00:00") for i in range(n)]


def test_batch_reports_number_of_chests_sent():
    result = _send([(("229", "A"), _rows(3)), (("229", "B"), _rows(2))],
                   [{"success": True}, {"success": True}])
    assert result["success"] is True and result["sent"] == 5


def test_failed_pair_is_not_counted():
    result = _send([(("229", "A"), _rows(3)), (("229", "B"), _rows(2))],
                   [{"success": True}, {"success": False}])
    assert result["success"] is False and result["sent"] == 3


def test_label_shows_dash_before_first_send_and_count_after():
    app = _app()
    app._render_chest_sent()
    assert app.chest_sent_label.configure.call_args.kwargs["text"] == "Отправлено: —"
    app._show_chest_sent(12)
    assert app.chest_sent_label.configure.call_args.kwargs["text"] == "Отправлено: 12"


def test_label_follows_language_switch():
    app = _app()
    app._show_chest_sent(7)
    app.current_lang = "EN"
    app._render_chest_sent()
    assert app.chest_sent_label.configure.call_args.kwargs["text"] == "Sent: 7"


def test_every_language_has_the_label():
    assert all(LANGS[code].get("chest_sent_lb") for code in LANGS)
