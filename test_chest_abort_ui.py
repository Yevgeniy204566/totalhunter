"""Одна кнопка распознавания сундуков (владелец 2026-11-14): пока идёт сбор/распознавание она
«Остановить распознавание», после остановки — «Запустить распознавание» (дорабатывает очередь без
кликов по игре). Без значка, без поясняющих надписей про «СТАРТ продолжит»."""
import threading

import pytest
from unittest.mock import MagicMock

import main as _main_module
from main import LANGS

App = _main_module.TotalHunterApp


@pytest.fixture(autouse=True)
def _ocr_selfcheck_ok(monkeypatch):
    import chest_reader
    monkeypatch.setattr(chest_reader, "selfcheck_ocr",
                        lambda full_lang=False: {"ok": True, "seconds": 0.1, "error": None})
    yield


class _SyncThread:
    def __init__(self, target=None, daemon=None, **kw): self._t = target
    def start(self): self._t()


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
    app.chest_recog_btn = MagicMock()
    app.chest_time_label = MagicMock()
    app._chest_elapsed = 0.0
    app._chest_t0 = None
    app._chest_timer_job = None
    app._chest_last_progress = None
    app._chest_stalled = False
    app._chest_selfcheck_note = None
    app._update_chest_counts_display = MagicMock()
    app._refresh_chest_queue = MagicMock()
    app.after = lambda ms, fn=None, *a: fn() if (fn and ms == 0) else None
    return app


def _pending(monkeypatch, n):
    import chest_reader
    monkeypatch.setattr(chest_reader, "count_pending", lambda *a, **k: n)


def test_button_stops_when_running_and_shows_stopping():
    app = _app()
    app.toggle_chest_recognition()
    assert app._chest_abort_event.is_set() and app._chest_stop_event.is_set()
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_stopping"]


def test_button_label_while_running_is_stop():
    app = _app(running=True)
    app._refresh_chest_recognition_btn()
    kw = app.chest_recog_btn.configure.call_args.kwargs
    assert kw["text"] == LANGS["RU"]["chest_abort_btn"] and kw["state"] == "normal"


def test_button_label_when_idle_with_queue_is_start_and_enabled(monkeypatch):
    _pending(monkeypatch, 88)
    app = _app(running=False)
    app._refresh_chest_recognition_btn()
    kw = app.chest_recog_btn.configure.call_args.kwargs
    assert kw["text"] == LANGS["RU"]["chest_recognize_btn"] and kw["state"] == "normal"


def test_button_disabled_when_idle_and_queue_empty(monkeypatch):
    _pending(monkeypatch, 0)
    app = _app(running=False)
    app._refresh_chest_recognition_btn()
    assert app.chest_recog_btn.configure.call_args.kwargs["state"] == "disabled"


def test_button_starts_recognition_only_run_without_clicking_game(monkeypatch):
    import chest_reader
    _pending(monkeypatch, 88)
    captured = {}

    def fake_collect(stop_flag, **kw):
        captured.update(kw)
        captured["running_during"] = app._chest_running
        return {"counts": {}, "items": []}
    monkeypatch.setattr(chest_reader, "collect_chests", fake_collect)
    monkeypatch.setattr(_main_module.threading, "Thread", _SyncThread)
    app = _app(running=False)
    app._other_automation_running = lambda exclude=None: False
    app.chest_kingdom_entry = MagicMock(); app.chest_kingdom_entry.get.return_value = "K"
    app.chest_clan_entry = MagicMock(); app.chest_clan_entry.get.return_value = "C"
    app.chest_full_lang_var = MagicMock(); app.chest_full_lang_var.get.return_value = False

    app.toggle_chest_recognition()

    assert captured["collect"] is False
    assert captured["running_during"] is True       # пока идёт — «СТАРТ» занят
    assert captured["abort_flag"]() is False        # флаг свежий
    assert app._chest_running is False              # по завершении снова свободно


def test_button_does_nothing_when_idle_and_queue_empty(monkeypatch):
    import chest_reader
    _pending(monkeypatch, 0)
    called = []
    monkeypatch.setattr(chest_reader, "collect_chests", lambda *a, **k: called.append(1))
    app = _app(running=False)
    app._other_automation_running = lambda exclude=None: False
    app.toggle_chest_recognition()
    assert not called and app._chest_running is False


def test_plain_stop_shows_stopping_immediately():
    app = _app()
    app.toggle_chest_bot()
    assert app._chest_stop_event.is_set() and not app._chest_abort_event.is_set()
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_stopping"]


def test_done_after_abort_shows_plain_stopped_without_hints(monkeypatch):
    _pending(monkeypatch, 120)
    app = _app()
    app._on_chest_collection_done({"counts": {}, "aborted": True})
    text = app.chest_status_label.configure.call_args.kwargs["text"]
    assert text == LANGS["RU"]["chest_status_stopped"]
    assert app._chest_running is False


def test_texts_all_languages_no_icon_no_hint():
    for code in LANGS:
        for key in ("chest_abort_btn", "chest_recognize_btn", "chest_stopping"):
            assert LANGS[code].get(key), (code, key)
        assert "⛔" not in LANGS[code]["chest_abort_btn"], code
        assert "chest_aborted" not in LANGS[code], code


def test_start_after_abort_uses_fresh_events(monkeypatch):
    """Регрессия 2026-11-14 (живой лог владельца): после экстренной остановки флаг abort оставался
    взведённым, и каждый следующий «СТАРТ» сразу прерывался (reason=abort, кадров=0)."""
    import chest_reader
    captured = {}
    monkeypatch.setattr(chest_reader, "grab_fullscreen", lambda: object())
    monkeypatch.setattr(chest_reader, "detect_dialog_bbox", lambda f: (0, 0, 10, 10))
    monkeypatch.setattr(chest_reader, "init_db", lambda *a, **k: MagicMock())
    monkeypatch.setattr(chest_reader, "get_unsynced_counts", lambda c: {})
    _pending(monkeypatch, 0)

    def fake_collect(stop_flag, **kw):
        captured["abort_set_at_start"] = kw["abort_flag"]()
        captured["stop_set_at_start"] = stop_flag()
        return {"counts": {}, "items": []}
    monkeypatch.setattr(chest_reader, "collect_chests", fake_collect)
    monkeypatch.setattr(_main_module.threading, "Thread", _SyncThread)

    app = _app(running=False)
    app.after = lambda ms, fn=None, *a: None
    app.chest_kingdom_entry = MagicMock(); app.chest_kingdom_entry.get.return_value = "K"
    app.chest_clan_entry = MagicMock(); app.chest_clan_entry.get.return_value = "C"
    app._other_automation_running = lambda exclude=None: False
    app.chest_speed_slider = MagicMock(); app.chest_speed_slider.get.return_value = 0.5
    app.chest_full_lang_var = MagicMock(); app.chest_full_lang_var.get.return_value = False
    app.chest_auto_send_var = MagicMock(); app.chest_auto_send_var.get.return_value = False

    app._chest_abort_event.set()
    app._chest_stop_event.set()
    app.toggle_chest_bot()

    assert captured["abort_set_at_start"] is False
    assert captured["stop_set_at_start"] is False
