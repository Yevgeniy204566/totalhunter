"""Сессия 2026-11-14, жалобы владельца:
1) после «Стоп» → «Запустить распознавание» при включённой автоотправке батч не уходил сам
   (в логе: «вышел штатно, распознано 79» и тишина до ручного «Отправить»);
2) таймер сбора справа от «Отправлено»: идёт, пока работает сбор/распознавание, на остановке
   стоит, при отправке батча сбрасывается."""
import os
import threading

import pytest
from unittest.mock import MagicMock

import cv2
import numpy as np

import chest_reader as cr
import main as _main_module
from main import LANGS

App = _main_module.TotalHunterApp


@pytest.fixture(autouse=True)
def _ocr_selfcheck_ok(monkeypatch):
    import chest_reader
    monkeypatch.setattr(chest_reader, "selfcheck_ocr",
                        lambda full_lang=False: {"ok": True, "seconds": 0.1, "error": None})
    yield


def _write_crops(pending_dir, n):
    os.makedirs(pending_dir, exist_ok=True)
    for i in range(1, n + 1):
        cv2.imwrite(os.path.join(pending_dir, cr._crop_name("20260101000000000000", i)),
                    np.zeros((10, 10, 3), dtype=np.uint8))


# ── chest_reader: распознавание очереди сообщает «готово» ─────────────────────────────────

def test_recognition_only_calls_batch_ready_when_done(tmp_path, monkeypatch):
    _write_crops(str(tmp_path / "p"), 2)
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda combined, full_lang=False: ("Тип", "Игрок"))
    got = []
    cr.collect_chests(lambda: False, db_path=str(tmp_path / "b.db"), pending_dir=str(tmp_path / "p"),
                      collect=False, on_batch_ready=got.append)
    assert got == ["recognized"]


def test_recognition_only_aborted_does_not_call_batch_ready(tmp_path, monkeypatch):
    _write_crops(str(tmp_path / "p"), 2)
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda combined, full_lang=False: ("Тип", "Игрок"))
    got = []
    result = cr.collect_chests(lambda: True, db_path=str(tmp_path / "b.db"), pending_dir=str(tmp_path / "p"),
                               collect=False, abort_flag=lambda: True, on_batch_ready=got.append)
    assert got == [] and result["aborted"] is True


def test_recognition_only_with_dead_consumer_does_not_send(tmp_path, monkeypatch):
    _write_crops(str(tmp_path / "p"), cr.CONSUMER_MAX_FAILS + 1)

    def boom(combined, full_lang=False):
        raise RuntimeError("dead")
    monkeypatch.setattr(cr, "ocr_top_row_crops", boom)
    got = []
    result = cr.collect_chests(lambda: False, db_path=str(tmp_path / "b.db"), pending_dir=str(tmp_path / "p"),
                               collect=False, on_batch_ready=got.append)
    assert got == [] and "error" in result


# ── GUI: автоотправка после распознавания ─────────────────────────────────────────────────

class _SyncThread:
    def __init__(self, target=None, daemon=None, **kw): self._t = target
    def start(self): self._t()


def _app():
    app = App.__new__(App)
    app.current_lang = "RU"
    app._chest_running = False
    app._chest_stop_event = threading.Event()
    app._chest_abort_event = threading.Event()
    for name in ("chest_status_label", "chest_start_btn", "chest_send_btn", "_chest_delete_batch_btn",
                 "chest_recog_btn", "chest_sent_label", "chest_time_label"):
        setattr(app, name, MagicMock())
    app._update_chest_counts_display = MagicMock()
    app._refresh_chest_queue = MagicMock()
    app._other_automation_running = lambda exclude=None: False
    app.after = lambda ms, fn=None, *a: fn() if (fn and ms == 0) else None   # тики таймера (1000 мс) не гоняем
    app._chest_elapsed = 0.0
    app._chest_t0 = None
    app._chest_timer_job = None
    app._chest_last_progress = None
    app._chest_stalled = False
    app._chest_selfcheck_note = None
    app.chest_kingdom_entry = MagicMock(); app.chest_kingdom_entry.get.return_value = "K"
    app.chest_clan_entry = MagicMock(); app.chest_clan_entry.get.return_value = "C"
    app.chest_full_lang_var = MagicMock(); app.chest_full_lang_var.get.return_value = False
    app._chest_last_sent = None
    return app


def _run_recognition(monkeypatch, auto_send, send_result):
    monkeypatch.setattr(cr, "count_pending", lambda *a, **k: 5)

    def fake_collect(stop_flag, **kw):
        kw["on_batch_ready"]("recognized")
        return {"counts": {}, "items": []}
    monkeypatch.setattr(cr, "collect_chests", fake_collect)
    monkeypatch.setattr(_main_module.threading, "Thread", _SyncThread)
    app = _app()
    app.chest_auto_send_var = MagicMock(); app.chest_auto_send_var.get.return_value = auto_send
    app._send_chest_batch = MagicMock(return_value=send_result)
    app.toggle_chest_recognition()
    return app


def test_recognition_run_auto_sends_batch_when_toggle_on(monkeypatch):
    app = _run_recognition(monkeypatch, True, {"success": True, "sent": 421})
    app._send_chest_batch.assert_called_once()
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_send_success"]
    assert app._chest_last_sent == 421


def test_recognition_run_does_not_send_when_toggle_off(monkeypatch):
    app = _run_recognition(monkeypatch, False, {"success": True, "sent": 1})
    app._send_chest_batch.assert_not_called()


# ── Таймер сбора ──────────────────────────────────────────────────────────────────────────

def test_format_elapsed():
    assert App._fmt_elapsed(0) == "0:00:00"
    assert App._fmt_elapsed(75) == "0:01:15"
    assert App._fmt_elapsed(3725.9) == "1:02:05"
    assert App._fmt_elapsed(-5) == "0:00:00"


def _timer_app(monkeypatch):
    app = _app()
    app._chest_elapsed = 0.0
    app._chest_t0 = None
    app._chest_timer_job = None
    clock = {"t": 1000.0}
    monkeypatch.setattr(_main_module.time, "monotonic", lambda: clock["t"])
    app.after = lambda ms, fn=None, *a: "job"
    app.after_cancel = lambda job: None
    return app, clock


def test_timer_runs_stops_and_accumulates(monkeypatch):
    app, clock = _timer_app(monkeypatch)
    app._chest_timer_start()
    clock["t"] += 90
    assert app._chest_elapsed_now() == 90
    app._chest_timer_stop()
    clock["t"] += 500                      # пауза — время стоит
    assert app._chest_elapsed_now() == 90
    app._chest_timer_start()
    clock["t"] += 30
    assert app._chest_elapsed_now() == 120
    assert app.chest_time_label.configure.called


def test_timer_resets_on_batch_sent_and_keeps_running(monkeypatch):
    app, clock = _timer_app(monkeypatch)
    app._chest_timer_start()
    clock["t"] += 100
    app._chest_timer_reset()
    assert app._chest_elapsed_now() == 0
    clock["t"] += 10                       # сбор продолжается следующей порцией
    assert app._chest_elapsed_now() == 10


def test_successful_send_resets_timer(monkeypatch):
    app, clock = _timer_app(monkeypatch)
    app._chest_timer_start()
    clock["t"] += 100
    app._reset_timer_after_send({"success": True, "sent": 5})
    assert app._chest_elapsed_now() == 0


def test_failed_or_empty_send_keeps_timer(monkeypatch):
    app, clock = _timer_app(monkeypatch)
    app._chest_timer_start()
    clock["t"] += 100
    app._reset_timer_after_send({"success": False})
    app._reset_timer_after_send({"success": True, "empty": True})
    assert app._chest_elapsed_now() == 100
