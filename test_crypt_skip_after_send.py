"""Склепы: список всегда прокручивается один раз между отправками капитанов (запрос владельца 2026-09-21).

Проблема: при отправке нескольких капитанов подряд бот брал ОДИН И ТОТ ЖЕ склеп для разных капитанов —
список между циклами не сбрасывается и поиск начинается с места, где только что отправленный склеп ещё виден.
Прокрутка `_pre_skip()` (пропустить ~5 позиций) включалась только после НЕУДАЧНОЙ детекции; теперь и после
успешной отправки капитана."""

from unittest.mock import MagicMock, patch


def make_hunter():
    with patch('crypt_hunter.YOLO', return_value=MagicMock()):
        from crypt_hunter import CryptHunter
        h = CryptHunter.__new__(CryptHunter)
        h.is_running = True
        h._conf = 0.7
        h._selected = ['Ordinary_1']
        h._accelerations = 0
        h._max_march_sec = 0.0
        h._break_sec = 0
        h._model = MagicMock()
        h.on_status_callback = None
        h.on_found_callback = None
        h.on_countdown_callback = None
        h._detect_fail_streak = 0
        h._log_file = None
        h._periodic_reset_sec = None
        h._next_periodic_reset_at = None
        return h


def run_cycle(hunter, order, send_ok=True, detect_ok=True):
    def fake_find(*a, **k):
        order.append('search')
        return 'Ordinary_1'

    def fake_skip():
        order.append('skip3')       # старая логика после неудачи: три прокрутки

    def fake_skip_one():
        order.append('skip1')       # новая: одна прокрутка после отправки

    def fake_send(*a, **k):
        order.append('send')
        return send_ok

    with patch.object(hunter, '_scroll_and_find', side_effect=fake_find), \
            patch.object(hunter, '_pre_skip', side_effect=fake_skip), \
            patch.object(hunter, '_skip_one_scroll', side_effect=fake_skip_one), \
            patch.object(hunter, '_reset_search'), \
            patch.object(hunter, '_interruptible_sleep'), \
            patch.object(hunter, '_open_watchtower'), \
            patch.object(hunter, '_select_crypts_tab'), \
            patch.object(hunter, '_detect_on_map', return_value=detect_ok), \
            patch.object(hunter, '_send_captain', side_effect=fake_send), \
            patch.object(hunter, '_click_captain_event'), \
            patch.object(hunter, '_accelerate', return_value=0.0), \
            patch.object(hunter, '_close_dialog'), \
            patch.object(hunter, '_random_pause'), \
            patch('crypt_hunter.time.monotonic', return_value=1.0):
        hunter._run_cycle()


class TestSkipAfterSend:
    def test_first_cycle_after_start_does_not_skip(self):
        h = make_hunter()
        order = []
        run_cycle(h, order)
        assert order == ['search', 'send']

    def test_second_cycle_skips_once_before_the_search(self):
        h = make_hunter()
        order = []
        run_cycle(h, order)          # 1-й капитан отправлен
        order.clear()
        run_cycle(h, order)          # 2-й капитан
        assert order == ['skip1', 'search', 'send']

    def test_every_following_captain_skips_once(self):
        h = make_hunter()
        order = []
        for _ in range(3):
            run_cycle(h, order)
        assert order == ['search', 'send', 'skip1', 'search', 'send', 'skip1', 'search', 'send']

    def test_after_a_failed_detection_the_old_three_scroll_skip_runs_and_no_extra_scroll(self):
        """Старая логика не тронута: после неудачи — _pre_skip (3 шага), а новая одна прокрутка не добавляется."""
        h = make_hunter()
        order = []
        run_cycle(h, order)
        order.clear()
        h._detect_fail_streak = 2
        run_cycle(h, order)
        assert order == ['skip3', 'search', 'send']
        assert 'skip1' not in order

    def test_failed_send_does_not_request_a_skip(self):
        """Капитан не отправлен — склеп не занят, повторно брать его можно."""
        h = make_hunter()
        order = []
        run_cycle(h, order, send_ok=False)
        order.clear()
        run_cycle(h, order)
        assert order == ['search', 'send']

    def test_failed_detection_keeps_the_old_skip_behavior(self):
        h = make_hunter()
        order = []
        run_cycle(h, order, detect_ok=False)
        assert h._detect_fail_streak == 1
        order.clear()
        run_cycle(h, order)
        assert order == ['skip3', 'search', 'send']

    def test_flag_is_consumed_by_the_skip(self):
        h = make_hunter()
        run_cycle(h, [])
        assert h._skip_next_search is True
        run_cycle(h, [], send_ok=False)
        assert h._skip_next_search is False


class TestScrollAmounts:
    """Владелец 2026-09-21: после неудачи прокрутка остаётся прежней (три шага), а для повседневной работы —
    новая: ровно ОДНА прокрутка (один шаг = три вызова колеса подряд, как в поиске)."""

    def _run(self, method_name):
        import numpy as np
        h = make_hunter()
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False), \
                patch('crypt_hunter.pyautogui.size', return_value=(1920, 1080)), \
                patch('crypt_hunter.pyautogui.moveTo'), \
                patch('crypt_hunter.pyautogui.scroll') as scroll, \
                patch.object(h, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)), \
                patch.object(h, '_status') as status, \
                patch.object(h, '_interruptible_sleep'), \
                patch.object(h, '_reset_search') as reset:
            getattr(h, method_name)()
        return scroll, status, reset

    def test_old_pre_skip_is_untouched_three_steps_nine_wheel_calls(self):
        scroll, status, _reset = self._run('_pre_skip')
        assert scroll.call_count == 9
        assert "3 скролла" in status.call_args_list[0][0][0]

    def test_new_skip_is_exactly_one_step_three_wheel_calls(self):
        scroll, _status, _reset = self._run('_skip_one_scroll')
        assert scroll.call_count == 3

    def test_new_skip_resets_the_search_when_the_list_did_not_move(self):
        _scroll, _status, reset = self._run('_skip_one_scroll')
        reset.assert_called_once()          # кадры до/после одинаковые — список уже в конце

    def test_new_skip_does_not_reset_when_the_list_moved(self):
        import numpy as np
        h = make_hunter()
        shots = [np.zeros((1080, 1920, 3), dtype=np.uint8), np.full((1080, 1920, 3), 200, dtype=np.uint8)]
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False), \
                patch('crypt_hunter.pyautogui.size', return_value=(1920, 1080)), \
                patch('crypt_hunter.pyautogui.moveTo'), \
                patch('crypt_hunter.pyautogui.scroll'), \
                patch.object(h, '_screenshot', side_effect=shots), \
                patch.object(h, '_status'), \
                patch.object(h, '_interruptible_sleep'), \
                patch.object(h, '_reset_search') as reset:
            h._skip_one_scroll()
        reset.assert_not_called()

    def test_new_skip_clears_nothing_about_failed_detection(self):
        """_skip_one_scroll не трогает счётчик неудач — он принадлежит старой логике."""
        h = make_hunter()
        h._detect_fail_streak = 0
        self._run('_skip_one_scroll')
        assert h._detect_fail_streak == 0
