"""
TDD: поведение после рефактора на Tkinter-based restart.

Архитектура (новая):
  - navigator: is_running=False немедленно, restart_callback() без аргументов
  - engine: нет restart_after_exchange, есть on_exchange_found_callback
  - main.py: after(10000, _programmatic_restart)

Старые тесты на restart_after_exchange удалены вместе с методом.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 1. engine.start() сохраняет kwargs — нужны для _programmatic_restart
# ---------------------------------------------------------------------------

class TestStartSavesKwargs:
    """engine.start() сохраняет все параметры в _last_start_kwargs."""

    def test_start_saves_all_kwargs(self):
        """start() сохраняет move_wait, conf и все остальные параметры."""
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

        class FakePacman:
            def __init__(self_p, **kw):
                self_p.is_running = False; self_p._yolo_unblock_time = 0.0
                self_p.on_found_callback = None; self_p.restart_callback = None
                self_p._thread = None
            def start(self_p): self_p.is_running = True
            def stop(self_p): self_p.is_running = False

        with patch('engine.PacmanEngine', FakePacman), patch.object(eng, '_start_heartbeat'):
            eng.start(conf=0.8, move_wait=1.5, center_x=90)

        assert eng._last_start_kwargs.get('move_wait') == 1.5
        assert eng._last_start_kwargs.get('conf') == 0.8
        assert 'joystick_step' in eng._last_start_kwargs
        assert 'navigation_enabled' in eng._last_start_kwargs


# ---------------------------------------------------------------------------
# 2. Navigator: ESC нажимается перед остановкой
# ---------------------------------------------------------------------------

class TestExchangeDetectedNewBehavior:
    """navigator._exchange_detected: новое поведение — мгновенная остановка."""

    def _setup(self):
        import numpy as np
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
        b = MagicMock()
        b.xyxy.cpu.return_value.tolist.return_value = [[100., 100., 200., 200.]]
        b.conf = [0.9]
        r = MagicMock(); r.boxes = [b]
        m = MagicMock(); m.predict.return_value = [r]
        eng.yolo_model = m
        j = CoastalSnakeNavigator.__new__(CoastalSnakeNavigator)
        j._last_move_vec = (1.0, 0.0); j._footprint_enabled = False
        j.center_x = 90; j.center_y = 925; j.p_range_x = 23; j.p_range_y = 13
        eng.joystick = j
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        return eng, frame

    def test_esc_pressed_after_found_callback(self):
        """ESC нажимается ПОСЛЕ on_found_callback — диалог закрывается корректно."""
        import numpy as np
        from navigator import CoastalSnakeNavigator
        eng, frame = self._setup()
        order = []
        eng.on_found_callback = lambda: order.append('ocr')

        sct = MagicMock()
        sct.monitors = [None, MagicMock()]
        sct.grab.return_value = np.zeros((100, 100, 4), dtype=np.uint8)
        cm = MagicMock(); cm.__enter__.return_value = sct; cm.__exit__.return_value = False

        with (
            patch('navigator.time.sleep'),
            patch('navigator.pyautogui.click'),
            patch('navigator.pyautogui.press', side_effect=lambda k: order.append(f'press_{k}')),
            patch('navigator.winsound.PlaySound'),
            patch('navigator.winsound.Beep'),
            patch('navigator.PacmanEngine._trigger_yolo_block'),
            patch('mss.mss', return_value=cm),
            patch.object(CoastalSnakeNavigator, '_click_vec'),
            patch('debug_reporter.report_find', MagicMock()),
            patch('debug_reporter.report_dialog', MagicMock()),
            patch('auth.get_hwid', return_value='test-hwid'),
        ):
            eng._exchange_detected(MagicMock(
                xyxy=MagicMock(cpu=lambda: MagicMock(tolist=lambda: [[100., 100., 200., 200.]])),
                conf=[0.9]
            ), frame=frame)

        assert 'ocr' in order
        assert any('escape' in e for e in order), \
            f"ESC должен быть нажат, события: {order}"
        ocr_idx = order.index('ocr')
        esc_idx = next(i for i, e in enumerate(order) if 'escape' in e)
        assert ocr_idx < esc_idx, "OCR должен быть ДО ESC"

    def test_fallback_no_yolo_block_when_callback_set(self):
        """Если restart_callback задан — _trigger_yolo_block НЕ вызывается (не нужен)."""
        import numpy as np
        from navigator import CoastalSnakeNavigator
        eng, frame = self._setup()
        eng.restart_callback = lambda: None

        sct = MagicMock()
        sct.monitors = [None, MagicMock()]
        sct.grab.return_value = np.zeros((100, 100, 4), dtype=np.uint8)
        cm = MagicMock(); cm.__enter__.return_value = sct; cm.__exit__.return_value = False

        with (
            patch('navigator.time.sleep'),
            patch('navigator.pyautogui.click'),
            patch('navigator.pyautogui.press'),
            patch('navigator.winsound.PlaySound'),
            patch('navigator.winsound.Beep'),
            patch('navigator.PacmanEngine._trigger_yolo_block') as mock_block,
            patch('mss.mss', return_value=cm),
            patch.object(CoastalSnakeNavigator, '_click_vec'),
            patch('debug_reporter.report_find', MagicMock()),
            patch('debug_reporter.report_dialog', MagicMock()),
            patch('auth.get_hwid', return_value='test-hwid'),
        ):
            b = MagicMock()
            b.xyxy.cpu.return_value.tolist.return_value = [[100., 100., 200., 200.]]
            b.conf = [0.9]
            eng._exchange_detected(b, frame=frame)

        mock_block.assert_not_called()
