"""
TDD v2: Exchange flow — поведение после Tkinter-based restart рефактора.

Актуальные тесты:
1. YOLO-блок 30с устанавливается ДО pacman.start() (нет гонки)
2. PacmanEngine.start() джойнит старый тред перед запуском нового
3. Дублирующие heartbeat/roy_scan треды не создаются при рестарте

Удалено: sleep(10), restart_callback(delay=0) → см. test_tkinter_restart_architecture.py
"""

import threading
import time
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 1. YOLO-блок 30с устанавливается ДО pacman.start()
# ---------------------------------------------------------------------------

class TestYoloBlock30sBeforeStart:
    """YOLO-блок 30с должен быть установлен ДО старта нового треда _run()."""

    def test_initial_yolo_block_sec_attribute_exists(self):
        """HuntEngine.__init__ устанавливает _initial_yolo_block_sec = 0.0."""
        import inspect
        from engine import HuntEngine
        source = inspect.getsource(HuntEngine.__init__)
        assert '_initial_yolo_block_sec' in source, \
            "_initial_yolo_block_sec не найден в HuntEngine.__init__"

    def test_yolo_block_set_before_pacman_thread_starts(self):
        """_initial_yolo_block_sec применяется ДО pacman.start() (нет гонки)."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.is_running = False
        eng.roy_enabled = False
        eng._roy_client = None
        eng.roy_kingdom = 0
        eng._last_start_kwargs = {}
        eng.on_engine_restart_callback = None
        eng.on_pool_refresh_callback = None
        eng.on_found_callback = None
        eng.on_last_exchange_callback = None
        eng._mm_cx = 90; eng._mm_cy = 925
        eng._initial_yolo_block_sec = 30.0
        eng._bg_gen = 0
        eng.sound_path = None
        eng.model = MagicMock()
        eng._pacman = None
        eng.on_exchange_found_callback = None

        yolo_block_at_thread_start = []

        class FakePacman:
            def __init__(self_p, **kwargs):
                self_p.is_running = False
                self_p._yolo_unblock_time = 0.0
                self_p.on_found_callback = None
                self_p.restart_callback = None
                self_p._thread = None

            def start(self_p):
                yolo_block_at_thread_start.append(self_p._yolo_unblock_time)
                self_p.is_running = True

            def stop(self_p):
                self_p.is_running = False

        with patch('engine.PacmanEngine', FakePacman), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.5)
            except Exception:
                pass

        assert yolo_block_at_thread_start, "pacman.start() не был вызван"
        recorded_block = yolo_block_at_thread_start[0]
        assert recorded_block > time.time() + 25, \
            f"YOLO-блок должен быть ≥25с при вызове pacman.start(), получили: {recorded_block - time.time():.1f}с"


# ---------------------------------------------------------------------------
# 2. PacmanEngine.start() джойнит старый тред
# ---------------------------------------------------------------------------

class TestPacmanStartJoinsOldThread:
    """PacmanEngine.start() должен дождаться завершения старого треда."""

    def test_join_called_on_alive_old_thread(self):
        """Если старый тред жив — join() вызывается перед запуском нового."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng.is_running = False
        eng._yolo_unblock_time = 0.0
        eng._suppressing_esc = False
        eng.restart_callback = None
        eng.on_found_callback = None

        order = []
        old_thread = MagicMock()
        old_thread.is_alive.return_value = True
        old_thread.join.side_effect = lambda timeout=None: order.append('join')
        eng._thread = old_thread
        eng.joystick = MagicMock()

        new_thread = MagicMock()
        new_thread.start.side_effect = lambda: order.append('new_start')

        with patch('threading.Thread', return_value=new_thread):
            eng.start()

        assert 'join' in order, "join() не был вызван для старого треда"
        assert 'new_start' in order, "новый тред не стартовал"
        assert order.index('join') < order.index('new_start'), \
            f"join() должен быть ДО нового старта, порядок: {order}"

    def test_no_join_if_thread_not_alive(self):
        """Если старый тред мёртв — join() не вызывается."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng.is_running = False
        eng._yolo_unblock_time = 0.0
        eng._suppressing_esc = False
        eng.restart_callback = None
        eng.on_found_callback = None
        old_thread = MagicMock()
        old_thread.is_alive.return_value = False
        eng._thread = old_thread
        eng.joystick = MagicMock()

        with patch('threading.Thread', return_value=MagicMock()):
            eng.start()

        old_thread.join.assert_not_called()

    def test_no_join_if_no_thread(self):
        """Если _thread=None — join() не вызывается (первый старт)."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng.is_running = False
        eng._yolo_unblock_time = 0.0
        eng._suppressing_esc = False
        eng.restart_callback = None
        eng.on_found_callback = None
        eng._thread = None
        eng.joystick = MagicMock()

        new_thread = MagicMock()
        with patch('threading.Thread', return_value=new_thread):
            eng.start()

        new_thread.start.assert_called_once()


# ---------------------------------------------------------------------------
# 3. Дублирующие фоновые треды не создаются
# ---------------------------------------------------------------------------

class TestNoDuplicateBackgroundThreads:
    """heartbeat и roy_scan треды не дублируются при повторном start()."""

    def _make_engine_for_heartbeat(self):
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.is_running = True
        eng.roy_enabled = False
        eng._pacman = None
        eng._roy_client = None
        eng.roy_kingdom = 0
        eng._bg_gen = 0
        return eng

    def test_bg_gen_attribute_exists(self):
        """HuntEngine.__init__ устанавливает _bg_gen = 0."""
        import inspect
        from engine import HuntEngine
        source = inspect.getsource(HuntEngine.__init__)
        assert '_bg_gen' in source, \
            "_bg_gen не найден в HuntEngine.__init__"

    def test_heartbeat_gen_increments_on_start(self):
        """Каждый start() увеличивает _bg_gen — старые треды видят изменение и выходят."""
        eng = self._make_engine_for_heartbeat()
        gen_before = eng._bg_gen

        thread_count = [0]
        original_thread = threading.Thread

        def counting_thread(*args, **kwargs):
            t = original_thread(*args, **kwargs)
            thread_count[0] += 1
            return t

        with patch('engine.threading.Thread', side_effect=counting_thread), \
             patch('engine._heartbeat'):
            eng._start_heartbeat()
            gen_after = eng._bg_gen

        assert gen_after > gen_before, \
            f"_bg_gen должен увеличиваться при _start_heartbeat(), было {gen_before}, стало {gen_after}"


# ---------------------------------------------------------------------------
# 4. joystick.step() не вызывается после _exchange_detected (guard)
# ---------------------------------------------------------------------------

class TestNoNavStepAfterExchange:
    """joystick.step() НЕ должен вызываться когда is_running=False после _exchange_detected."""

    def test_no_step_after_exchange_detected(self):
        """После _exchange_detected (is_running=False) joystick.step() не вызывается."""
        import inspect
        from navigator import PacmanEngine
        source = inspect.getsource(PacmanEngine._run)

        step_pos = source.find('joystick.step(')
        assert step_pos != -1, "joystick.step() должен быть в _run()"

        guard_pos = source.rfind('if not self.is_running', 0, step_pos)
        assert guard_pos != -1, \
            "Перед joystick.step() должен быть guard 'if not self.is_running: break'"

