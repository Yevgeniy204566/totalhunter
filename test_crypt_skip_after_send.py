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
        order.append('skip')

    def fake_send(*a, **k):
        order.append('send')
        return send_ok

    with patch.object(hunter, '_scroll_and_find', side_effect=fake_find), \
            patch.object(hunter, '_pre_skip', side_effect=fake_skip), \
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
        assert order == ['skip', 'search', 'send']

    def test_every_following_captain_skips_once(self):
        h = make_hunter()
        order = []
        for _ in range(3):
            run_cycle(h, order)
        assert order == ['search', 'send', 'skip', 'search', 'send', 'skip', 'search', 'send']

    def test_skip_is_once_per_cycle_not_twice(self):
        h = make_hunter()
        order = []
        run_cycle(h, order)
        order.clear()
        h._detect_fail_streak = 2      # и провал детекции, и отправка — прокрутка всё равно одна
        run_cycle(h, order)
        assert order.count('skip') == 1

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
        assert order == ['skip', 'search', 'send']

    def test_flag_is_consumed_by_the_skip(self):
        h = make_hunter()
        run_cycle(h, [])
        assert h._skip_next_search is True
        run_cycle(h, [], send_ok=False)
        assert h._skip_next_search is False


class TestPreSkipIsExactlyOneScroll:
    """Владелец 2026-09-21: «после неудачи идут три прокрутки, а нам надо одну прокрутку каждый раз».
    Одна прокрутка = тот же шаг (три вызова колеса подряд), что делает поиск склепа в _scroll_and_find."""

    def _run_pre_skip(self):
        import numpy as np
        h = make_hunter()
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False), \
                patch('crypt_hunter.pyautogui.size', return_value=(1920, 1080)), \
                patch('crypt_hunter.pyautogui.moveTo'), \
                patch('crypt_hunter.pyautogui.scroll') as scroll, \
                patch.object(h, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)), \
                patch.object(h, '_status') as status, \
                patch.object(h, '_interruptible_sleep'), \
                patch.object(h, '_reset_search'):
            h._pre_skip()
        return scroll, status

    def test_one_scroll_step_is_three_wheel_calls_not_nine(self):
        scroll, _status = self._run_pre_skip()
        assert scroll.call_count == 3

    def test_status_text_says_one_scroll(self):
        _scroll, status = self._run_pre_skip()
        assert "3 скролла" not in status.call_args_list[0][0][0]

    def test_still_resets_the_search_when_the_list_did_not_move(self):
        import numpy as np
        h = make_hunter()
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False), \
                patch('crypt_hunter.pyautogui.size', return_value=(1920, 1080)), \
                patch('crypt_hunter.pyautogui.moveTo'), \
                patch('crypt_hunter.pyautogui.scroll'), \
                patch.object(h, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)), \
                patch.object(h, '_status'), \
                patch.object(h, '_interruptible_sleep'), \
                patch.object(h, '_reset_search') as reset:
            h._pre_skip()
        reset.assert_called_once()          # кадры до/после одинаковые — список уже в конце
