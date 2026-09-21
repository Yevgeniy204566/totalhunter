"""Цепочка после находки в Бирже 2.0 (сессия #148, разбор «скрины с биржами не дали ни сигнала, ни
координат в РОЙ»): нейросеть находила биржу на всех 8 скринах, но
  1) область чтения координат (экранные пиксели, 2560x1440) применялась к скринам 1920x1080 и лежала
     ЗА пределами картинки -> координаты не читались -> в РОЙ ничего;
  2) звука находки в 2.0 не было вообще;
  3) результат обработки нигде не фиксировался, а исключение в обработчике молча убивало consumer."""

import json
import os
import time
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

import exchange_scout
from exchange_scout import (
    ExchangeScoutEngine, make_found_handler, scale_crop_box, append_result_journal, cleanup_expired,
)


def write_png(path, size=20):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, np.zeros((size, size, 3), np.uint8))


def wait_for(cond, timeout=4.0):
    end = time.time() + timeout
    while time.time() < end and not cond():
        time.sleep(0.02)
    return cond()


class TestScaleCropBox:
    def test_same_resolution_is_unchanged(self):
        assert scale_crop_box((5, 1366, 235, 1404), (2560, 1440), (1440, 2560, 3)) == (5, 1366, 235, 1404)

    def test_1080p_frame_from_1440p_screen_is_scaled_into_the_image(self):
        box = scale_crop_box((5, 1366, 235, 1404), (2560, 1440), (1080, 1920, 3))
        assert box == (4, 1024, 176, 1053)          # реальный случай: 8 скринов владельца
        x1, y1, x2, y2 = box
        assert 0 <= x1 < x2 <= 1920 and 0 <= y1 < y2 <= 1080

    def test_box_never_leaves_the_frame(self):
        x1, y1, x2, y2 = scale_crop_box((0, 0, 9999, 9999), (1920, 1080), (720, 1280, 3))
        assert (x1, y1) == (0, 0) and x2 <= 1280 and y2 <= 720

    def test_bad_screen_size_leaves_box_as_is(self):
        assert scale_crop_box((1, 2, 3, 4), (0, 0), (100, 100, 3)) == (1, 2, 3, 4)


class TestFoundHandler:
    def _handler(self, monkeypatch, coords=(512, 318), screen=(2560, 1440), **kw):
        seen = {}

        def fake_read(frame, crop_box):
            seen["crop"] = crop_box
            return coords

        monkeypatch.setattr(exchange_scout, "read_exchange_coords", fake_read)
        spend = MagicMock(return_value={"success": True, "credits": 90})
        roy = MagicMock()
        roy.report_scout_find.return_value = True
        h = make_found_handler((5, 1366, 235, 1404), 7, "exchange", "hw", spend_fn=spend, roy_client=roy,
                               screen_size=screen, **kw)
        return h, seen, spend, roy

    def test_crop_is_scaled_to_the_frame_resolution(self, monkeypatch):
        h, seen, _s, _r = self._handler(monkeypatch)
        h(np.zeros((1080, 1920, 3), np.uint8), "x.png")
        assert seen["crop"] == (4, 1024, 176, 1053)

    def test_sound_plays_first_even_when_coordinates_are_not_read(self, monkeypatch):
        order = []
        h, _seen, spend, _r = self._handler(monkeypatch, coords=None, on_sound=lambda: order.append("sound"))
        spend.side_effect = lambda *_a: order.append("spend") or {"success": True}
        h(np.zeros((1080, 1920, 3), np.uint8), "x.png")
        assert order == ["sound", "spend"]

    def test_broken_sound_does_not_break_the_chain(self, monkeypatch):
        def boom():
            raise RuntimeError("no audio device")

        h, _seen, spend, roy = self._handler(monkeypatch, on_sound=boom)
        result = h(np.zeros((1080, 1920, 3), np.uint8), "x.png")
        assert result["published"] is True
        spend.assert_called_once_with("exchange")

    def test_on_result_receives_kingdom_and_result(self, monkeypatch):
        got = []
        h, _seen, _s, _r = self._handler(monkeypatch, on_result=lambda k, r: got.append((k, r)))
        h(np.zeros((1080, 1920, 3), np.uint8), "x.png")
        assert got[0][0] == 7 and got[0][1]["x"] == 512 and got[0][1]["published"] is True

    def test_returns_the_result_dict(self, monkeypatch):
        h, _seen, _s, _r = self._handler(monkeypatch)
        r = h(np.zeros((1080, 1920, 3), np.uint8), "x.png")
        assert r == {"coords_ok": True, "x": 512, "y": 318, "charged": True, "published": True}


class TestResultJournalAndConsumerSafety:
    def _engine(self, tmp_path, cb):
        model = MagicMock()
        model.predict.return_value = [MagicMock(boxes=[MagicMock()])]      # биржа есть на каждом кадре
        return ExchangeScoutEngine(
            navigator=MagicMock(), capture_fn=lambda: np.zeros((40, 40, 3), np.uint8), model=model,
            conf=0.8, sessions_root=str(tmp_path), move_wait=0.01, on_found_callback=cb)

    def _journal(self, tmp_path):
        path = tmp_path / "scout_results.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_result_of_each_find_is_journaled(self, tmp_path):
        engine = self._engine(tmp_path, lambda f, p: {"coords_ok": True, "x": 5, "y": 6,
                                                      "charged": True, "published": True})
        write_png(str(tmp_path / "pending" / "a.png"))
        engine.start_consumer()
        assert wait_for(lambda: len(self._journal(tmp_path)) == 1)
        row = self._journal(tmp_path)[0]
        assert row["file"] == "a.png" and row["x"] == 5 and row["y"] == 6
        assert row["charged"] is True and row["published"] is True and "ts" in row

    def test_exception_in_handler_does_not_kill_the_consumer_and_is_journaled(self, tmp_path):
        calls = []

        def cb(frame, path):
            calls.append(os.path.basename(path))
            if len(calls) == 1:
                raise RuntimeError("OCR exploded")
            return {"coords_ok": True, "x": 1, "y": 2, "charged": True, "published": True}

        engine = self._engine(tmp_path, cb)
        write_png(str(tmp_path / "pending" / "a.png"))
        time.sleep(0.05)
        write_png(str(tmp_path / "pending" / "b.png"))
        engine.start_consumer()
        assert wait_for(lambda: len(self._journal(tmp_path)) == 2)
        rows = self._journal(tmp_path)
        assert "OCR exploded" in rows[0]["error"]
        assert rows[1]["x"] == 1
        assert engine.queue_size() == 0        # второй кадр обработан — consumer жив

    def test_journal_survives_the_ttl_cleanup(self, tmp_path):
        append_result_journal(str(tmp_path), {"file": "x"})
        (tmp_path / "pending").mkdir()
        cleanup_expired(str(tmp_path), now=time.time() + 10 ** 6)
        assert (tmp_path / "scout_results.jsonl").exists()


class TestDebugTelegramHooks:
    """Владелец 2026-09-21: скрины с биржами параллельно уходят в его debug-Telegram; звук и списание
    10◆ идут как обычно. Хуки необязательны и их сбои цепочку не ломают."""

    def _handler(self, monkeypatch, **kw):
        monkeypatch.setattr(exchange_scout, "read_exchange_coords", lambda f, c: (512, 318))
        spend = MagicMock(return_value={"success": True})
        roy = MagicMock()
        roy.report_scout_find.return_value = True
        return make_found_handler((5, 1366, 235, 1404), 7, "exchange", "hw", spend_fn=spend,
                                  roy_client=roy, screen_size=(2560, 1440), **kw), spend, roy

    def test_frame_goes_out_first_then_sound_spend_and_result(self, monkeypatch):
        order = []
        h, spend, _roy = self._handler(
            monkeypatch, on_sound=lambda: order.append("sound"),
            on_debug_frame=lambda fr: order.append("debug_frame"),
            on_debug_result=lambda name, r: order.append(("debug_result", name, r["x"])))
        spend.side_effect = lambda *_a: order.append("spend") or {"success": True}
        h(np.zeros((1080, 1920, 3), np.uint8), os.path.join("found", "s1.png"))
        assert order == ["sound", "debug_frame", "spend", ("debug_result", "s1.png", 512)]

    def test_spend_10_diamonds_path_is_unchanged_by_debug_hooks(self, monkeypatch):
        h, spend, roy = self._handler(monkeypatch, on_debug_frame=lambda fr: None,
                                      on_debug_result=lambda n, r: None)
        r = h(np.zeros((1080, 1920, 3), np.uint8), "s.png")
        spend.assert_called_once_with("exchange")
        assert r["charged"] is True and r["published"] is True

    def test_broken_debug_hooks_do_not_break_sound_spend_or_publish(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("telegram down")

        played = []
        h, spend, roy = self._handler(monkeypatch, on_sound=lambda: played.append(1),
                                      on_debug_frame=boom, on_debug_result=boom)
        r = h(np.zeros((1080, 1920, 3), np.uint8), "s.png")
        assert played == [1] and r["published"] is True
        spend.assert_called_once_with("exchange")

    def test_hooks_are_optional(self, monkeypatch):
        h, _s, _r = self._handler(monkeypatch)
        assert h(np.zeros((1080, 1920, 3), np.uint8), "s.png")["published"] is True


class TestDebugReporterMessage:
    def test_message_for_full_success(self):
        from debug_reporter import scout_result_message
        msg = scout_result_message("a.png", {"coords_ok": True, "x": 316, "y": 924,
                                             "charged": True, "published": True})
        assert "a.png" in msg and "X:316" in msg and "Y:924" in msg
        assert "списано 10◆" in msg and "отправлено в РОЙ" in msg

    def test_message_when_coordinates_not_read(self):
        from debug_reporter import scout_result_message
        msg = scout_result_message("b.png", {"coords_ok": False, "x": None, "y": None,
                                             "charged": True, "published": False})
        assert "координаты не прочитаны" in msg and "в РОЙ не отправлено" in msg

    def test_message_for_handler_error(self):
        from debug_reporter import scout_result_message
        msg = scout_result_message("c.png", {"error": "RuntimeError: boom"})
        assert "Ошибка обработки" in msg and "boom" in msg

    def test_report_functions_never_block_or_raise(self, monkeypatch):
        import debug_reporter
        monkeypatch.setattr(debug_reporter.requests, "post",
                            lambda *a, **k: (_ for _ in ()).throw(ConnectionError("offline")))
        debug_reporter.report_scout_frame("hw", np.zeros((10, 10, 3), np.uint8))
        debug_reporter.report_scout_result("hw", "a.png", {"coords_ok": False})
