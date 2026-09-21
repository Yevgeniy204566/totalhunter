"""Кнопка «Очистить очередь» и упрощение панели (сессия #148, решения владельца 2026-09-21):

- «Очистить очередь» удаляет ВСЕ скрины из очереди (pending), включая подпапки;
- находки в debug-Telegram идут ВСЕГДА (для отладки и статистики) — переключателя нет;
- публикация в РОЙ — без переключателя: пока константа выключена (сегодня ничего не выпускаем, под РОЙ нужны
  новые таблицы), при выпуске версии включается одной правкой."""

import os
import time
from unittest.mock import MagicMock

import cv2
import numpy as np

import exchange_mode_settings
from exchange_scout import ExchangeScoutEngine, clear_queue_dir, count_queue, list_queue


def write_png(path, size=10):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, np.zeros((size, size, 3), np.uint8))


def wait_for(cond, timeout=4.0):
    end = time.time() + timeout
    while time.time() < end and not cond():
        time.sleep(0.02)
    return cond()


class TestClearQueueDir:
    def test_removes_every_screenshot_and_reports_the_count(self, tmp_path):
        pending = tmp_path / "pending"
        write_png(str(pending / "a.jpg"))
        write_png(str(pending / "b.png"))
        write_png(str(pending / "old_session" / "c.jpg"))
        assert clear_queue_dir(str(pending)) == 3
        assert count_queue(str(pending)) == 0

    def test_root_folder_stays_and_empty_subfolders_go(self, tmp_path):
        pending = tmp_path / "pending"
        write_png(str(pending / "sub" / "x.png"))
        clear_queue_dir(str(pending))
        assert pending.is_dir() and os.listdir(pending) == []

    def test_leftover_tmp_files_are_removed_too(self, tmp_path):
        pending = tmp_path / "pending"
        pending.mkdir()
        (pending / "half.tmp").write_bytes(b"x")
        clear_queue_dir(str(pending))
        assert os.listdir(pending) == []

    def test_does_not_touch_found(self, tmp_path):
        write_png(str(tmp_path / "pending" / "a.jpg"))
        write_png(str(tmp_path / "found" / "keep.png"))
        clear_queue_dir(str(tmp_path / "pending"))
        assert (tmp_path / "found" / "keep.png").exists()

    def test_missing_folder_is_zero(self, tmp_path):
        assert clear_queue_dir(str(tmp_path / "nope")) == 0

    def test_empty_queue_is_zero(self, tmp_path):
        (tmp_path / "pending").mkdir()
        assert clear_queue_dir(str(tmp_path / "pending")) == 0


class TestEngineClearQueue:
    def _engine(self, tmp_path, **kw):
        kw.setdefault("move_wait", 0.01)
        return ExchangeScoutEngine(
            navigator=MagicMock(), capture_fn=lambda: np.zeros((40, 40, 3), np.uint8),
            model=MagicMock(), conf=0.8, sessions_root=str(tmp_path), **kw)

    def test_clear_queue_empties_it(self, tmp_path):
        engine = self._engine(tmp_path)
        for i in range(5):
            write_png(str(tmp_path / "pending" / f"{i}.png"))
        assert engine.clear_queue() == 5
        assert engine.queue_size() == 0

    def test_paused_snake_resumes_after_the_queue_is_cleared(self, tmp_path):
        engine = self._engine(tmp_path, pause_threshold=20, pause_seconds=60)
        engine.start()
        engine.stop_consumer()
        assert wait_for(lambda: engine.paused_by_queue)
        engine.clear_queue()
        assert wait_for(lambda: not engine.paused_by_queue, timeout=2)     # очередь пуста — не ждём 3 минуты
        engine.stop()

    def test_running_neural_net_survives_a_clear(self, tmp_path):
        """Кадр, который нейросеть уже взяла, может исчезнуть из-под неё — это не должно ронять поток."""
        model = MagicMock()
        model.predict.return_value = [MagicMock(boxes=[])]
        engine = self._engine(tmp_path)
        engine.model = model
        engine.start()
        time.sleep(0.2)
        engine.clear_queue()
        time.sleep(0.3)
        assert engine.consumer_alive is True and engine.producer_error is None
        engine.stop()


class TestSimplifiedPanelSettings:
    def test_roy_publishing_is_off_for_now_and_is_a_single_constant(self):
        assert exchange_mode_settings.SCOUT_PUBLISH_TO_ROY is False

    def test_switch_helpers_are_gone(self):
        assert not hasattr(exchange_mode_settings, "scout_debug_default")
        assert not hasattr(exchange_mode_settings, "scout_roy_publish_default")

    def test_clear_button_text_in_every_language(self):
        for lang in ("RU", "UK", "EN"):
            assert exchange_mode_settings.scout_text(lang, "clear_queue")

    def test_switch_texts_are_gone(self):
        for lang in ("RU", "UK", "EN"):
            assert "debug_tg" not in exchange_mode_settings._TEXTS[lang]
            assert "roy_publish" not in exchange_mode_settings._TEXTS[lang]
