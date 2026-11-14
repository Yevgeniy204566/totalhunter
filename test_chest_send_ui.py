"""Сессия #167: «жму Отправить — ничего не происходит». Исключение в потоке отправки раньше
оставляло кнопку выключенной навсегда и не оставляло следа. Теперь кнопка возвращается,
игрок видит «ошибка отправки», причина пишется в лог сбора."""
from unittest.mock import MagicMock, patch

import chest_log
import main as _main_module


class _SyncThread:
    def __init__(self, target=None, daemon=None, **kw):
        self._t = target

    def start(self):
        self._t()


def _app():
    app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
    app.current_lang = "RU"
    app.chest_kingdom_entry = MagicMock(); app.chest_kingdom_entry.get.return_value = "K1"
    app.chest_clan_entry = MagicMock(); app.chest_clan_entry.get.return_value = "Clan"
    app.chest_send_btn = MagicMock()
    app.chest_status_label = MagicMock()
    app.chest_sent_label = MagicMock()
    app._chest_last_sent = None
    app.after = lambda ms, fn=None, *a: fn() if fn else None
    return app


def test_send_button_comes_back_when_send_raises(tmp_path):
    chest_log.start_run(log_dir=str(tmp_path))
    app = _app()
    app._send_chest_batch = MagicMock(side_effect=RuntimeError("database is locked"))
    with patch.object(_main_module.threading, "Thread", _SyncThread):
        app.send_chests_to_server()

    states = [c.kwargs.get("state") for c in app.chest_send_btn.configure.call_args_list]
    assert states[0] == "disabled" and states[-1] == "normal"
    L = _main_module.LANGS["RU"]
    assert app.chest_status_label.configure.call_args.kwargs["text"] == L["chest_send_failed"]
    assert "database is locked" in open(chest_log.current_file(), encoding="utf-8").read()


def test_collection_done_shows_error_instead_of_plain_stopped():
    app = _app()
    app.chest_start_btn = MagicMock()
    app.chest_abort_btn = MagicMock()
    app._chest_delete_batch_btn = MagicMock()
    app._update_chest_counts_display = MagicMock()
    app._refresh_chest_queue = MagicMock()
    app._on_chest_collection_done({"counts": {}, "error": "OCR: RuntimeError: timeout"})

    text = app.chest_status_label.configure.call_args.kwargs["text"]
    assert "RuntimeError: timeout" in text
    assert app._chest_running is False
    assert app.chest_send_btn.configure.call_args.kwargs["state"] == "normal"
