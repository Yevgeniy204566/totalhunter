"""Единая очередь Биржи 2.0 (сессия #148, решения владельца 2026-09-21):

- все кадры и все скрины, которые кладёт пользователь, лежат в ОДНОЙ папке pending/ и разбираются по
  времени добавления (старые первыми); нет папок «на сессию», очередь не обнуляется новым запуском;
- нейросеть одна, независимая от змейки: «остановить» реально её останавливает, «запустить» работает
  и без змейки (можно гонять свои скрины);
- очередь заполнилась (порог) — змейка сама встаёт на паузу, при спаде до 10% продолжает;
- ВСЁ старше 30 минут удаляется вместе с опустевшими папками — мусор не копится."""

import os
import time
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from exchange_scout import (
    ExchangeScoutEngine, list_queue, count_queue, cleanup_expired,
    QUEUE_TTL_SEC, IMAGE_EXTS, generate_session_id,
)
from exchange_mode_settings import SCOUT_QUEUE_PAUSE_THRESHOLD, SCOUT_QUEUE_RESUME_THRESHOLD


def write_img(path, size=10, ext=None):
    """Пишет реальную картинку size x size (размер = метка кадра в тестах порядка)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = np.zeros((size, size, 3), dtype=np.uint8)
    ext = ext or os.path.splitext(path)[1]
    ok, enc = cv2.imencode(ext, img)
    assert ok
    with open(path, "wb") as f:
        f.write(enc.tobytes())


def no_box_model():
    model = MagicMock()
    model.predict.return_value = [MagicMock(boxes=[])]
    return model


def make_engine(root, model=None, **kw):
    frame = np.zeros((40, 40, 3), dtype=np.uint8)
    kw.setdefault("move_wait", 0.01)
    return ExchangeScoutEngine(
        navigator=MagicMock(), capture_fn=lambda: frame, model=model or no_box_model(), conf=0.8,
        sessions_root=str(root), **kw)


def wait_for(cond, timeout=4.0):
    end = time.time() + timeout
    while time.time() < end and not cond():
        time.sleep(0.02)
    return cond()


class TestConstants:
    def test_pause_at_300_resume_at_10_percent(self):
        assert SCOUT_QUEUE_PAUSE_THRESHOLD == 300
        assert SCOUT_QUEUE_RESUME_THRESHOLD == 30

    def test_ttl_is_30_minutes(self):
        assert QUEUE_TTL_SEC == 30 * 60

    def test_png_and_jpg_are_accepted(self):
        assert {".jpg", ".jpeg", ".png"} <= set(IMAGE_EXTS)


class TestListQueue:
    def test_accepts_all_image_extensions_case_insensitive(self, tmp_path):
        for name in ("a.jpg", "b.JPEG", "c.png", "d.PNG", "e.bmp", "f.webp"):
            write_img(str(tmp_path / name))
        assert len(list_queue(str(tmp_path))) == 6

    def test_ignores_tmp_and_non_images(self, tmp_path):
        write_img(str(tmp_path / "ok.jpg"))
        (tmp_path / "half.tmp").write_bytes(b"x")
        (tmp_path / "notes.txt").write_text("x")
        assert [os.path.basename(p) for p in list_queue(str(tmp_path))] == ["ok.jpg"]

    def test_finds_files_in_subfolders(self, tmp_path):
        write_img(str(tmp_path / "old_session" / "x.png"))
        write_img(str(tmp_path / "top.jpg"))
        assert len(list_queue(str(tmp_path))) == 2

    def test_oldest_first_by_time_added_not_by_name(self, tmp_path):
        write_img(str(tmp_path / "z_first.png"))
        time.sleep(0.05)
        write_img(str(tmp_path / "a_second.png"))
        time.sleep(0.05)
        write_img(str(tmp_path / "m_third.jpg"))
        names = [os.path.basename(p) for p in list_queue(str(tmp_path))]
        assert names == ["z_first.png", "a_second.png", "m_third.jpg"]

    def test_missing_directory_is_empty(self, tmp_path):
        assert list_queue(str(tmp_path / "nope")) == []
        assert count_queue(str(tmp_path / "nope")) == 0


class TestCleanupExpired:
    def _root(self, tmp_path):
        for d in ("pending", "found", "errors"):
            (tmp_path / d).mkdir()
        return str(tmp_path)

    def test_fresh_files_are_kept(self, tmp_path):
        root = self._root(tmp_path)
        write_img(str(tmp_path / "pending" / "a.jpg"))
        cleanup_expired(root)
        assert (tmp_path / "pending" / "a.jpg").exists()

    def test_expired_files_deleted_in_pending_and_found(self, tmp_path):
        root = self._root(tmp_path)
        write_img(str(tmp_path / "pending" / "a.jpg"))
        write_img(str(tmp_path / "found" / "b.png"))
        cleanup_expired(root, now=time.time() + QUEUE_TTL_SEC + 5)
        assert not (tmp_path / "pending" / "a.jpg").exists()
        assert not (tmp_path / "found" / "b.png").exists()

    def test_expired_leftover_non_image_files_are_removed_too(self, tmp_path):
        root = self._root(tmp_path)
        (tmp_path / "pending" / "half.tmp").write_bytes(b"x")
        cleanup_expired(root, now=time.time() + QUEUE_TTL_SEC + 5)
        assert not (tmp_path / "pending" / "half.tmp").exists()

    def test_old_session_folder_removed_together_with_its_frames(self, tmp_path):
        root = self._root(tmp_path)
        write_img(str(tmp_path / "pending" / "2026-01-01_00-00-00_dead" / "000001.jpg"))
        (tmp_path / "found" / "2026-01-01_00-00-00_dead").mkdir()
        (tmp_path / "errors" / "2026-01-01_00-00-00_dead").mkdir()
        cleanup_expired(root, now=time.time() + QUEUE_TTL_SEC + 5)
        assert os.listdir(tmp_path / "pending") == []
        assert os.listdir(tmp_path / "found") == []
        assert os.listdir(tmp_path / "errors") == []

    def test_root_folders_themselves_survive(self, tmp_path):
        root = self._root(tmp_path)
        cleanup_expired(root, now=time.time() + QUEUE_TTL_SEC + 5)
        for d in ("pending", "found", "errors"):
            assert (tmp_path / d).is_dir()

    def test_folder_with_a_fresh_file_is_kept_even_if_folder_is_old(self, tmp_path):
        root = self._root(tmp_path)
        sub = tmp_path / "pending" / "old_session"
        sub.mkdir()
        time.sleep(0.4)
        write_img(str(sub / "fresh.png"))
        cleanup_expired(root, ttl_sec=0.2)
        assert (sub / "fresh.png").exists() and sub.is_dir()

    def test_returns_removed_counts(self, tmp_path):
        root = self._root(tmp_path)
        write_img(str(tmp_path / "pending" / "s" / "a.jpg"))
        write_img(str(tmp_path / "pending" / "s" / "b.jpg"))
        files, dirs = cleanup_expired(root, now=time.time() + QUEUE_TTL_SEC + 5)
        assert (files, dirs) == (2, 1)

    def test_missing_root_is_not_an_error(self, tmp_path):
        assert cleanup_expired(str(tmp_path / "nothing_here")) == (0, 0)


class TestEngineFlatQueue:
    def test_dirs_are_fixed_and_exist_before_any_start(self, tmp_path):
        engine = make_engine(tmp_path)
        assert engine.pending_dir == str(tmp_path / "pending")
        assert engine.found_dir == str(tmp_path / "found")
        assert os.path.isdir(engine.pending_dir) and os.path.isdir(engine.found_dir)

    def test_two_sessions_share_one_queue_and_nothing_resets(self, tmp_path):
        engine = make_engine(tmp_path)
        engine.start()
        engine.stop_consumer()
        assert wait_for(lambda: not engine.consumer_alive)
        assert wait_for(lambda: engine.queue_size() >= 3)
        engine.stop()
        first_size = engine.queue_size()
        first_sid = engine.sid
        engine.start()
        assert engine.sid != first_sid
        assert wait_for(lambda: engine.queue_size() > first_size)    # растёт поверх, не с нуля
        engine.stop()
        assert engine.pending_dir == str(tmp_path / "pending")

    def test_frame_names_carry_session_id_so_sessions_never_collide(self, tmp_path):
        engine = make_engine(tmp_path)
        engine.start()
        engine.stop_consumer()
        assert wait_for(lambda: engine.queue_size() >= 1)
        engine.stop()
        names = [os.path.basename(p) for p in list_queue(engine.pending_dir)]
        assert all(n.startswith(engine.sid + "_") for n in names)

    def test_queue_size_counts_user_dropped_files_and_subfolders(self, tmp_path):
        engine = make_engine(tmp_path)
        write_img(str(tmp_path / "pending" / "mine.png"))
        write_img(str(tmp_path / "pending" / "old" / "x.jpg"))
        assert engine.queue_size() == 2


class TestNeuralOnlyMode:
    def test_start_consumer_processes_user_dropped_png_without_snake(self, tmp_path):
        model = no_box_model()
        engine = make_engine(tmp_path, model=model)
        write_img(str(tmp_path / "pending" / "mine.png"))
        engine.start_consumer()
        assert wait_for(lambda: engine.queue_size() == 0)
        assert model.predict.called
        assert wait_for(lambda: not engine.consumer_alive)    # очередь пуста, змейки нет — сам остановился
        assert engine.is_running is False

    def test_found_png_moves_to_found_and_triggers_callback(self, tmp_path):
        model = MagicMock()
        model.predict.return_value = [MagicMock(boxes=[MagicMock()])]
        seen = []
        engine = make_engine(tmp_path, model=model, on_found_callback=lambda f, p: seen.append(p))
        write_img(str(tmp_path / "pending" / "bourse.png"), size=32)
        engine.start_consumer()
        assert wait_for(lambda: len(seen) == 1)
        assert os.path.dirname(seen[0]) == engine.found_dir
        assert os.path.exists(seen[0])
        assert engine.queue_size() == 0

    def test_files_processed_oldest_first(self, tmp_path):
        model = MagicMock()
        order = []

        def predict(frame, **kw):
            order.append(frame.shape[0])
            return [MagicMock(boxes=[])]

        model.predict.side_effect = predict
        engine = make_engine(tmp_path, model=model)
        write_img(str(tmp_path / "pending" / "zzz.png"), size=11)
        time.sleep(0.05)
        write_img(str(tmp_path / "pending" / "aaa.png"), size=22)
        time.sleep(0.05)
        write_img(str(tmp_path / "pending" / "mmm.jpg"), size=33)
        engine.start_consumer()
        assert wait_for(lambda: engine.queue_size() == 0)
        assert order == [11, 22, 33]

    def test_expired_frame_is_deleted_without_running_the_network(self, tmp_path):
        model = no_box_model()
        engine = make_engine(tmp_path, model=model, ttl_sec=0.2)
        write_img(str(tmp_path / "pending" / "stale.png"))
        time.sleep(0.4)
        engine.start_consumer()
        assert wait_for(lambda: engine.queue_size() == 0)
        assert not model.predict.called


class TestNeuralButtonSemantics:
    def test_stop_consumer_really_stops_processing_files_added_later(self, tmp_path):
        model = no_box_model()
        engine = make_engine(tmp_path, model=model)
        engine.start()
        engine.stop_consumer()
        assert wait_for(lambda: not engine.consumer_alive)
        time.sleep(0.2)
        calls_before = model.predict.call_count
        write_img(str(tmp_path / "pending" / "later.png"))
        time.sleep(0.6)
        assert model.predict.call_count == calls_before     # нейросеть остановлена и не трогает очередь
        assert (tmp_path / "pending" / "later.png").exists()
        engine.stop()

    def test_snake_start_does_not_revive_a_network_the_user_stopped(self, tmp_path):
        engine = make_engine(tmp_path)
        engine.stop_consumer()
        engine.start()
        time.sleep(0.4)
        assert engine.consumer_alive is False
        engine.stop()

    def test_snake_start_spawns_network_when_user_did_not_stop_it(self, tmp_path):
        engine = make_engine(tmp_path)
        engine.start()
        assert wait_for(lambda: engine.consumer_alive)
        engine.stop()

    def test_explicit_start_consumer_clears_the_user_stop(self, tmp_path):
        engine = make_engine(tmp_path)
        engine.stop_consumer()
        write_img(str(tmp_path / "pending" / "x.png"))
        engine.start_consumer()      # без змейки и с пустой очередью нейросеть сразу бы завершилась
        assert wait_for(lambda: engine.queue_size() == 0)


class TestAutoPause:
    def _paused_engine(self, tmp_path, pause=6, resume=2):
        engine = make_engine(tmp_path, pause_threshold=pause, resume_threshold=resume)
        engine.start()
        engine.stop_consumer()                       # очередь только растёт
        return engine

    def test_snake_pauses_itself_when_queue_reaches_threshold(self, tmp_path):
        engine = self._paused_engine(tmp_path)
        assert wait_for(lambda: engine.paused_by_queue)
        size = engine.queue_size()
        assert 6 <= size <= 7
        counter = engine._frame_counter
        time.sleep(0.6)
        assert engine._frame_counter == counter      # змейка стоит: новых кадров нет
        assert engine.is_running is True             # сессия жива — это пауза, не остановка
        engine.stop()

    def test_stays_paused_between_thresholds_and_resumes_at_low_mark(self, tmp_path):
        engine = self._paused_engine(tmp_path, pause=6, resume=2)
        assert wait_for(lambda: engine.paused_by_queue)
        files = list_queue(engine.pending_dir)
        for p in files[: len(files) - 4]:            # оставляем 4: выше порога возобновления (2)
            os.remove(p)
        time.sleep(0.6)
        assert engine.paused_by_queue is True        # гистерезис: 4 > 2 — ещё пауза
        for p in list_queue(engine.pending_dir)[:3]:  # остаётся 1 <= 2
            os.remove(p)
        assert wait_for(lambda: not engine.paused_by_queue)
        counter = engine._frame_counter
        assert wait_for(lambda: engine._frame_counter > counter)   # снова пишет кадры
        engine.stop()

    def test_resumes_when_the_network_is_started_and_drains_the_queue(self, tmp_path):
        engine = self._paused_engine(tmp_path)
        assert wait_for(lambda: engine.paused_by_queue)
        engine.start_consumer()
        assert wait_for(lambda: not engine.paused_by_queue)
        engine.stop()

    def test_stop_during_pause_returns_promptly(self, tmp_path):
        engine = self._paused_engine(tmp_path)
        assert wait_for(lambda: engine.paused_by_queue)
        t0 = time.time()
        engine.stop()
        assert time.time() - t0 < 2.0
        assert not engine._producer_thread.is_alive()
        assert engine.paused_by_queue is False

    def test_default_thresholds_come_from_the_owner_decision(self, tmp_path):
        engine = make_engine(tmp_path)
        assert engine.pause_threshold == 300
        assert engine.resume_threshold == 30


class TestStaleFramesAfterLongPause:
    """Бот выключили и включили через неделю: всё, что добавлено больше 30 минут назад по реальному
    времени, удаляется — до старта и без обработки нейросетью."""

    def test_snake_start_removes_stale_frames_and_folders_left_from_old_runs(self, tmp_path):
        model = no_box_model()
        engine = make_engine(tmp_path, model=model, ttl_sec=0.2)
        write_img(str(tmp_path / "pending" / "2026-09-14_10-00-00_dead" / "000001.jpg"))
        write_img(str(tmp_path / "pending" / "screen.png"))
        write_img(str(tmp_path / "found" / "old_find.jpg"))
        time.sleep(0.4)
        engine.stop_consumer()          # чтобы проверить именно чистку при старте, а не consumer
        engine.start()
        engine.stop()
        assert not (tmp_path / "pending" / "screen.png").exists()
        assert not (tmp_path / "pending" / "2026-09-14_10-00-00_dead").exists()
        assert not (tmp_path / "found" / "old_find.jpg").exists()
        assert not model.predict.called

    def test_neural_start_removes_stale_frames_without_processing_them(self, tmp_path):
        model = no_box_model()
        engine = make_engine(tmp_path, model=model, ttl_sec=0.2)
        write_img(str(tmp_path / "pending" / "week_old.png"))
        time.sleep(0.4)
        engine.start_consumer()
        assert wait_for(lambda: engine.queue_size() == 0)
        assert not model.predict.called

    def test_fresh_frames_survive_the_start_cleanup(self, tmp_path):
        engine = make_engine(tmp_path)
        write_img(str(tmp_path / "pending" / "fresh.png"))
        engine.stop_consumer()
        engine.start()
        engine.stop()
        assert (tmp_path / "pending" / "fresh.png").exists()
