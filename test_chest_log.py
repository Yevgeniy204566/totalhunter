"""Лог сбора сундуков (сессия #167, владелец 2026-11-14): после нескольких Старт/Стоп сбор/отправка
молча не работали, а следов не было. Файл logs/chest_*.log + ограниченная отправка ключевых
событий на сервер (/log_error). Лог никогда не должен ронять сбор."""
import os

import chest_log


def test_start_run_creates_file_and_writes_lines(tmp_path):
    chest_log.start_run(log_dir=str(tmp_path))
    chest_log.log("INFO", "старт")
    files = [n for n in os.listdir(tmp_path) if n.startswith("chest_") and n.endswith(".log")]
    assert len(files) == 1
    text = open(tmp_path / files[0], encoding="utf-8").read()
    assert "[INFO] старт" in text


def test_log_without_start_run_does_not_raise():
    chest_log._state["file"] = None
    chest_log.log("INFO", "никуда")   # не падает


def test_log_exc_writes_traceback(tmp_path):
    chest_log.start_run(log_dir=str(tmp_path))
    try:
        raise ValueError("boom")
    except ValueError:
        chest_log.log_exc("сбой OCR")
    text = open(chest_log.current_file(), encoding="utf-8").read()
    assert "сбой OCR" in text and "ValueError: boom" in text and "Traceback" in text


def test_old_logs_are_rotated(tmp_path):
    for i in range(15):
        (tmp_path / f"chest_20260101_0000{i:02d}.log").write_text("x")
    chest_log.start_run(log_dir=str(tmp_path))
    files = [n for n in os.listdir(tmp_path) if n.startswith("chest_")]
    assert len(files) <= chest_log.KEEP_LOGS


def test_report_sends_to_server_and_is_rate_limited(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(chest_log, "_send_to_server", lambda text: sent.append(text))
    monkeypatch.setattr(chest_log, "_spawn", lambda fn, *a: fn(*a))
    chest_log.start_run(log_dir=str(tmp_path))
    for i in range(chest_log.SERVER_REPORT_LIMIT + 10):
        chest_log.report(f"событие {i}")
    assert len(sent) == chest_log.SERVER_REPORT_LIMIT
    assert sent[0].startswith("chest: ")
    # каждое событие при этом остаётся в файле
    text = open(chest_log.current_file(), encoding="utf-8").read()
    assert f"событие {chest_log.SERVER_REPORT_LIMIT + 9}" in text


def test_report_limit_resets_on_new_run(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(chest_log, "_send_to_server", lambda text: sent.append(text))
    monkeypatch.setattr(chest_log, "_spawn", lambda fn, *a: fn(*a))
    chest_log.start_run(log_dir=str(tmp_path))
    for i in range(chest_log.SERVER_REPORT_LIMIT):
        chest_log.report("a")
    chest_log.start_run(log_dir=str(tmp_path))
    chest_log.report("b")
    assert sent[-1] == "chest: b"


def test_unwritable_dir_does_not_raise(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    chest_log.start_run(log_dir=str(blocker / "sub"))   # путь внутри файла — создать нельзя
    chest_log.log("INFO", "ок")                           # молча игнорируется
