"""
TDD tests for calibration.py
Run: python -m pytest test_calibration.py -v
"""
import pytest
from unittest.mock import patch, MagicMock, call
import numpy as np


class TestCalibrator:

    def test_calibrator_reads_initial_position(self):
        """Калибровщик читает стартовую X/Y позицию"""
        from calibration import Calibrator
        cal = Calibrator()
        mock_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        with patch.object(cal.reader, 'read', return_value=(908, 874)):
            pos = cal.read_position(mock_screen)
        assert pos == (908, 874)

    def test_calibrator_raises_if_position_unreadable(self):
        """Если координаты не читаются — понятная ошибка"""
        from calibration import Calibrator
        cal = Calibrator()
        mock_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        with patch.object(cal.reader, 'read', return_value=None):
            with pytest.raises(RuntimeError, match="координаты"):
                cal.read_position(mock_screen)

    def test_calibrate_screen_w_from_two_positions(self):
        """SCREEN_W = разница X после клика джойстика вправо"""
        from calibration import Calibrator
        cal = Calibrator()
        result = cal.calc_screen_size(before=(908, 874), after=(958, 874), direction='RIGHT')
        assert result == 50

    def test_calibrate_screen_h_from_two_positions(self):
        """SCREEN_H = разница Y после клика джойстика вниз"""
        from calibration import Calibrator
        cal = Calibrator()
        result = cal.calc_screen_size(before=(908, 874), after=(908, 909), direction='DOWN')
        assert result == 35

    def test_calc_screen_size_uses_abs_value(self):
        """Разница всегда положительная"""
        from calibration import Calibrator
        cal = Calibrator()
        result = cal.calc_screen_size(before=(958, 874), after=(908, 874), direction='LEFT')
        assert result == 50

    def test_calc_screen_size_raises_on_no_movement(self):
        """Если позиция не изменилась — ошибка (джойстик не сработал)"""
        from calibration import Calibrator
        cal = Calibrator()
        with pytest.raises(RuntimeError, match="не изменилась"):
            cal.calc_screen_size(before=(908, 874), after=(908, 874), direction='RIGHT')

    def test_save_creates_config_file(self, tmp_path):
        """Сохранение результатов в JSON файл"""
        from calibration import Calibrator
        cal = Calibrator()
        config_path = tmp_path / "nav_config.json"
        cal.save(
            screen_w=50, screen_h=35,
            center_x=90, center_y=925,
            step=17,
            path=str(config_path)
        )
        assert config_path.exists()

    def test_save_config_has_correct_values(self, tmp_path):
        """Сохранённый JSON содержит правильные значения"""
        import json
        from calibration import Calibrator
        cal = Calibrator()
        config_path = tmp_path / "nav_config.json"
        cal.save(screen_w=50, screen_h=35, center_x=90, center_y=925, step=17, path=str(config_path))
        data = json.loads(config_path.read_text())
        assert data['screen_w'] == 50
        assert data['screen_h'] == 35
        assert data['center_x'] == 90
        assert data['center_y'] == 925
        assert data['step'] == 17

    def test_load_config_restores_values(self, tmp_path):
        """Загрузка конфига восстанавливает все параметры"""
        import json
        from calibration import Calibrator
        config_path = tmp_path / "nav_config.json"
        config_path.write_text(json.dumps({
            'screen_w': 50, 'screen_h': 35,
            'center_x': 90, 'center_y': 925, 'step': 17
        }))
        cal = Calibrator()
        data = cal.load(str(config_path))
        assert data['screen_w'] == 50
        assert data['screen_h'] == 35

    def test_run_calibration_moves_joystick_right_then_down(self):
        """run() делает 2 хода: вправо и вниз"""
        from calibration import Calibrator
        cal = Calibrator()
        # 3 скриншота: до RIGHT, после RIGHT, после DOWN
        screens = [np.zeros((1080, 1920, 3), dtype=np.uint8)] * 3
        # 3 чтения координат: старт → после RIGHT → после DOWN
        positions = [(908, 874), (958, 874), (958, 909)]

        with patch.object(cal.reader, 'read', side_effect=positions), \
             patch.object(cal.joystick, 'move') as mock_move, \
             patch('calibration.grab_screen', side_effect=screens), \
             patch.object(cal, 'save'):
            result = cal.run()

        calls = [c[0][0] for c in mock_move.call_args_list]
        assert 'RIGHT' in calls
        assert 'DOWN' in calls
        assert result['screen_w'] == 50
        assert result['screen_h'] == 35

    def test_run_returns_calibration_dict(self):
        """run() возвращает словарь с screen_w, screen_h, center_x, center_y, step"""
        from calibration import Calibrator
        cal = Calibrator()
        screens = [np.zeros((1080, 1920, 3), dtype=np.uint8)] * 3
        positions = [(908, 874), (958, 874), (958, 909)]

        with patch.object(cal.reader, 'read', side_effect=positions), \
             patch.object(cal.joystick, 'move'), \
             patch('calibration.grab_screen', side_effect=screens), \
             patch.object(cal, 'save'):
            result = cal.run()

        assert set(result.keys()) >= {'screen_w', 'screen_h', 'center_x', 'center_y', 'step'}
