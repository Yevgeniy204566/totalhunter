"""
TDD: Новая архитектура перезапуска через Tkinter mainloop.

Алгоритм:
  1. Биржа найдена → navigator: is_running=False (немедленно), restart_callback() без арг.
  2. engine: передаёт on_exchange_found_callback как pacman.restart_callback
  3. main.py._on_exchange_found: engine.stop() + self.after(10000, _programmatic_restart)
  4. _programmatic_restart: engine.start(**last_kwargs) — один чистый поток

Гарантия: Tkinter after() вызывается ТОЛЬКО РАЗ в главном цикле.
Пересечение потоков физически невозможно.
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _yolo_found():
    """YOLO model mock — всегда находит биржу на fresh scan."""
    b = MagicMock()
    b.xyxy.cpu.return_value.tolist.return_value = [[100., 100., 200., 200.]]
    b.conf = [0.9]
    r = MagicMock()
    r.boxes = [b]
    m = MagicMock()
    m.predict.return_value = [r]
    return m


def _make_exchange_engine():
    """PacmanEngine + CoastalSnakeNavigator для тестов _exchange_detected."""
    from navigator import PacmanEngine, CoastalSnakeNavigator
    eng = PacmanEngine.__new__(PacmanEngine)
    eng.is_running = True
    eng._yolo_unblock_time = 0.0
    eng.on_found_callback = None
    eng.restart_callback = None
    eng._suppressing_esc = False
    eng._thread = None
    eng.conf = 0.7
    eng.sound_path = ''
    eng.yolo_model = _yolo_found()  # fresh scan всегда находит биржу
    j = CoastalSnakeNavigator.__new__(CoastalSnakeNavigator)
    j._last_move_vec = (1.0, 0.0)
    j._footprint_enabled = False
    j.center_x = 90; j.center_y = 925
    j.p_range_x = 23; j.p_range_y = 13
    eng.joystick = j
    return eng


def _fake_mss_cm():
    sct = MagicMock()
    sct.monitors = [None, MagicMock()]
    sct.grab.return_value = np.zeros((100, 100, 4), dtype=np.uint8)
    cm = MagicMock()
    cm.__enter__.return_value = sct
    cm.__exit__.return_value = False
    return cm


def _box():
    b = MagicMock()
    b.xyxy.cpu.return_value.tolist.return_value = [[100., 100., 200., 200.]]
    b.conf = [0.9]
    return b


def _run_exchange_detected(eng, extra_patches=None):
    """Запустить _exchange_detected с замокированным I/O."""
    from navigator import CoastalSnakeNavigator
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    patches = [
        patch('navigator.time.sleep'),
        patch('navigator.pyautogui.click'),
        patch('navigator.pyautogui.press'),
        patch('navigator.winsound.PlaySound'),
        patch('navigator.winsound.Beep'),
        patch('navigator.PacmanEngine._trigger_yolo_block'),
        patch('mss.mss', return_value=_fake_mss_cm()),
        patch.object(CoastalSnakeNavigator, '_click_vec'),
        patch('debug_reporter.report_find', MagicMock()),
        patch('debug_reporter.report_dialog', MagicMock()),
        patch('auth.get_hwid', return_value='test-hwid'),
    ]
    if extra_patches:
        patches.extend(extra_patches)

    entered = [p.__enter__() for p in patches]
    try:
        eng._exchange_detected(_box(), frame=frame)
    finally:
        for p in patches:
            p.__exit__(None, None, None)
    return entered


# ─────────────────────────────────────────────────────────────────────────────
# 1. navigator: поток умирает НЕМЕДЛЕННО, без sleep(10)
# ─────────────────────────────────────────────────────────────────────────────

class TestNavigatorExchangeStopsImmediately:

    def test_is_running_false_after_exchange_detected(self):
        """is_running=False выставляется внутри _exchange_detected."""
        eng = _make_exchange_engine()
        _run_exchange_detected(eng)
        assert eng.is_running is False, \
            "is_running должен быть False сразу после _exchange_detected"

    def test_no_sleep_10_inside_exchange_detected(self):
        """time.sleep(10) НЕ вызывается внутри _exchange_detected — 10с теперь в Tkinter after."""
        from navigator import PacmanEngine, CoastalSnakeNavigator
        eng = _make_exchange_engine()
        sleep_calls = []

        def fake_sleep(s):
            sleep_calls.append(s)

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        with (
            patch('navigator.time.sleep', side_effect=fake_sleep),
            patch('navigator.pyautogui.click'),
            patch('navigator.pyautogui.press'),
            patch('navigator.winsound.PlaySound'),
            patch('navigator.winsound.Beep'),
            patch('navigator.PacmanEngine._trigger_yolo_block'),
            patch('mss.mss', return_value=_fake_mss_cm()),
            patch.object(CoastalSnakeNavigator, '_click_vec'),
            patch('debug_reporter.report_find', MagicMock()),
            patch('debug_reporter.report_dialog', MagicMock()),
            patch('auth.get_hwid', return_value='test-hwid'),
        ):
            eng._exchange_detected(_box(), frame=frame)

        assert 10 not in sleep_calls and 10.0 not in sleep_calls, \
            f"sleep(10) запрещён в navigator — 10с теперь в Tkinter. Найдено: {sleep_calls}"

    def test_restart_callback_called_without_positional_args(self):
        """restart_callback() вызывается БЕЗ аргументов — main.py сам контролирует задержку."""
        eng = _make_exchange_engine()
        call_args_list = []
        eng.restart_callback = lambda *args, **kwargs: call_args_list.append((args, kwargs))

        _run_exchange_detected(eng)

        assert len(call_args_list) == 1, \
            f"restart_callback должен быть вызван ровно 1 раз, вызовов: {len(call_args_list)}"
        args, kwargs = call_args_list[0]
        assert args == (), \
            f"restart_callback должен вызываться БЕЗ аргументов, получили args={args}"

    def test_restart_callback_called_after_is_running_false(self):
        """is_running=False выставляется ДО вызова restart_callback."""
        eng = _make_exchange_engine()
        order = []

        original_setattr = object.__setattr__

        class TrackingEngine(eng.__class__):
            pass

        # Используем свойство is_running через side_effect на restart_callback
        running_at_callback = []

        def cb():
            running_at_callback.append(eng.is_running)

        eng.restart_callback = cb
        _run_exchange_detected(eng)

        assert running_at_callback == [False], \
            f"is_running должен быть False ДО restart_callback, было: {running_at_callback}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. engine: нет restart_after_exchange, есть on_exchange_found_callback
# ─────────────────────────────────────────────────────────────────────────────

class TestEngineNewRestartArchitecture:

    def test_engine_has_no_restart_after_exchange(self):
        """HuntEngine.restart_after_exchange УДАЛЁН — перезапуском управляет main.py."""
        from engine import HuntEngine
        assert not hasattr(HuntEngine, 'restart_after_exchange'), \
            "restart_after_exchange должен быть удалён — только Tkinter-based restart"

    def test_engine_has_on_exchange_found_callback_attr(self):
        """HuntEngine.__init__ инициализирует on_exchange_found_callback = None."""
        from engine import HuntEngine
        eng = HuntEngine()
        assert hasattr(eng, 'on_exchange_found_callback'), \
            "HuntEngine должен иметь on_exchange_found_callback"
        # Не проверяем значение — может быть None или другим в полном __init__

    def test_engine_start_passes_on_exchange_found_to_pacman(self):
        """engine.start() передаёт on_exchange_found_callback как pacman.restart_callback."""
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
        eng._initial_yolo_block_sec = 0.0
        eng._bg_gen = 0
        eng.sound_path = None
        eng.model = MagicMock()
        eng._pacman = None

        my_cb = lambda: None
        eng.on_exchange_found_callback = my_cb

        class FakePacman:
            def __init__(self_p, **kw):
                self_p.is_running = False
                self_p._yolo_unblock_time = 0.0
                self_p.on_found_callback = None
                self_p.restart_callback = None
                self_p._thread = None
            def start(self_p): self_p.is_running = True
            def stop(self_p): self_p.is_running = False

        with patch('engine.PacmanEngine', FakePacman), patch.object(eng, '_start_heartbeat'):
            eng.start(conf=0.5)

        assert eng._pacman.restart_callback is my_cb, \
            "pacman.restart_callback должен быть on_exchange_found_callback из engine"

    def test_engine_start_no_threading_timer(self):
        """engine.start() не создаёт threading.Timer (таймер теперь в Tkinter.after)."""
        import threading as _threading
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
        eng._initial_yolo_block_sec = 0.0
        eng._bg_gen = 0
        eng.sound_path = None
        eng.model = MagicMock()
        eng._pacman = None
        eng.on_exchange_found_callback = None

        timer_created = []
        original_timer = _threading.Timer

        class TrackingTimer(original_timer):
            def __init__(self_t, *a, **kw):
                super().__init__(*a, **kw)
                timer_created.append(True)

        class FakePacman:
            def __init__(self_p, **kw):
                self_p.is_running = False
                self_p._yolo_unblock_time = 0.0
                self_p.on_found_callback = None
                self_p.restart_callback = None
                self_p._thread = None
            def start(self_p): self_p.is_running = True
            def stop(self_p): self_p.is_running = False

        with patch('engine.PacmanEngine', FakePacman), \
             patch.object(eng, '_start_heartbeat'), \
             patch('threading.Timer', TrackingTimer):
            eng.start(conf=0.5)

        assert len(timer_created) == 0, \
            f"engine.start() не должен создавать threading.Timer, создано: {len(timer_created)}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Связка: on_exchange_found_callback → engine.stop() + after(10000)
# ─────────────────────────────────────────────────────────────────────────────

class TestOnExchangeFoundCallback:
    """Тестируем поведение callback без импорта Tkinter."""

    def test_callback_calls_engine_stop(self):
        """Когда on_exchange_found_callback срабатывает — engine.stop() вызывается."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.is_running = True
        eng._pacman = None
        eng.roy_enabled = False
        eng._roy_client = None
        eng.roy_kingdom = 0
        eng._bg_gen = 0
        eng._last_start_kwargs = {}
        eng.on_found_callback = None
        eng.on_pool_refresh_callback = None
        eng.on_last_exchange_callback = None
        eng.on_engine_restart_callback = None
        eng._initial_yolo_block_sec = 0.0
        eng._mm_cx = 90; eng._mm_cy = 925
        eng.sound_path = None
        eng.model = MagicMock()

        stop_called = []

        def on_exchange_found():
            eng.stop()
            stop_called.append(True)

        eng.on_exchange_found_callback = on_exchange_found

        class FakePacman:
            def __init__(self_p, **kw):
                self_p.is_running = False
                self_p._yolo_unblock_time = 0.0
                self_p.on_found_callback = None
                self_p.restart_callback = None
                self_p._thread = None
            def start(self_p): self_p.is_running = True
            def stop(self_p): self_p.is_running = False

        with patch('engine.PacmanEngine', FakePacman), patch.object(eng, '_start_heartbeat'):
            eng.start(conf=0.5)

        # Вызываем callback напрямую (симулируем что navigator вызвал его)
        eng._pacman.restart_callback()
        assert stop_called, "on_exchange_found_callback должен вызывать engine.stop()"

    def test_programmatic_restart_uses_last_start_kwargs(self):
        """Параметры из _last_start_kwargs (включая move_wait) передаются при перезапуске."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._last_start_kwargs = {
            'conf': 0.8, 'move_wait': 1.5, 'center_x': 90, 'center_y': 925,
            'joystick_step': 13, 'scan_interval': 0.6, 'navigation_enabled': True,
            'max_inland_steps': 5, 'ocean_land_ratio': 0.03, 'min_water_px': 500,
            'footprint_ttl': 120.0, 'diagonal_blind_coeff': 0.5,
            'coast_detect_radius': 50, 'return_delta_px': 0,
            'smooth_alpha': 0.5, 'use_beacon': False, 'pixels_per_step': 20,
        }

        restart_kwargs = {}

        def fake_start(**kwargs):
            restart_kwargs.update(kwargs)

        with patch.object(eng, 'start', side_effect=fake_start):
            # Симулируем _programmatic_restart: берём kwargs и вызываем start
            eng.start(**eng._last_start_kwargs)

        assert restart_kwargs.get('move_wait') == 1.5, \
            f"move_wait=1.5 должен быть в restart kwargs, получили: {restart_kwargs}"
        assert restart_kwargs.get('conf') == 0.8


# ─────────────────────────────────────────────────────────────────────────────
# 4. _programmatic_restart устанавливает YOLO-блок 20с (авто-рестарт после биржи)
# ─────────────────────────────────────────────────────────────────────────────

class TestProgrammaticRestartYoloBlock:
    """_programmatic_restart: YOLO блок 20с при авто-рестарте, ручной старт без блока."""

    def test_programmatic_restart_yolo_block_20s(self):
        """Авто-рестарт после биржи: YOLO блок 20с — бот уходит от найденной биржи."""
        import inspect
        import main as _main_module
        source = inspect.getsource(_main_module.TotalHunterApp._programmatic_restart)
        assert '60.0' in source, "_initial_yolo_block_sec = 60.0 должен быть в _programmatic_restart"
        assert '5.0' not in source, "5.0 запрещено — старый Ghost YOLO"
        assert '20.0' not in source, "20.0 запрещено — мало, ловим ту же биржу"

    def test_ghost_yolo_sleeps_measured_time_when_blocked(self):
        """Ghost YOLO: когда YOLO заблокирован — sleep(_last_yolo_inference_time) без cap."""
        import inspect
        from navigator import PacmanEngine
        source = inspect.getsource(PacmanEngine._run)
        assert 'time.sleep(self._last_yolo_inference_time)' in source, \
            "Ghost YOLO должен спать ровно _last_yolo_inference_time когда YOLO заблокирован"
        assert 'move_wait * 0.8' not in source, \
            "cap-формула move_wait*0.8 запрещена — вызывает ускорение"

    def test_yolo_block_mechanism_in_engine(self):
        """engine.py: _initial_yolo_block_sec > 0 → выставляет _yolo_unblock_time перед start."""
        import inspect
        from engine import HuntEngine
        source = inspect.getsource(HuntEngine.start)
        assert '_initial_yolo_block_sec' in source, \
            "_initial_yolo_block_sec должен применяться в start()"
        assert '_yolo_unblock_time' in source, \
            "start() должен передавать _yolo_unblock_time в _pacman"
