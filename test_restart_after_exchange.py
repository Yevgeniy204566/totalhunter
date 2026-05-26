"""
TDD: stop/auto-restart после находки биржи.
Бот находит биржу → engine.stop() → 10с таймер → engine.start(saved_kwargs).
"""

import threading
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# 1. engine.restart_after_exchange
# ---------------------------------------------------------------------------

class TestRestartAfterExchange:
    """HuntEngine.restart_after_exchange() — остановка + таймер + перезапуск."""

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
        return eng

    def test_stop_called_immediately(self):
        """restart_after_exchange() немедленно вызывает stop()."""
        eng = self._make_engine()
        with patch.object(eng, 'stop') as mock_stop, \
             patch.object(eng, 'start'):
            eng.restart_after_exchange(delay=0)
            threading.Event().wait(0.1)
            mock_stop.assert_called_once()

    def test_start_called_with_saved_kwargs(self):
        """После задержки start() вызывается с сохранёнными параметрами."""
        eng = self._make_engine()
        started = threading.Event()
        captured_kwargs = {}

        def fake_start(**kwargs):
            captured_kwargs.update(kwargs)
            started.set()

        with patch.object(eng, 'stop'), \
             patch.object(eng, 'start', side_effect=fake_start):
            eng.restart_after_exchange(delay=0)
            started.wait(timeout=2.0)

        assert started.is_set(), "start() не был вызван"
        assert captured_kwargs == {'conf': 0.5, 'center_x': 90}

    def test_on_engine_restart_callback_stopped(self):
        """Callback получает 'stopped' сразу после stop()."""
        eng = self._make_engine()
        states = []
        eng.on_engine_restart_callback = lambda s: states.append(s)

        with patch.object(eng, 'stop'), \
             patch.object(eng, 'start'):
            eng.restart_after_exchange(delay=0)
            threading.Event().wait(0.15)

        assert 'stopped' in states

    def test_on_engine_restart_callback_starting(self):
        """Callback получает 'starting' перед вызовом start()."""
        eng = self._make_engine()
        states = []
        started = threading.Event()
        eng.on_engine_restart_callback = lambda s: states.append(s)

        def fake_start(**_):
            started.set()

        with patch.object(eng, 'stop'), \
             patch.object(eng, 'start', side_effect=fake_start):
            eng.restart_after_exchange(delay=0)
            started.wait(timeout=2.0)

        assert 'starting' in states
        assert states.index('stopped') < states.index('starting')

    def test_empty_kwargs_does_not_start(self):
        """Если _last_start_kwargs пуст — start() не вызывается (защита от краша)."""
        eng = self._make_engine()
        eng._last_start_kwargs = {}
        started = threading.Event()

        with patch.object(eng, 'stop'), \
             patch.object(eng, 'start', side_effect=lambda **_: started.set()):
            eng.restart_after_exchange(delay=0)
            started.wait(timeout=0.3)

        assert not started.is_set(), "start() не должен вызываться с пустыми kwargs"


# ---------------------------------------------------------------------------
# 2. engine.start() сохраняет kwargs
# ---------------------------------------------------------------------------

class TestStartSavesKwargs:
    """HuntEngine.start() сохраняет все аргументы в _last_start_kwargs."""

    def test_start_saves_all_kwargs(self):
        """Все параметры start() сохраняются в _last_start_kwargs."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.roy_enabled = False
        eng._pacman = None
        eng.is_running = False
        eng.on_engine_restart_callback = None

        # Не даём реально запускать — только проверяем сохранение kwargs
        with patch('engine.PacmanEngine') as MockPacman, \
             patch.object(eng, '_start_heartbeat'):
            mock_instance = MagicMock()
            MockPacman.return_value = mock_instance
            try:
                eng.start(
                    conf=0.7,
                    center_x=100,
                    center_y=900,
                    joystick_step=13,
                    scan_interval=0.6,
                    move_wait=2.0,
                    navigation_enabled=True,
                    max_inland_steps=5,
                    ocean_land_ratio=0.03,
                    min_water_px=500,
                    footprint_ttl=120.0,
                    diagonal_blind_coeff=0.5,
                    coast_detect_radius=50,
                    return_delta_px=0,
                    smooth_alpha=0.5,
                    use_beacon=False,
                    pixels_per_step=20,
                )
            except Exception:
                pass  # движок может упасть без реального YOLO — это нормально

        assert hasattr(eng, '_last_start_kwargs'), "_last_start_kwargs не создан"
        kw = eng._last_start_kwargs
        assert kw.get('conf') == 0.7
        assert kw.get('center_x') == 100
        assert kw.get('center_y') == 900
        assert kw.get('joystick_step') == 13


# ---------------------------------------------------------------------------
# 3. navigator._exchange_detected — нет time.sleep(10), есть restart_callback
# ---------------------------------------------------------------------------

def _make_mss_mock(img_array=None):
    """Возвращает контекст-менеджер для mss, имитирующий захват экрана."""
    import numpy as np
    if img_array is None:
        img_array = np.zeros((1080, 1920, 4), dtype=np.uint8)
    mock_sct = MagicMock()
    mock_sct.monitors = [None, {'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]
    mock_sct.grab.return_value = img_array
    mock_sct.__enter__ = lambda s: s
    mock_sct.__exit__ = MagicMock(return_value=False)
    return mock_sct


def _make_box_mock():
    box = MagicMock()
    box.xyxy.cpu.return_value.tolist.return_value = [[100.0, 100.0, 200.0, 200.0]]
    box.conf = [0.9]
    return box


class TestExchangeDetectedNoSleep10:
    """_exchange_detected не вызывает time.sleep(10), вместо этого — restart_callback."""

    def _make_pacman(self):
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
        return eng

    def _run_exchange_detected(self, eng, box, fake_sleep=None, fake_press=None):
        """Запускает _exchange_detected с полным набором моков."""
        import numpy as np
        fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mss_mock = _make_mss_mock()

        # Настраиваем yolo_model.predict чтобы _fresh_scan возвращал box
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

    def test_restart_callback_called_instead_of_sleep10(self):
        """restart_callback вызывается с delay=10; time.sleep(10) НЕ вызывается."""
        eng = self._make_pacman()
        restart_called = threading.Event()
        restart_delay = []

        def fake_restart(delay):
            restart_delay.append(delay)
            restart_called.set()

        eng.restart_callback = fake_restart

        sleep_calls = []

        def fake_sleep(s):
            if s == 10:
                sleep_calls.append(s)

        self._run_exchange_detected(eng, _make_box_mock(), fake_sleep=fake_sleep)

        assert restart_called.is_set(), "restart_callback не был вызван"
        assert restart_delay == [10], f"restart_callback должен быть вызван с delay=10, получили {restart_delay}"
        assert 10 not in sleep_calls, "time.sleep(10) всё ещё вызывается — нужно убрать!"

    def test_esc_pressed_before_restart(self):
        """ESC нажимается ДО вызова restart_callback."""
        eng = self._make_pacman()
        order = []

        def fake_press(key):
            if key == 'escape':
                order.append('esc')

        def fake_restart(delay):
            order.append('restart')

        eng.restart_callback = fake_restart

        self._run_exchange_detected(eng, _make_box_mock(), fake_press=fake_press)

        assert 'esc' in order, "ESC не был нажат"
        assert 'restart' in order, "restart_callback не был вызван"
        assert order.index('esc') < order.index('restart'), \
            f"ESC должен быть ДО restart, порядок: {order}"

    def test_fallback_yolo_block_when_no_restart_callback(self):
        """Если restart_callback=None — YOLO-блок работает (fallback)."""
        eng = self._make_pacman()
        eng.restart_callback = None

        yolo_block_called = threading.Event()
        orig_trigger = eng.__class__._trigger_yolo_block

        with patch.object(eng.__class__, '_trigger_yolo_block',
                          lambda self, s=20: yolo_block_called.set()):
            self._run_exchange_detected(eng, _make_box_mock())

        assert yolo_block_called.is_set(), "_trigger_yolo_block должен вызываться как fallback"
