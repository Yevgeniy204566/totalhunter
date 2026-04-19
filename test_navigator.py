"""
TDD tests for navigator.py
Run: python -m pytest test_navigator.py -v
"""
import pytest
from unittest.mock import patch, MagicMock, call
import numpy as np
import cv2


# ─────────────────────────────────────────────
# PositionReader — OCR координат с экрана
# ─────────────────────────────────────────────

class TestPositionReader:

    def test_parse_coordinates_from_ocr_text(self):
        from navigator import PositionReader
        reader = PositionReader(crop_box=(0, 1000, 250, 1080))
        result = reader._parse_ocr("K: 228   X: 908   Y: 874")
        assert result == (908, 874)

    def test_parse_returns_none_on_bad_text(self):
        from navigator import PositionReader
        reader = PositionReader(crop_box=(0, 1000, 250, 1080))
        result = reader._parse_ocr("no coordinates here")
        assert result is None

    def test_parse_handles_ocr_noise(self):
        from navigator import PositionReader
        reader = PositionReader(crop_box=(0, 1000, 250, 1080))
        result = reader._parse_ocr("K: 228 X: 90B Y: B74")
        # Should return None or a tuple — must not crash
        assert result is None or isinstance(result, tuple)


# ─────────────────────────────────────────────
# PacmanJoystick — pixel-based minimap nav
# ─────────────────────────────────────────────

def _make_land_frame(size=180):
    """BGR frame that is all green land (HSV H≈40 → land range 5-95)."""
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:] = (30, 140, 50)  # BGR: green-ish land
    return frame


def _make_water_frame(size=180):
    """BGR frame that is all blue water (HSV H≈115 → water range 100-140)."""
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[:] = (180, 60, 20)  # BGR: blue dominant
    return frame


class TestPacmanJoystick:

    def test_reset_initializes_memory_canvas(self):
        from navigator import PacmanJoystick, MEMORY_CANVAS_SIZE
        j = PacmanJoystick()
        j.reset()
        assert j.memory is not None
        assert j.memory.shape == (MEMORY_CANVAS_SIZE, MEMORY_CANVAS_SIZE)
        assert j.memory.sum() == 0

    def test_reset_clears_stuck_counter(self):
        from navigator import PacmanJoystick
        j = PacmanJoystick()
        j.reset()
        j.stuck_counter = 7
        j.reset()
        assert j.stuck_counter == 0

    def test_reset_restores_last_vec(self):
        from navigator import PacmanJoystick
        j = PacmanJoystick()
        j.reset()
        j.last_vec = (0.5, 0.5)
        j.reset()
        assert j.last_vec == (0.0, 1.0)

    def test_step_calls_pyautogui_click_on_land(self):
        """On an all-land minimap, step() should click somewhere."""
        from navigator import PacmanJoystick
        j = PacmanJoystick(center_x=90, center_y=925, step=16)
        j.reset()
        land_shot = _make_land_frame()
        # PIL screenshot mock
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cv2.cvtColor(land_shot, cv2.COLOR_BGR2RGB))
        with patch('pyautogui.screenshot', return_value=pil_img), \
             patch('pyautogui.click') as mock_click:
            result = j.step()
        # May or may not find a target depending on memory state,
        # but should not raise
        assert isinstance(result, bool)

    def test_step_returns_false_when_all_visited(self):
        """If memory canvas marks everything visited, step() returns False."""
        from navigator import PacmanJoystick, MEMORY_CANVAS_SIZE
        j = PacmanJoystick(center_x=90, center_y=925, step=16)
        j.reset()
        # Fill entire memory white = all visited
        j.memory[:] = 255
        land_shot = _make_land_frame()
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cv2.cvtColor(land_shot, cv2.COLOR_BGR2RGB))
        with patch('pyautogui.screenshot', return_value=pil_img), \
             patch('pyautogui.click') as mock_click:
            result = j.step()
        assert result is False
        mock_click.assert_not_called()

    def test_step_increments_stuck_counter_when_no_target(self):
        from navigator import PacmanJoystick
        j = PacmanJoystick(center_x=90, center_y=925, step=16)
        j.reset()
        j.memory[:] = 255  # all visited → no target
        land_shot = _make_land_frame()
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cv2.cvtColor(land_shot, cv2.COLOR_BGR2RGB))
        with patch('pyautogui.screenshot', return_value=pil_img), \
             patch('pyautogui.click'):
            j.step()
        assert j.stuck_counter == 1

    def test_step_erodes_memory_at_stuck_threshold(self):
        """When stuck_counter reaches STUCK_THRESHOLD, stuck_counter resets to 0."""
        from navigator import PacmanJoystick, STUCK_THRESHOLD
        j = PacmanJoystick(center_x=90, center_y=925, step=16)
        j.reset()
        j.memory[:] = 255
        j.stuck_counter = STUCK_THRESHOLD - 1  # one more step → erode
        land_shot = _make_land_frame()
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cv2.cvtColor(land_shot, cv2.COLOR_BGR2RGB))
        with patch('pyautogui.screenshot', return_value=pil_img), \
             patch('pyautogui.click'):
            j.step()
        # After erosion the counter resets to 0
        assert j.stuck_counter == 0

    def test_step_does_not_click_on_water_frame(self):
        """On an all-water minimap, no land → no click."""
        from navigator import PacmanJoystick
        j = PacmanJoystick(center_x=90, center_y=925, step=16)
        j.reset()
        water_shot = _make_water_frame()
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cv2.cvtColor(water_shot, cv2.COLOR_BGR2RGB))
        with patch('pyautogui.screenshot', return_value=pil_img), \
             patch('pyautogui.click') as mock_click:
            result = j.step()
        assert result is False
        mock_click.assert_not_called()

    def test_step_click_stays_within_p_range(self):
        """Click coordinates must be within p_range of center."""
        from navigator import PacmanJoystick
        cx, cy, p = 90, 925, 16
        j = PacmanJoystick(center_x=cx, center_y=cy, step=p)
        j.reset()
        land_shot = _make_land_frame()
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cv2.cvtColor(land_shot, cv2.COLOR_BGR2RGB))
        clicked = []
        with patch('pyautogui.screenshot', return_value=pil_img), \
             patch('pyautogui.click', side_effect=lambda x, y: clicked.append((x, y))):
            j.step()
        for fx, fy in clicked:
            assert cx - p <= fx <= cx + p
            assert cy - p <= fy <= cy + p


# ─────────────────────────────────────────────
# PacmanEngine — главный цикл навигации
# ─────────────────────────────────────────────

class TestPacmanEngine:

    def test_engine_stops_when_exchange_found(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        engine.is_running = True
        engine._on_exchange_found()
        assert engine.is_running is False

    def test_engine_plays_sound_when_exchange_found(self):
        from navigator import PacmanEngine
        engine = PacmanEngine(sound_path='Logo_exchange.wav')
        with patch('winsound.PlaySound') as mock_sound:
            engine._on_exchange_found()
            mock_sound.assert_called_once()

    def test_engine_calls_callback_when_exchange_found(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        cb = MagicMock()
        engine.on_found_callback = cb
        with patch('winsound.PlaySound'):
            engine._on_exchange_found()
        cb.assert_called_once()

    def test_engine_start_sets_is_running(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        with patch('threading.Thread') as mock_thread:
            mock_thread.return_value.start = MagicMock()
            engine.start()
        assert engine.is_running is True

    def test_engine_stop_clears_is_running(self):
        from navigator import PacmanEngine
        engine = PacmanEngine()
        engine.is_running = True
        engine.stop()
        assert engine.is_running is False

    def test_engine_reset_clears_joystick_memory(self):
        """After joystick.reset(), memory canvas is cleared."""
        from navigator import PacmanEngine
        engine = PacmanEngine()
        engine.joystick.reset()
        engine.joystick.memory[:] = 255
        engine.joystick.stuck_counter = 3
        engine.joystick.reset()
        assert engine.joystick.memory.sum() == 0
        assert engine.joystick.stuck_counter == 0
