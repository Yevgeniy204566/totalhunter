"""Исправления змейки Биржи 2.0 после живого теста владельца (сессия #148):

1. Змейка умирала на втором запуске: `AttributeError: '_thread._local' object has no attribute 'srcdc'` —
   mss хранит дескрипторы захвата отдельно для каждого потока, а общий движок переиспользовал экземпляр
   mss из потока предыдущего запуска. Теперь mss создаётся по одному на поток.
2. Исключение в потоке змейки убивало её молча (кнопка продолжала показывать «Стоп»). Теперь ошибка
   запоминается, поток честно заканчивается, GUI возвращает кнопку и показывает ошибку.
3. Глубина нырка в 2.0 не должна расти от «Памяти следов» (в 1.0 растёт — не трогаем): 13 остаётся 13.
4. Публикация в РОЙ — отдельный переключатель (на время теста выключен, находки идут только в
   debug-Telegram); списание и звук от него не зависят."""

import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import exchange_scout
from exchange_scout import ExchangeScoutEngine, make_found_handler, process_found_frame


class TestCaptureIsPerThread:
    def _fake_mss_module(self, monkeypatch):
        """Двойник mss, который ведёт себя как настоящий на Windows: grab() из потока, отличного от
        создавшего экземпляр, падает тем же AttributeError про thread-local дескрипторы."""
        created = []

        class FakeSct:
            monitors = [None, {"left": 0, "top": 0, "width": 8, "height": 4}]

            def __init__(self):
                self.owner = threading.get_ident()
                created.append(self.owner)

            def grab(self, monitor):
                if threading.get_ident() != self.owner:
                    raise AttributeError("'_thread._local' object has no attribute 'srcdc'")
                return np.zeros((4, 8, 4), dtype=np.uint8)

        monkeypatch.setattr("mss.mss", lambda: FakeSct())
        return created

    def test_same_capture_fn_works_from_two_different_threads(self, monkeypatch):
        import main
        created = self._fake_mss_module(monkeypatch)
        capture = main.build_scout_capture_fn()
        results = []

        def run():
            results.append(capture().shape)

        for _ in range(2):                 # два «запуска змейки» = два разных потока-производителя
            t = threading.Thread(target=run)
            t.start()
            t.join()
        assert results == [(4, 8, 3), (4, 8, 3)]
        assert len(set(created)) == 2      # свой mss на каждый поток

    def test_one_thread_still_reuses_its_mss(self, monkeypatch):
        import main
        created = self._fake_mss_module(monkeypatch)
        capture = main.build_scout_capture_fn()
        capture()
        capture()
        assert len(created) == 1


class TestProducerErrorIsNotSilent:
    def _engine(self, tmp_path, capture_fn):
        return ExchangeScoutEngine(navigator=MagicMock(), capture_fn=capture_fn, model=MagicMock(),
                                   conf=0.8, sessions_root=str(tmp_path), move_wait=0.01)

    def test_exception_in_the_snake_is_recorded_and_the_session_ends(self, tmp_path):
        def boom():
            raise AttributeError("'_thread._local' object has no attribute 'srcdc'")

        engine = self._engine(tmp_path, boom)
        engine._nn_user_stopped = True
        engine.start()
        engine._producer_thread.join(timeout=3)
        assert not engine._producer_thread.is_alive()
        assert engine.is_running is False                 # больше не притворяется работающей
        assert "srcdc" in engine.producer_error

    def test_error_is_cleared_on_the_next_start(self, tmp_path):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("first run dies")
            return np.zeros((40, 40, 3), np.uint8)

        engine = self._engine(tmp_path, flaky)
        engine._nn_user_stopped = True
        engine.start()
        engine._producer_thread.join(timeout=3)
        assert engine.producer_error
        engine.start()
        time.sleep(0.3)
        assert engine.producer_error is None and engine.is_running is True
        engine.stop()

    def test_healthy_run_has_no_error(self, tmp_path):
        engine = self._engine(tmp_path, lambda: np.zeros((40, 40, 3), np.uint8))
        engine._nn_user_stopped = True
        engine.start()
        time.sleep(0.2)
        engine.stop()
        assert engine.producer_error is None


class TestDepthIsNotCoupledToFootprintMemoryIn20:
    def _nav(self, **kw):
        from navigator import CoastalSnakeNavigator
        nav = CoastalSnakeNavigator(center_x=90, center_y=925, step=13, footprint_ttl=100.0, **kw)
        return nav

    def test_2_0_navigator_keeps_the_chosen_depth_no_matter_the_footprint_memory(self):
        import main
        nav = main.build_scout_navigator(90, 925, 13, {
            'max_inland_steps': 5, 'ocean_land_ratio': 0.03, 'min_water_px': 500,
            'diagonal_blind_coeff': 0.5, 'footprint_ttl': 10.0, 'return_delta_px': 0,
            'smooth_alpha': 0.5, 'pixels_per_step': 20})
        with patch('navigator.time.time', return_value=1_000_000.0):
            nav._maybe_grow_dive_depth()
        with patch('navigator.time.time', return_value=1_100_000.0):    # намного дольше памяти следов
            nav._maybe_grow_dive_depth()
        assert nav.max_inland_steps == 5

    def test_13_stays_13(self):
        import main
        nav = main.build_scout_navigator(90, 925, 13, {
            'max_inland_steps': 13, 'ocean_land_ratio': 0.03, 'min_water_px': 500,
            'diagonal_blind_coeff': 0.5, 'footprint_ttl': 60.0, 'return_delta_px': 0,
            'smooth_alpha': 0.5, 'pixels_per_step': 20})
        with patch('navigator.time.time', return_value=1_000_000.0):
            nav._maybe_grow_dive_depth()
        with patch('navigator.time.time', return_value=1_100_000.0):
            nav._maybe_grow_dive_depth()
        assert nav.max_inland_steps == 13

    def test_bot_1_0_still_grows_depth_by_default(self):
        """Биржа 1.0 не тронута: значение по умолчанию прежнее — глубина растёт от памяти следов."""
        nav = self._nav(max_inland_steps=2)
        assert nav.auto_grow_depth is True
        with patch('navigator.time.time', return_value=1_000_000.0):
            nav._maybe_grow_dive_depth()
        with patch('navigator.time.time', return_value=1_000_101.0):
            nav._maybe_grow_dive_depth()
        assert nav.max_inland_steps == 3

    def test_footprint_memory_itself_is_untouched_in_2_0(self):
        import main
        nav = main.build_scout_navigator(90, 925, 13, {
            'max_inland_steps': 13, 'ocean_land_ratio': 0.03, 'min_water_px': 500,
            'diagonal_blind_coeff': 0.5, 'footprint_ttl': 77.0, 'return_delta_px': 0,
            'smooth_alpha': 0.5, 'pixels_per_step': 20})
        assert nav._footprint_ttl == 77.0


class TestRoyPublishSwitch:
    def _run(self, publish):
        spend = MagicMock(return_value={"success": True})
        roy = MagicMock()
        roy.report_scout_find.return_value = True
        with patch.object(exchange_scout, "read_exchange_position", lambda f, c: (233, 898, 548)):
            result = process_found_frame(np.zeros((10, 10, 3), np.uint8), (0, 0, 5, 5), 7, "exchange",
                                         spend, roy, publish=publish)
        return result, spend, roy

    def test_publish_off_charges_but_does_not_call_roy(self):
        result, spend, roy = self._run(publish=False)
        spend.assert_called_once_with("exchange")
        roy.report_scout_find.assert_not_called()
        assert result["charged"] is True and result["published"] is False and result["coords_ok"] is True

    def test_publish_on_is_the_old_behavior(self):
        result, _spend, roy = self._run(publish=True)
        roy.report_scout_find.assert_called_once_with(kingdom=233, x=898, y=548)
        assert result["published"] is True

    def test_handler_reads_the_switch_at_call_time(self):
        state = {"on": False}
        spend = MagicMock(return_value={"success": True})
        roy = MagicMock()
        roy.report_scout_find.return_value = True
        with patch.object(exchange_scout, "read_exchange_position", lambda f, c: (233, 898, 548)):
            h = make_found_handler((0, 0, 5, 5), 7, "exchange", "hw", spend_fn=spend, roy_client=roy,
                                   screen_size=(10, 10), publish_fn=lambda: state["on"])
            h(np.zeros((10, 10, 3), np.uint8), "a.png")
            assert roy.report_scout_find.call_count == 0
            state["on"] = True
            h(np.zeros((10, 10, 3), np.uint8), "b.png")
            assert roy.report_scout_find.call_count == 1

    def test_default_when_running_from_source_is_off_and_release_is_on(self):
        from exchange_mode_settings import scout_roy_publish_default
        assert scout_roy_publish_default(frozen=False) is False     # тест владельца: только Telegram
        assert scout_roy_publish_default(frozen=True) is True       # релиз: игроки ждут публикации

    def test_texts_exist(self):
        from exchange_mode_settings import scout_text
        for lang in ("RU", "UK", "EN"):
            assert scout_text(lang, "roy_publish")
