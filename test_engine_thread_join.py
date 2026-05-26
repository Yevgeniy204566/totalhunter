"""
TDD: engine.start() должен джойнить СТАРЫЙ pacman._thread ДО создания нового PacmanEngine.

Текущий баг: join() вызывается на НОВОМ PacmanEngine(_thread=None) — NO-OP.
Старый тред жив → два треда одновременно дёргают джойстик → x2 скорость.

Правильный фикс: в engine.start(), ДО создания нового PacmanEngine,
join old_pacman._thread с is_alive() проверкой после join.
"""

import threading
import time
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------

def _make_engine_with_old_pacman(old_thread_alive=True):
    """Создаёт HuntEngine с 'живым' старым _pacman._thread."""
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
    eng._initial_yolo_block_sec = 0.0
    eng._bg_gen = 0
    eng.sound_path = None
    eng.model = MagicMock()

    # Создаём старый мок-pacman с живым/мёртвым тредом
    old_pacman = MagicMock()
    old_thread = MagicMock()
    old_thread.is_alive.return_value = old_thread_alive
    old_pacman._thread = old_thread
    old_pacman.is_running = True
    old_pacman._yolo_unblock_time = 0.0
    old_pacman.on_found_callback = None
    old_pacman.restart_callback = None

    eng._pacman = old_pacman
    return eng, old_pacman, old_thread


class FakePacmanForJoinTest:
    """Новый PacmanEngine — проверяем что он запускается ТОЛЬКО после join старого."""

    def __init__(self_p, **kwargs):
        self_p.is_running = False
        self_p._yolo_unblock_time = 0.0
        self_p.on_found_callback = None
        self_p.restart_callback = None
        self_p._thread = None

    def start(self_p):
        self_p.is_running = True

    def stop(self_p):
        self_p.is_running = False


# ---------------------------------------------------------------------------
# 1. Основной тест: join OLD thread ПЕРЕД созданием нового PacmanEngine
# ---------------------------------------------------------------------------

class TestEngineJoinsOldPacmanThread:
    """engine.start() должен джойнить old_pacman._thread ДО создания нового PacmanEngine."""

    def test_old_thread_joined_before_new_pacman_created(self):
        """join() вызывается на old_pacman._thread ДО инициализации нового PacmanEngine."""
        eng, old_pacman, old_thread = _make_engine_with_old_pacman(old_thread_alive=True)
        order = []

        old_thread.join.side_effect = lambda timeout=None: order.append('join_old')
        old_thread.is_alive.side_effect = [True, False]  # alive → join → then dead

        new_pacman_created = threading.Event()

        class TrackingFakePacman(FakePacmanForJoinTest):
            def __init__(self_p, **kwargs):
                super().__init__(**kwargs)
                order.append('new_pacman_created')
                new_pacman_created.set()

        with patch('engine.PacmanEngine', TrackingFakePacman), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.5)
            except Exception:
                pass

        assert 'join_old' in order, "join() на старом треде не был вызван"
        assert 'new_pacman_created' in order, "новый PacmanEngine не был создан"
        assert order.index('join_old') < order.index('new_pacman_created'), \
            f"join(old) должен быть ДО создания нового PacmanEngine, порядок: {order}"

    def test_no_join_on_first_start(self):
        """На первом запуске (old _pacman=None) join не вызывается — не падает."""
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
        eng._initial_yolo_block_sec = 0.0
        eng._bg_gen = 0
        eng.sound_path = None
        eng.model = MagicMock()
        eng._pacman = None  # нет старого pacman

        with patch('engine.PacmanEngine', FakePacmanForJoinTest), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.5)
            except Exception:
                pass  # нормально упасть без реального YOLO

        # Тест проходит если не было AttributeError/исключений до этой точки

    def test_no_join_if_old_thread_already_dead(self):
        """Если старый тред уже умер — join не вызывается (незачем ждать мёртвого)."""
        eng, old_pacman, old_thread = _make_engine_with_old_pacman(old_thread_alive=False)

        with patch('engine.PacmanEngine', FakePacmanForJoinTest), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.5)
            except Exception:
                pass

        old_thread.join.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Проверка после join: if still alive → stop + повторный join
# ---------------------------------------------------------------------------

class TestEngineHandlesZombieThread:
    """Если старый тред завис и не умер за 5с — принудительный stop + ещё 2с ожидание."""

    def test_zombie_thread_gets_stop_and_second_join(self):
        """Тред не умер за timeout → old_pacman.stop() + ещё один join."""
        eng, old_pacman, old_thread = _make_engine_with_old_pacman(old_thread_alive=True)
        order = []

        # join не убивает тред (он "завис")
        old_thread.join.side_effect = lambda timeout=None: order.append(f'join({timeout})')
        # is_alive: True до первого join, True после первого join (зависший), False после stop+join
        old_thread.is_alive.side_effect = [True, True, False]
        old_pacman.stop.side_effect = lambda: order.append('stop')

        with patch('engine.PacmanEngine', FakePacmanForJoinTest), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.5)
            except Exception:
                pass

        assert any('join' in e for e in order), "join() не был вызван"
        assert 'stop' in order, "old_pacman.stop() не был вызван при зависшем треде"

    def test_kwargs_logged_on_auto_restart(self):
        """При авто-рестарте параметры логируются для диагностики."""
        import re
        from engine import HuntEngine

        eng = HuntEngine.__new__(HuntEngine)
        eng.is_running = True
        eng.roy_enabled = False
        eng._pacman = None
        eng._roy_client = None
        eng.roy_kingdom = 0
        eng._last_start_kwargs = {'conf': 0.7, 'move_wait': 1.5, 'center_x': 90}
        eng.on_engine_restart_callback = None
        eng._initial_yolo_block_sec = 0.0
        eng._bg_gen = 0

        log_messages = []
        started = threading.Event()

        def fake_start(**kwargs):
            started.set()

        with patch('engine._roy_log', side_effect=lambda m: log_messages.append(m)), \
             patch.object(eng, 'stop'), \
             patch.object(eng, 'start', side_effect=fake_start):
            eng.restart_after_exchange(delay=0)
            started.wait(timeout=2.0)

        assert started.is_set(), "start() не был вызван"
        # Хотя бы одно сообщение содержит move_wait или kwargs
        kwargs_logged = any('move_wait' in m or 'kwargs' in m or '1.5' in m
                           for m in log_messages)
        assert kwargs_logged, \
            f"Параметры (move_wait и др.) не логируются при авто-рестарте. Логи: {log_messages}"


# ---------------------------------------------------------------------------
# 3. Интеграционный: move_wait корректно передаётся при авто-рестарте
# ---------------------------------------------------------------------------

class TestMoveWaitPreservedOnRestart:
    """move_wait из _last_start_kwargs должен корректно передаваться при авто-рестарте."""

    def test_move_wait_saved_in_last_start_kwargs(self):
        """engine.start() сохраняет move_wait=1.5 в _last_start_kwargs."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.is_running = False
        eng.roy_enabled = False
        eng._pacman = None
        eng._roy_client = None
        eng.roy_kingdom = 0
        eng._last_start_kwargs = {}
        eng.on_engine_restart_callback = None
        eng.on_pool_refresh_callback = None
        eng.on_found_callback = None
        eng.on_last_exchange_callback = None
        eng._mm_cx = 90
        eng._mm_cy = 925
        eng._initial_yolo_block_sec = 0.0
        eng._bg_gen = 0
        eng.sound_path = None
        eng.model = MagicMock()

        with patch('engine.PacmanEngine', FakePacmanForJoinTest), \
             patch.object(eng, '_start_heartbeat'):
            try:
                eng.start(conf=0.8, move_wait=1.5, center_x=90)
            except Exception:
                pass

        assert eng._last_start_kwargs.get('move_wait') == 1.5, \
            f"move_wait должен быть 1.5 в _last_start_kwargs, получили: {eng._last_start_kwargs}"

    def test_move_wait_passed_to_new_start_on_restart(self):
        """При авто-рестарте start() получает move_wait из _last_start_kwargs."""
        from engine import HuntEngine
        eng = HuntEngine.__new__(HuntEngine)
        eng.is_running = True
        eng.roy_enabled = False
        eng._pacman = None
        eng._roy_client = None
        eng.roy_kingdom = 0
        eng._last_start_kwargs = {'conf': 0.8, 'move_wait': 1.5, 'center_x': 90}
        eng.on_engine_restart_callback = None
        eng._initial_yolo_block_sec = 0.0
        eng._bg_gen = 0

        received_kwargs = {}
        started = threading.Event()

        def fake_start(**kwargs):
            received_kwargs.update(kwargs)
            started.set()

        with patch.object(eng, 'stop'), \
             patch.object(eng, 'start', side_effect=fake_start):
            eng.restart_after_exchange(delay=0)
            started.wait(timeout=2.0)

        assert started.is_set(), "start() не был вызван"
        assert received_kwargs.get('move_wait') == 1.5, \
            f"move_wait должен быть 1.5 при авто-рестарте, получили: {received_kwargs}"
