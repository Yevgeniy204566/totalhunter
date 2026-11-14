"""Сессия #167: самопроверка OCR при «Старт» (бот, распакованный в неудачное место / Tesseract заблокирован
антивирусом, раньше молча копил очередь), статус «распознавание не работает» и защита от утечек за
много циклов Старт/Стоп."""
import os
import threading
from unittest.mock import MagicMock

import cv2
import numpy as np

import chest_reader as cr
import main as _main_module
from main import LANGS

App = _main_module.TotalHunterApp


# ── selfcheck_ocr ─────────────────────────────────────────────────────────────────────────

def test_selfcheck_real_tesseract_ok():
    res = cr.selfcheck_ocr()
    assert res["ok"] is True, res
    assert 0 <= res["seconds"] < 8


def test_selfcheck_reports_failure_with_exception_type(monkeypatch):
    def boom(*a, **k):
        raise cr.pytesseract.TesseractNotFoundError()
    monkeypatch.setattr(cr.pytesseract, "image_to_string", boom)
    res = cr.selfcheck_ocr()
    assert res["ok"] is False and "TesseractNotFoundError" in res["error"]


def test_selfcheck_uses_the_language_set_the_run_will_use(monkeypatch):
    seen = []
    monkeypatch.setattr(cr.pytesseract, "image_to_string",
                        lambda image, config, lang, timeout: seen.append(lang) or "x")
    cr.selfcheck_ocr(full_lang=False)
    cr.selfcheck_ocr(full_lang=True)
    assert seen == [cr.LIGHT_SENDER_OCR_LANG, cr.FULL_SENDER_OCR_LANG]


# ── GUI: «Старт» и «Запустить распознавание» не стартуют при сломанном OCR ────────────────────

class _SyncThread:
    def __init__(self, target=None, daemon=None, **kw): self._t = target
    def start(self): self._t()


def _app(running=False):
    app = App.__new__(App)
    app.current_lang = "RU"
    app._chest_running = running
    app._chest_stop_event = threading.Event()
    app._chest_abort_event = threading.Event()
    for name in ("chest_status_label", "chest_start_btn", "chest_send_btn", "_chest_delete_batch_btn",
                 "chest_recog_btn", "chest_sent_label", "chest_sent_value_lb", "chest_time_label", "chest_speed_slider",
                 "chest_full_lang_var", "chest_auto_send_var"):
        setattr(app, name, MagicMock())
    app.chest_speed_slider.get.return_value = 0.5
    app.chest_full_lang_var.get.return_value = False
    app.chest_auto_send_var.get.return_value = False
    app._update_chest_counts_display = MagicMock()
    app._refresh_chest_queue = MagicMock()
    app._other_automation_running = lambda exclude=None: False
    app.after = lambda ms, fn=None, *a: fn() if (fn and ms == 0) else None
    app.chest_kingdom_entry = MagicMock(); app.chest_kingdom_entry.get.return_value = "K"
    app.chest_clan_entry = MagicMock(); app.chest_clan_entry.get.return_value = "C"
    app._chest_elapsed = 0.0
    app._chest_t0 = None
    app._chest_timer_job = None
    app._chest_last_progress = None
    app._chest_stalled = False
    return app


def _broken_ocr(monkeypatch, tmp_path):
    import chest_log
    monkeypatch.setattr(chest_log, "_default_log_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cr, "selfcheck_ocr", lambda full_lang=False: {"ok": False, "seconds": 0.1,
                                                                    "error": "TesseractNotFoundError: x"})
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: object())
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda f: (0, 0, 10, 10))
    monkeypatch.setattr(cr, "init_db", lambda *a, **k: MagicMock())
    monkeypatch.setattr(cr, "get_unsynced_counts", lambda c: {})
    called = []
    monkeypatch.setattr(cr, "collect_chests", lambda *a, **k: called.append(1))
    monkeypatch.setattr(_main_module.threading, "Thread", _SyncThread)
    return called


def test_start_refuses_when_ocr_broken(monkeypatch, tmp_path):
    called = _broken_ocr(monkeypatch, tmp_path)
    app = _app()
    app.toggle_chest_bot()
    assert not called and app._chest_running is False
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_ocr_broken"]


def test_recognition_button_refuses_when_ocr_broken(monkeypatch, tmp_path):
    called = _broken_ocr(monkeypatch, tmp_path)
    monkeypatch.setattr(cr, "count_pending", lambda *a, **k: 10)
    app = _app()
    app.toggle_chest_recognition()
    assert not called and app._chest_running is False
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_ocr_broken"]


# ── «распознавание не работает»: очередь растёт, записей нет ──────────────────────────────────

def _stall_app(monkeypatch, pending, idle_s):
    app = _app(running=True)
    clock = {"t": 1000.0}
    monkeypatch.setattr(_main_module.time, "monotonic", lambda: clock["t"])
    app._chest_t0 = 1000.0
    app._chest_last_progress = clock["t"] - idle_s
    monkeypatch.setattr(cr, "count_pending", lambda *a, **k: pending)
    app.after = lambda ms, fn=None, *a: "job"
    return app


def test_stall_status_shown_when_queue_grows_without_records(monkeypatch):
    app = _stall_app(monkeypatch, pending=40, idle_s=61)
    app._check_chest_stall()
    assert app._chest_stalled is True
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_stalled"]


def test_no_stall_when_queue_small(monkeypatch):
    app = _stall_app(monkeypatch, pending=10, idle_s=300)
    app._check_chest_stall()
    assert app._chest_stalled is False


def test_no_stall_when_recent_progress(monkeypatch):
    app = _stall_app(monkeypatch, pending=500, idle_s=20)
    app._check_chest_stall()
    assert app._chest_stalled is False


def test_stall_status_cleared_when_recognition_resumes():
    app = _app(running=True)
    app._chest_stalled = True
    app._note_chest_progress()
    assert app._chest_stalled is False
    assert app.chest_status_label.configure.call_args.kwargs["text"] == LANGS["RU"]["chest_status_running"]


def test_texts_in_all_languages():
    for code in LANGS:
        for key in ("chest_ocr_broken", "chest_stalled"):
            assert LANGS[code].get(key), (code, key)


# ── утечки: много циклов Старт/Стоп не копят потоки и файлы ─────────────────────────────────

def test_twenty_start_stop_cycles_leave_no_threads_or_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "find_open_button", lambda bbox, dialog: (10, 10))
    monkeypatch.setattr(cr, "crop_top_row", lambda frame: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "click_open_button", lambda pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)
    monkeypatch.setattr(cr, "ocr_top_row_crops", lambda combined, full_lang=False: ("Тип", "Игрок"))
    baseline = threading.active_count()
    db = str(tmp_path / "b.db")
    pend = str(tmp_path / "p")
    for _ in range(20):
        n = {"i": 0}

        def stop():
            n["i"] += 1
            return n["i"] > 3
        cr.collect_chests(stop, db_path=db, pending_dir=pend, pause_range=(0, 0))
    assert threading.active_count() <= baseline
    assert cr.count_pending(pend) == 0
    conn = cr.init_db(db)
    assert sum(cr.get_unsynced_counts(conn).values()) > 0
    conn.close()
    leftovers = [n for n in os.listdir(pend) if not n.endswith(".png")]
    assert leftovers == []        # служебные .pair-файлы чистятся
