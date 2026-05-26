"""
TDD: защита от самоостановки бота при нажатии ESC в шаге 11 _exchange_detected.

Проблема: pyautogui.press('escape') в шаге 11 (закрытие диалога биржи) срабатывает
в keyboard.hook → _emergency_stop() → бот останавливает себя.
Решение: флаг _suppressing_esc в PacmanEngine — хук игнорирует автоматические нажатия.

Run: python -m pytest test_exchange_esc_guard.py -v
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


class TestEscSuppression:
    """PacmanEngine._suppressing_esc защищает от самоостановки при ESC на шаге 11."""

    def test_suppressing_esc_in_init(self):
        """PacmanEngine.__init__ устанавливает _suppressing_esc=False."""
        from navigator import PacmanEngine
        with patch('navigator.CoastalSnakeNavigator'):
            eng = PacmanEngine(yolo_model=None)
        assert hasattr(eng, '_suppressing_esc'), "_suppressing_esc должен быть атрибутом PacmanEngine"
        assert eng._suppressing_esc is False

    def test_emergency_stop_bypassed_when_suppressing(self):
        """Имитация _esc_handler: стоп НЕ срабатывает когда _suppressing_esc=True."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._suppressing_esc = True
        # логика в main.py: if pacman and getattr(pacman, '_suppressing_esc', False): return
        should_stop = not getattr(eng, '_suppressing_esc', False)
        assert not should_stop, "При _suppressing_esc=True аварийный стоп не должен срабатывать"

    def test_emergency_stop_fires_when_not_suppressed(self):
        """Имитация _esc_handler: стоп СРАБАТЫВАЕТ когда _suppressing_esc=False."""
        from navigator import PacmanEngine
        eng = PacmanEngine.__new__(PacmanEngine)
        eng._suppressing_esc = False
        should_stop = not getattr(eng, '_suppressing_esc', False)
        assert should_stop, "При _suppressing_esc=False аварийный стоп должен срабатывать"

    def test_exchange_detected_sets_flag_during_esc(self):
        """В шаге 11 _suppressing_esc=True в момент нажатия ESC; False — после."""
        from navigator import PacmanEngine

        with patch('navigator.CoastalSnakeNavigator'):
            eng = PacmanEngine(yolo_model=MagicMock())
        eng.on_found_callback = None

        # Подготовка mock-бокса биржи
        mock_box = MagicMock()
        mock_box.conf = [0.9]
        mock_box.xyxy.cpu.return_value.tolist.return_value = [[100., 100., 200., 200.]]
        mock_box.__len__ = lambda s: 1
        mock_box.__getitem__ = lambda s, i: mock_box

        mock_r = MagicMock()
        mock_r.boxes = mock_box
        mock_r.boxes.__len__ = lambda s: 1
        mock_r.boxes.__getitem__ = lambda s, i: mock_box
        eng.yolo_model.predict.return_value = [mock_r]

        # Перехватываем каждый вызов pyautogui.press
        esc_flag_state = []

        def capture_press(key):
            if key == 'escape':
                esc_flag_state.append(eng._suppressing_esc)

        fake_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        fake_screen = np.zeros((100, 100, 4), dtype=np.uint8)

        mock_sct = MagicMock()
        mock_sct.monitors = [None, {'left': 0, 'top': 0, 'width': 100, 'height': 100}]
        mock_sct.grab.return_value = fake_screen
        mock_sct.__enter__ = lambda s: s
        mock_sct.__exit__ = MagicMock(return_value=False)

        with patch('mss.mss', return_value=mock_sct), \
             patch('cv2.cvtColor', return_value=fake_frame), \
             patch('pyautogui.click'), \
             patch('pyautogui.press', side_effect=capture_press), \
             patch('time.sleep'), \
             patch('winsound.Beep'), \
             patch('winsound.PlaySound'), \
             patch('debug_reporter.report_find'), \
             patch('debug_reporter.report_dialog'), \
             patch('auth.get_hwid', return_value='test_hwid'):
            eng._exchange_detected(mock_box)

        assert len(esc_flag_state) == 1, f"ESC нажат {len(esc_flag_state)} раз (ожидался 1)"
        assert esc_flag_state[0] is True, \
            f"_suppressing_esc в момент нажатия ESC = {esc_flag_state[0]}, ожидалось True"
        assert eng._suppressing_esc is False, \
            "После шага 11 _suppressing_esc должен вернуться в False"
