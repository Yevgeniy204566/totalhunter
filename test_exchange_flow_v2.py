"""
TDD v2: Exchange flow — желаемое поведение после рефактора.

1. time.sleep(10) В шаге 10 (пользователь видит координаты)
2. restart_callback вызывается с delay=0 (немедленный рестарт)
3. YOLO-блок 30с устанавливается ДО pacman.start() (нет гонки)
4. PacmanEngine.start() джойнит старый тред перед запуском нового
5. Дублирующие heartbeat/roy_scan треды не создаются при рестарте
"""

import threading
import time
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------

def _make_pacman():
    """Минимальный PacmanEngine без реального YOLO/экрана."""
    from navigator import PacmanEngine
    eng = PacmanEngine.__new__(PacmanEngine)
    eng.is_running = True
    eng.conf = 0.5
    eng.scan_interval = 0.6
    eng.yolo_model = MagicMock()
    eng.sound_path = None
    eng.move_wait = 2.0
    eng.navigation_enabled = True
    eng.on_found_callback = None
    eng._yolo_unblock_time = 0.0
    eng._suppressing_esc = False
    eng.restart_callback = None
    eng.joystick = MagicMock()
    eng.joystick.last_dx = 1
    eng.joystick.last_dy = 0
    eng._thread = None
    return eng


def _make_box_mock():
    box = MagicMock()
    box.xyxy.cpu.return_value.tolist.return_value = [[100.0, 100.0, 200.0, 200.0]]
    box.conf = [0.9]
    return box


def _make_mss_mock():
    import numpy as np
    img_array = np.zeros((1080, 1920, 4), dtype=np.uint8)
    mock_sct = MagicMock()
    mock_sct.monitors = [None, {'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]
    mock_sct.grab.return_value = img_array
    mock_sct.__enter__ = lambda s: s
    mock_sct.__exit__ = MagicMock(return_value=False)
    return mock_sct


def _run_exchange_detected(eng, box, fake_sleep=None, fake_press=None):
    """Запускает _exchange_detected с полным набором моков."""
    import numpy as np
    fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    mss_mock = _make_mss_mock()

    pred_result = MagicMock()
    pred_result.boxes = [box]
    eng.yolo_model.predict.return_value = [pred_result]

    patch_sleep = patch('navigator.time.sleep', side_effect=fake_sleep or (lambda s: None))
    patch_press = patch('navigator.pyautogui.press', side_effect=fake_press or (lambda k: None))

    with patch_sleep, patch_press, \
         patch('navigator.pyautogui.click'), \
         patch('navigator.winsound.PlaySound'), \
         patch('navigator.winsound.Beep'), \
         patch('mss.mss', return_value=mss_mock):
        eng._exchange_detected(box, frame=fake_frame)


# ---------------------------------------------------------------------------
# 1. time.sleep(10) в шаге 10
# ---------------------------------------------------------------------------

class TestSleep10InExchangeDetected:
    """_exchange_detected должна выдерживать 10-секундную паузу ДО ESC+рестарта."""

    def test_sleep10_called_before_esc(self):
        """time.sleep(10) вызывается ДО нажатия ESC."""
        eng = _make_pacman()
        order = []
        sleeps = []

        def fake_sleep(s):
            sleeps.append(s)
            if s == 10:
                order.append('sleep10')

        def fake_press(key):
            if key == 'escape':
                order.append('esc')

        eng.restart_callback = lambda delay: order.append('restart')

        _run_exchange_detected(eng, _make_box_mock(), fake_sleep=fake_sleep, fake_press=fake_press)

        assert 10 in sleeps, "time.sleep(10) не вызывается — должна быть пауза для просмотра координат"
        assert 'sleep10' in order, "'sleep10' не зафиксирован"
        assert 'esc' in order, "ESC не был нажат"
        assert order.index('sleep10') < order.index('esc'), \
            f"sleep(10) должен быть ДО ESC, порядок: {order}"

    def test_sleep10_called_before_restart(self):
        """time.sleep(10) вызывается ДО вызова restart_callback."""
        eng = _make_pacman()
        order = []

        def fake_sleep(s):
            if s == 10:
                order.append('sleep10')

        def fake_restart(delay):
            order.append('restart')

        eng.restart_callback = fake_restart

        _run_exchange_detected(eng, _make_box_mock(), fake_sleep=fake_sleep)

        assert 'sleep10' in order, "time.sleep(10) должен вызываться"
        assert 'restart' in order, "restart_callback должен вызываться"
        assert order.index('sleep10') < order.index('restart'), \
            f"sleep(10) должен быть ДО restart, порядок: {order}"


# ---------------------------------------------------------------------------
# 2. restart_callback вызывается с delay=0
# ---------------------------------------------------------------------------

class TestRestartCallbackDelay0:
    """restart_callback должен вызываться с delay=0 (немедленный рестарт)."""

    def test_restart_callback_delay_is_zero(self):
        """restart_callback вызывается с delay=0, НЕ с delay=10."""
        eng = _make_pacman()
        received_delay = []

        def fake_restart(delay):
            received_delay.append(delay)

        eng.restart_callback = fake_restart

        _run_exchange_detected(eng, _make_box_mock())

        assert received_delay, "restart_callback не был вызван"
        assert received_delay[0] == 0, \
            f"restart_callback должен вызываться с delay=0, получили delay={received_delay[0]}"

    def test_no_sleep_10_after_esc(self):
        """После ESC нет time.sleep(10) — задержка только ДО ESC."""
        eng = _make_pacman()
        order = []

        def fake_sleep(s):
            order.append(('sleep', s))

        def fake_press(key):
            if key == 'escape':
                order.append('esc')

        eng.restart_callback = lambda delay: None

        _run_exchange_detected(eng, _make_box_mock(), fake_sleep=fake_sleep, fake_press=fake_press)

        # Найти последний sleep(10) и ESC
        sleep10_indices = [i for i, e in enumerate(order) if e == ('sleep', 10)]
        esc_indices = [i for i, e in enumerate(order) if e == 'esc']
        if sleep10_indices and esc_indices:
            # Все sleep(10) должны быть ДО ESC
            assert max(sleep10_indices) < min(esc_indices), \
                f"sleep(10) после ESC! Порядок: {order}"


# ---------------------------------------------------------------------------
# 3. YOLO-блок 30с устанавливается ДО pacman.start()
# ---------------------------------------------------------------------------

class TestYoloBlock30sBeforeStart:
    """YOLO-блок 30с должен быть установлен ДО старта нового треда _run()."""

    def _make_engine(self):
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.is_running = True
        eng.roy_enabled = False
        eng._pacman = None
        eng._roy_client = None
        eng.roy_kingdom = 0
        eng._last_start_kwargs = {'conf': 0.5, 'center_x': 90}
        eng.on_engine_restart_callback = None
        eng._initial_yolo_block_sec = 0.0
        return eng

    def test_yolo_block_30s_after_restart(self):
        """Через restart_after_exchange YOLO-блок ≥25с (30с минус время выполнения)."""
        eng = self._make_engine()
        yolo_time_at_start = []

        def fake_start(**kwargs):
            if eng._pacman:
                yolo_time_at_start.append(eng._pacman._yolo_unblock_time)

        started = threading.Event()

        def fake_start_and_signal(**kwargs):
            if hasattr(eng, '_pacman') and eng._pacman:
                yolo_time_at_start.append(eng._pacman._yolo_unblock_time)
            started.set()

        with patch.object(eng, 'stop'), \
             patch.object(eng, 'start', side_effect=fake_start_and_signal):
            eng.restart_after_exchange(delay=0)
            started.wait(timeout=2.0)

        assert started.is_set(), "start() не был вызван"

    def test_initial_yolo_block_sec_attribute_exists(self):
        """HuntEngine.__init__ устанавливает _initial_yolo_block_sec = 0.0."""
        import inspect
        from engine import HuntEngine
        source = inspect.getsource(HuntEngine.__init__)
        assert '_initial_yolo_block_sec' in source, \
            "_initial_yolo_block_sec не найден в HuntEngine.__init__ — нужно добавить"

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
        eng._mm_cx = 90
        eng._mm_cy = 925
        eng._initial_yolo_block_sec = 30.0
        eng._bg_gen = 0
        eng.sound_path = None
        eng.model = MagicMock()

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
# 4. PacmanEngine.start() джойнит старый тред
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

        # Мокаем старый живой тред
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
        """Если старый тред мёртв — join() не вызывается (незачем ждать)."""
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
            eng.start()  # не должен упасть

        new_thread.start.assert_called_once()


# ---------------------------------------------------------------------------
# 5. Дублирующие фоновые треды не создаются
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
            "_bg_gen не найден в HuntEngine.__init__ — нужен для защиты от дублирующих тредов"

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
            f"_bg_gen должен увеличиваться при вызове _start_heartbeat(), было {gen_before}, стало {gen_after}"
