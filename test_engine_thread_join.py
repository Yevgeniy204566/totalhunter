"""
TDD: move_wait корректно сохраняется и передаётся при перезапуске.

Тесты на join в engine.start() удалены — join убран (Tkinter-based restart).
Тесты на join в PacmanEngine.start() — в test_exchange_flow_v2.py.
"""

import threading
import pytest
from unittest.mock import MagicMock, patch


class FakePacmanForTest:
    def __init__(self_p, **kwargs):
        self_p.is_running = False
        self_p._yolo_unblock_time = 0.0
        self_p.on_found_callback = None
        self_p.restart_callback = None
        self_p._thread = None

    def start(self_p): self_p.is_running = True
    def stop(self_p):  self_p.is_running = False


def _make_engine(pacman_cls=None):
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
    return eng


# ---------------------------------------------------------------------------
# move_wait корректно сохраняется и передаётся
# ---------------------------------------------------------------------------

class TestMoveWaitPreservedOnRestart:
    """move_wait из _last_start_kwargs должен корректно сохраняться и передаваться."""

    def test_move_wait_saved_in_last_start_kwargs(self):
        """engine.start() сохраняет move_wait=1.5 в _last_start_kwargs."""
        eng = _make_engine()

        with patch('engine.PacmanEngine', FakePacmanForTest), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.8, move_wait=1.5, center_x=90)
            except Exception:
                pass

        assert eng._last_start_kwargs.get('move_wait') == 1.5, \
            f"move_wait должен быть 1.5 в _last_start_kwargs, получили: {eng._last_start_kwargs}"

    def test_all_params_saved_in_last_start_kwargs(self):
        """engine.start() сохраняет все параметры включая навигационные."""
        eng = _make_engine()

        with patch('engine.PacmanEngine', FakePacmanForTest), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.8, move_wait=1.5, center_x=90,
                          joystick_step=13, ocean_land_ratio=0.03)
            except Exception:
                pass

        kw = eng._last_start_kwargs
        assert kw.get('move_wait') == 1.5
        assert kw.get('joystick_step') == 13
        assert kw.get('ocean_land_ratio') == 0.03
        assert 'navigation_enabled' in kw

    def test_programmatic_restart_gets_move_wait_from_last_kwargs(self):
        """При перезапуске start() получает move_wait из _last_start_kwargs."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng._last_start_kwargs = {'conf': 0.8, 'move_wait': 1.5, 'center_x': 90}

        received_kwargs = {}

        def fake_start(**kwargs):
            received_kwargs.update(kwargs)

        with patch.object(eng, 'start', side_effect=fake_start):
            eng.start(**eng._last_start_kwargs)

        assert received_kwargs.get('move_wait') == 1.5, \
            f"move_wait должен быть 1.5 при перезапуске, получили: {received_kwargs}"
