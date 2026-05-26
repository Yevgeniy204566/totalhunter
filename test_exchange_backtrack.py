"""
TDD — _exchange_detected backtracking logic.

Scenarios:
  A: fresh YOLO finds → click at fresh coords, no backtrack step
  B: fresh YOLO misses → _backtrack_step → 2nd YOLO finds → click at 2nd coords
  C: fresh YOLO misses → _backtrack_step → 2nd YOLO misses → return, no click

Run: python -m pytest test_exchange_backtrack.py -v
"""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


_FAKE_BGRA = np.zeros((100, 100, 4), dtype=np.uint8)


def _box(x1=100., y1=100., x2=200., y2=200., conf=0.9):
    """Minimal YOLO box mock."""
    b = MagicMock()
    b.xyxy.cpu.return_value.tolist.return_value = [[x1, y1, x2, y2]]
    b.conf = [conf]
    return b


def _yolo_seq(*boxes):
    """yolo_model whose predict() yields boxes in order (None = miss)."""
    it = iter(boxes)

    def _predict(*a, **kw):
        val = next(it, None)
        r = MagicMock()
        r.boxes = [val] if val is not None else []
        return [r]

    m = MagicMock()
    m.predict.side_effect = _predict
    return m


def _make_engine(yolo):
    from navigator import PacmanEngine, CoastalSnakeNavigator

    eng = PacmanEngine.__new__(PacmanEngine)
    eng.sound_path = ''
    eng.on_found_callback = None
    eng._yolo_unblock_time = 0.0
    eng._suppressing_esc = False
    eng.restart_callback = None
    eng._thread = None
    eng.conf = 0.7
    eng.yolo_model = yolo

    j = CoastalSnakeNavigator.__new__(CoastalSnakeNavigator)
    j._last_move_vec = (1.0, 0.0)   # last step was rightward (DIVING)
    j._footprint_enabled = False
    j.center_x = 90
    j.center_y = 925
    j.p_range_x = 23
    j.p_range_y = 13
    eng.joystick = j
    return eng


def _fake_mss_cm():
    """Context-manager mock for mss.mss()."""
    sct = MagicMock()
    sct.monitors = [None, MagicMock()]
    sct.grab.return_value = _FAKE_BGRA
    cm = MagicMock()
    cm.__enter__.return_value = sct
    cm.__exit__.return_value = False
    return cm


def _run(eng, initial_box):
    """Call _exchange_detected with all I/O mocked out."""
    from navigator import CoastalSnakeNavigator
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    with (
        patch('navigator.time.sleep'),
        patch('navigator.pyautogui.click') as mock_click,
        patch('navigator.pyautogui.press'),
        patch('navigator.winsound.PlaySound'),
        patch('navigator.winsound.Beep'),
        patch('navigator.PacmanEngine._trigger_yolo_block'),
        patch('mss.mss', return_value=_fake_mss_cm()),
        patch.object(CoastalSnakeNavigator, '_click_vec') as mock_jstk,
        patch('debug_reporter.report_find', MagicMock()),
        patch('debug_reporter.report_dialog', MagicMock()),
        patch('auth.get_hwid', return_value='test-hwid'),
    ):
        eng._exchange_detected(initial_box, frame=frame)

    return mock_click, mock_jstk


class TestExchangeDetectedBacktrack:

    def test_fresh_found_no_backtrack(self):
        """Scenario A: fresh YOLO hits → one click at fresh coords, zero backtrack steps."""
        fresh = _box(300., 200., 400., 300.)
        eng = _make_engine(_yolo_seq(fresh))
        initial = _box(50., 50., 150., 150.)

        mock_click, mock_jstk = _run(eng, initial)

        assert mock_click.call_count == 1, "должен быть ровно один клик"
        assert mock_jstk.call_count == 0, "шаг назад не нужен — биржа найдена сразу"
        cx, cy = mock_click.call_args[0]
        assert cx == 350                             # (300+400)//2
        assert cy == int(200 + (300 - 200) * 0.35)  # верхняя треть

    def test_miss_backtrack_found_clicks_second_coords(self):
        """Scenario B: first miss → backtrack → second hit → click at 2nd bbox."""
        second = _box(500., 400., 600., 500.)
        eng = _make_engine(_yolo_seq(None, second))
        initial = _box(50., 50., 150., 150.)

        mock_click, mock_jstk = _run(eng, initial)

        assert mock_click.call_count == 1, "клик должен быть — биржа нашлась на 2-м скане"
        assert mock_jstk.call_count == 1, "один шаг назад перед 2-м сканом"
        cx, cy = mock_click.call_args[0]
        assert cx == 550                             # (500+600)//2
        assert cy == int(400 + (500 - 400) * 0.35)

    def test_double_miss_no_click(self):
        """Scenario C: both scans miss → backtrack tried once → no click, early return."""
        eng = _make_engine(_yolo_seq(None, None))
        initial = _box(50., 50., 150., 150.)

        mock_click, mock_jstk = _run(eng, initial)

        assert mock_click.call_count == 0, "ложное срабатывание — кликать не надо"
        assert mock_jstk.call_count == 1, "один шаг назад был предпринят"

    def test_backtrack_uses_inverted_last_move(self):
        """_backtrack_step inverts _last_move_vec and calls _click_vec."""
        from navigator import PacmanEngine, CoastalSnakeNavigator

        eng = PacmanEngine.__new__(PacmanEngine)
        j = CoastalSnakeNavigator.__new__(CoastalSnakeNavigator)
        j._last_move_vec = (0.6, 0.8)   # arbitrary normalised direction
        j._footprint_enabled = False
        j.center_x = 90; j.center_y = 925
        j.p_range_x = 23; j.p_range_y = 13
        eng.joystick = j

        with patch.object(CoastalSnakeNavigator, '_click_vec') as mock_cv:
            eng._backtrack_step()

        assert mock_cv.call_count == 1
        dx, dy = mock_cv.call_args[0]
        assert dx == pytest.approx(-0.6)
        assert dy == pytest.approx(-0.8)

    def test_backtrack_noop_when_no_last_move(self):
        """_backtrack_step does nothing if _last_move_vec is zero (fresh engine)."""
        from navigator import PacmanEngine, CoastalSnakeNavigator

        eng = PacmanEngine.__new__(PacmanEngine)
        j = CoastalSnakeNavigator.__new__(CoastalSnakeNavigator)
        j._last_move_vec = (0.0, 0.0)
        eng.joystick = j

        with patch.object(CoastalSnakeNavigator, '_click_vec') as mock_cv:
            eng._backtrack_step()

        assert mock_cv.call_count == 0
