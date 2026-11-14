"""Экстренная кнопка «Остановить распознавание» (владелец 2026-11-14) и мгновенная обратная связь
обычного «Стоп»."""
from unittest.mock import MagicMock
import threading

import main as _main_module
from main import LANGS

App = _main_module.TotalHunterApp


def _app(running=True):
    app = App.__new__(App)
    app.current_lang = "RU"
    app._chest_running = running
    app._chest_stop_event = threading.Event()
    app._chest_abort_event = threading.Event()
    app.chest_status_label = MagicMock()
    app.chest_start_btn = MagicMock()
    app.chest_send_btn = MagicMock()
    app._chest_delete_batch_btn = MagicMock()
    app.chest_abort_btn = MagicMock()
    app._update_chest_counts_display = MagicMock()
    app._refresh_chest_queue = MagicMock()
    return app


def test_abort_sets_both_events_and_shows_stopping():
    app = _app()
    app.abort_chest_recognition()
    assert app._chest_abort_event.is_set() and app._chest_stop_event.is_set()
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_stopping"]


def test_abort_does_nothing_when_not_running():
    app = _app(running=False)
    app.abort_chest_recognition()
    assert not app._chest_abort_event.is_set()


def test_plain_stop_shows_stopping_immediately():
    app = _app()
    app.toggle_chest_bot()
    assert app._chest_stop_event.is_set() and not app._chest_abort_event.is_set()
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_stopping"]


def test_done_after_abort_tells_player_queue_is_kept(monkeypatch):
    import chest_reader
    monkeypatch.setattr(chest_reader, "count_pending", lambda *a, **k: 120)
    app = _app()
    app._on_chest_collection_done({"counts": {}, "aborted": True})
    text = app.chest_status_label.configure.call_args.kwargs["text"]
    assert "120" in text
    assert app._chest_running is False
    assert app.chest_abort_btn.configure.call_args.kwargs["state"] == "disabled"


def test_every_language_has_abort_texts():
    for code in LANGS:
        for key in ("chest_abort_btn", "chest_stopping", "chest_aborted"):
            assert LANGS[code].get(key), (code, key)
        assert "{n}" in LANGS[code]["chest_aborted"], code
