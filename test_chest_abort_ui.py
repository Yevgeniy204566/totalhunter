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


def test_start_after_abort_uses_fresh_events(monkeypatch):
    """Регрессия 2026-11-14 (живой лог владельца): после экстренной остановки флаг abort оставался
    взведённым, и каждый следующий «СТАРТ» сразу прерывался (reason=abort, кадров=0)."""
    import chest_reader
    captured = {}

    monkeypatch.setattr(chest_reader, "grab_fullscreen", lambda: object())
    monkeypatch.setattr(chest_reader, "detect_dialog_bbox", lambda f: (0, 0, 10, 10))
    monkeypatch.setattr(chest_reader, "init_db", lambda *a, **k: MagicMock())
    monkeypatch.setattr(chest_reader, "get_unsynced_counts", lambda c: {})

    def fake_collect(stop_flag, **kw):
        captured["abort_set_at_start"] = kw["abort_flag"]()
        captured["stop_set_at_start"] = stop_flag()
        return {"counts": {}, "items": []}
    monkeypatch.setattr(chest_reader, "collect_chests", fake_collect)

    class _SyncThread:
        def __init__(self, target=None, daemon=None, **kw): self._t = target
        def start(self): self._t()
    monkeypatch.setattr(_main_module.threading, "Thread", _SyncThread)

    app = _app(running=False)
    app.after = lambda ms, fn=None, *a: None
    app.chest_kingdom_entry = MagicMock(); app.chest_kingdom_entry.get.return_value = "K"
    app.chest_clan_entry = MagicMock(); app.chest_clan_entry.get.return_value = "C"
    app._other_automation_running = lambda exclude=None: False
    app.chest_speed_slider = MagicMock(); app.chest_speed_slider.get.return_value = 0.5
    app.chest_full_lang_var = MagicMock(); app.chest_full_lang_var.get.return_value = False
    app.chest_auto_send_var = MagicMock(); app.chest_auto_send_var.get.return_value = False

    app._chest_abort_event.set()          # прошлый запуск закончился экстренной остановкой
    app._chest_stop_event.set()
    app.toggle_chest_bot()

    assert captured["abort_set_at_start"] is False
    assert captured["stop_set_at_start"] is False
