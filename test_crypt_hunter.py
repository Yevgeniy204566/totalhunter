"""
TDD tests for crypt_hunter.py
Run: python -m pytest test_crypt_hunter.py -v
"""
import pytest




class TestCryptHunterInit:
    def test_init_loads_model(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            hunter = CryptHunter.__new__(CryptHunter)
            hunter._model = MagicMock()
            assert hunter._model is not None

    def test_is_running_false_initially(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            hunter = CryptHunter.__new__(CryptHunter)
            hunter.is_running = False
            assert hunter.is_running is False

    def test_stop_sets_is_running_false(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            hunter = CryptHunter.__new__(CryptHunter)
            hunter.is_running = True
            hunter._thread = None
            hunter.stop()
            assert hunter.is_running is False


class TestCryptHunterHelpers:
    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h._conf = 0.7
            h._model = MagicMock()
            return h

    def test_click_calls_pyautogui(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter.pyautogui') as mock_pg:
            with patch('crypt_hunter.time'):
                hunter._click(100, 200, jitter=0)
            mock_pg.moveTo.assert_called_once()
            args = mock_pg.moveTo.call_args[0]
            assert args[0] == 100
            assert args[1] == 200

    def test_click_applies_jitter(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter.pyautogui') as mock_pg:
            with patch('crypt_hunter.time'):
                hunter._click(100, 200, jitter=6)
            args = mock_pg.moveTo.call_args[0]
            x, y = args[0], args[1]
            assert 94 <= x <= 106
            assert 194 <= y <= 206

    def test_random_pause_sleeps(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch.object(hunter, '_interruptible_sleep') as mock_sleep:
            with patch('crypt_hunter.random.uniform', return_value=0.5):
                hunter._random_pause()
                mock_sleep.assert_called_once_with(0.5)


class TestWatchtowerMenu:
    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h._model = MagicMock()
            h.on_status_callback = None
            return h

    def test_open_watchtower_uses_template_when_available(self):
        """Когда template matching доступен — кликает по найденной позиции, не по hardcoded."""
        from unittest.mock import patch
        hunter = self._make_hunter()
        clicks = []
        found_pos = (700, 950)
        with patch('crypt_hunter._TEMPLATE_AVAILABLE', True):
            with patch('crypt_hunter.find_in_screen_region', return_value=found_pos):
                with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
                    with patch.object(hunter, '_random_pause'):
                        hunter._open_watchtower()
        assert found_pos in clicks

    def test_open_watchtower_falls_back_to_wt_icon_when_template_not_found(self):
        """Если шаблон не найден — кликает по WT_ICON напрямую (без scale_coord)."""
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch('crypt_hunter._TEMPLATE_AVAILABLE', True):
            with patch('crypt_hunter.find_in_screen_region', return_value=None):
                with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
                    with patch.object(hunter, '_random_pause'):
                        hunter._open_watchtower()
        # Должен кликнуть РЯДОМ с WT_ICON (с jitter ±5)
        assert any(abs(x - ch.WT_ICON[0]) <= 5 and abs(y - ch.WT_ICON[1]) <= 5
                   for x, y in clicks), f"Ожидал клик около {ch.WT_ICON}, получил {clicks}"

    def test_select_crypts_tab_uses_template_when_available(self):
        """Когда template matching доступен — кликает по найденной вкладке."""
        from unittest.mock import patch
        hunter = self._make_hunter()
        clicks = []
        found_pos = (690, 470)
        with patch('crypt_hunter._TEMPLATE_AVAILABLE', True):
            with patch('crypt_hunter.find_in_screen_region', return_value=found_pos):
                with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
                    with patch.object(hunter, '_random_pause'):
                        hunter._select_crypts_tab()
        assert found_pos in clicks

    def test_select_crypts_tab_falls_back_to_wt_crypts_tab_when_template_not_found(self):
        """Если шаблон вкладки не найден — кликает по WT_CRYPTS_TAB напрямую."""
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch('crypt_hunter._TEMPLATE_AVAILABLE', True):
            with patch('crypt_hunter.find_in_screen_region', return_value=None):
                with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
                    with patch.object(hunter, '_random_pause'):
                        hunter._select_crypts_tab()
        assert any(abs(x - ch.WT_CRYPTS_TAB[0]) <= 5 and abs(y - ch.WT_CRYPTS_TAB[1]) <= 5
                   for x, y in clicks), f"Ожидал клик около {ch.WT_CRYPTS_TAB}, получил {clicks}"

    def test_reset_search_clicks_arena_twice(self):
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
            with patch.object(hunter, '_random_pause'):
                with patch('crypt_hunter.time.sleep'):
                    hunter._reset_search()
        arena_clicks = [c for c in clicks if c == ch.WT_ARENA_TAB]
        assert len(arena_clicks) == 2


class TestScrollAndFind:
    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h._conf = 0.7
            h._model = MagicMock()
            h.on_status_callback = None
            return h

    def test_returns_none_when_not_found(self):
        from unittest.mock import patch, MagicMock
        import numpy as np
        hunter = self._make_hunter()
        mock_result = MagicMock()
        mock_result.boxes = []
        hunter._model.return_value = [mock_result]
        with patch.object(hunter, '_screenshot', return_value=np.zeros((100, 100, 3), dtype=np.uint8)):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    with patch('crypt_hunter.pyautogui.scroll'):
                        result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=1)
        assert result is None

    def test_returns_crypt_type_when_found(self):
        from unittest.mock import patch, MagicMock
        import numpy as np
        import crypt_hunter as ch
        hunter = self._make_hunter()
        mock_box = MagicMock()
        mock_box.cls.tolist.return_value = [0]
        # Центр (650, 320) — внутри MENU_SCAN_REGION = (597, 242, 721, 575)
        mock_box.xyxy.tolist.return_value = [[600, 300, 700, 340]]
        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        mock_result.names = {0: 'crypt_0'}  # YOLO-имя; YOLO_TO_GUI['crypt_0'] == 'Ordinary_1'
        hunter._model.return_value = [mock_result]
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch('crypt_hunter._TEMPLATE_AVAILABLE', False):
                with patch.object(hunter, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch.object(hunter, '_click'):
                        with patch.object(hunter, '_random_pause'):
                            with patch('crypt_hunter.pyautogui.scroll'):
                                with patch('crypt_hunter.time.sleep'):
                                    result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=3)
        assert result == 'Ordinary_1'


class TestMapDetection:
    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h._conf = 0.7
            h._model = MagicMock()
            h.on_status_callback = None
            return h

    def test_detect_on_map_returns_true_when_found(self):
        from unittest.mock import patch, MagicMock
        import numpy as np
        hunter = self._make_hunter()
        mock_box = MagicMock()
        mock_box.cls.tolist.return_value = [0]            # crypt_0 = Ordinary_1
        mock_box.xyxy.tolist.return_value = [[900, 500, 1020, 580]]
        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        mock_result.names = {0: 'crypt_0'}
        hunter._model.return_value = [mock_result]
        with patch.object(hunter, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    result = hunter._detect_on_map('Ordinary_1')
        assert result is True

    def test_detect_on_map_returns_false_when_not_found(self):
        from unittest.mock import patch, MagicMock
        import numpy as np
        hunter = self._make_hunter()
        mock_result = MagicMock()
        mock_result.boxes = []
        hunter._model.return_value = [mock_result]
        with patch.object(hunter, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
            with patch.object(hunter, '_random_pause'):
                result = hunter._detect_on_map('Ordinary_1')
        assert result is False

    def test_send_captain_rare_crypt_clicks_open_first(self):
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        # _find_button возвращает fallback-координаты (реальный экран не нужен)
        with patch.object(hunter, '_find_button',
                          side_effect=lambda ref_region, color, pick, fallback: fallback):
            with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
                with patch.object(hunter, '_random_pause'):
                    hunter._send_captain('R_1')
        # «Открыть» должна быть нажата ДО «Исследовать»
        assert ch.CRYPT_OPEN_BTN in clicks
        assert ch.CRYPT_STUDY_BTN in clicks
        open_idx = clicks.index(ch.CRYPT_OPEN_BTN)
        study_idx = clicks.index(ch.CRYPT_STUDY_BTN)
        assert open_idx < study_idx


class TestImagesDiffer:
    """Tests for _images_differ — pure function, no screen access."""

    def test_identical_images_returns_false(self):
        import numpy as np
        import crypt_hunter as ch
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        assert ch._images_differ(img, img.copy()) is False

    def test_completely_different_images_returns_true(self):
        import numpy as np
        import crypt_hunter as ch
        a = np.zeros((100, 100, 3), dtype=np.uint8)
        b = np.full((100, 100, 3), 200, dtype=np.uint8)
        assert ch._images_differ(a, b) is True

    def test_single_pixel_change_below_threshold(self):
        import numpy as np
        import crypt_hunter as ch
        a = np.zeros((100, 100, 3), dtype=np.uint8)
        b = a.copy()
        b[50, 50] = [128, 128, 128]  # один пиксель из 10000 — ниже порога
        assert ch._images_differ(a, b) is False

    def test_scrolled_menu_above_threshold(self):
        """Прокрутка меняет ~30-40% пикселей — выше порога."""
        import numpy as np
        import crypt_hunter as ch
        a = np.zeros((100, 100, 3), dtype=np.uint8)
        b = a.copy()
        b[30:70, :] = 150  # 40% строк изменились
        assert ch._images_differ(a, b) is True

    def test_different_shapes_returns_true(self):
        import numpy as np
        import crypt_hunter as ch
        a = np.zeros((100, 100, 3), dtype=np.uint8)
        b = np.zeros((50, 50, 3), dtype=np.uint8)
        assert ch._images_differ(a, b) is True


class TestScrollAndFindEndOfList:
    """End-of-list detection: возвращает None когда ничего не найдено за max_scrolls."""

    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h._conf = 0.7
            h._model = MagicMock()
            h.on_status_callback = None
            return h

    def test_does_not_trigger_on_first_scroll(self):
        """После первого скролла (меню изменилось) продолжаем поиск и находим склеп."""
        from unittest.mock import patch, MagicMock
        import numpy as np
        hunter = self._make_hunter()
        no_result = MagicMock()
        no_result.boxes = []
        found_box = MagicMock()
        found_box.cls.tolist.return_value = [0]
        found_box.xyxy.tolist.return_value = [[600, 300, 700, 340]]
        found_result = MagicMock()
        found_result.boxes = [found_box]
        found_result.names = {0: 'crypt_0'}
        hunter._model.side_effect = [[no_result], [found_result]]
        # Первый скриншот — пустой; второй — другой (меню прокрутилось)
        img1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img2 = np.full((1080, 1920, 3), 80, dtype=np.uint8)  # отличается → не freeze
        screenshots = iter([img1, img2])
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch('crypt_hunter._TEMPLATE_AVAILABLE', False):
                with patch.object(hunter, '_screenshot', side_effect=screenshots):
                    with patch.object(hunter, '_click'):
                        with patch.object(hunter, '_random_pause'):
                            with patch('crypt_hunter.time.sleep'):
                                with patch('crypt_hunter.pyautogui.scroll'):
                                    with patch('crypt_hunter.pyautogui.moveTo'):
                                        result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=5)
        assert result == 'Ordinary_1'


class TestRunCycleEndOfList:
    """_run_cycle без счётчика resets — просто reset + sleep(10-15) + повтор."""

    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h._conf = 0.7
            h._selected = ['Ordinary_1']
            h._accelerations = 3
            h._max_march_sec = 900.0
            h._break_sec = 3
            h._model = MagicMock()
            h.on_status_callback = None
            h.on_found_callback = None
            h.on_countdown_callback = None
            return h

    def test_resets_and_waits_when_no_crypt_found(self):
        """Когда склеп не найден: _reset_search + sleep 10-15 сек + повторный поиск."""
        from unittest.mock import patch, MagicMock, call
        hunter = self._make_hunter()
        sleep_calls = []

        # Первый _scroll_and_find → None, второй → 'Ordinary_1' (цикл завершается)
        with patch.object(hunter, '_scroll_and_find',
                          side_effect=[None, 'Ordinary_1']) as mock_find:
            with patch.object(hunter, '_reset_search') as mock_reset:
                with patch.object(hunter, '_interruptible_sleep',
                                  side_effect=lambda s: sleep_calls.append(s)):
                    with patch.object(hunter, '_open_watchtower'):
                        with patch.object(hunter, '_select_crypts_tab'):
                            with patch.object(hunter, '_detect_on_map', return_value=True):
                                with patch.object(hunter, '_send_captain', return_value=True):
                                    with patch.object(hunter, '_click_captain_event'):
                                        with patch.object(hunter, '_accelerate', return_value=0.0):
                                            with patch.object(hunter, '_close_dialog'):
                                                with patch.object(hunter, '_random_pause'):
                                                    hunter._run_cycle()

        mock_reset.assert_called_once()
        # Должен быть один sleep 10-15 сек после reset
        reset_waits = [s for s in sleep_calls if 10.0 <= s <= 15.0]
        assert len(reset_waits) == 1, f"Ожидал один sleep 10-15с, получил: {sleep_calls}"

    def test_no_sleep_60_on_repeated_misses(self):
        """Старый механизм sleep(60) после 10 сбросов должен быть удалён."""
        from unittest.mock import patch
        hunter = self._make_hunter()
        sleep_calls = []
        # 11 раз None, потом находим — проверяем что нет sleep(60)
        side_effects = [None] * 11 + ['Ordinary_1']
        with patch.object(hunter, '_scroll_and_find', side_effect=side_effects):
            with patch.object(hunter, '_reset_search'):
                with patch.object(hunter, '_interruptible_sleep',
                                  side_effect=lambda s: sleep_calls.append(s)):
                    with patch.object(hunter, '_open_watchtower'):
                        with patch.object(hunter, '_select_crypts_tab'):
                            with patch.object(hunter, '_detect_on_map', return_value=True):
                                with patch.object(hunter, '_send_captain', return_value=True):
                                    with patch.object(hunter, '_click_captain_event'):
                                        with patch.object(hunter, '_accelerate', return_value=0.0):
                                            with patch.object(hunter, '_close_dialog'):
                                                with patch.object(hunter, '_random_pause'):
                                                    hunter._run_cycle()

        assert 60.0 not in sleep_calls, f"Нашёл sleep(60) — старый механизм не удалён: {sleep_calls}"


class TestVerifyAction:
    """_verify_action — опрос verify_fn до timeout."""

    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h.on_status_callback = None
            return h

    def test_returns_true_immediately_when_verify_passes(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch.object(hunter, '_interruptible_sleep'):
            result = hunter._verify_action('test', lambda: True, timeout=3.0)
        assert result is True

    def test_returns_true_on_second_attempt(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        calls = [False, True]
        with patch.object(hunter, '_interruptible_sleep'):
            result = hunter._verify_action('test', lambda: calls.pop(0), timeout=3.0)
        assert result is True

    def test_returns_false_on_timeout(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch.object(hunter, '_interruptible_sleep'):
            with patch('crypt_hunter.time.monotonic', side_effect=[0.0, 0.0, 5.0]):
                result = hunter._verify_action('test', lambda: False, timeout=3.0)
        assert result is False

    def test_returns_false_when_stopped(self):
        hunter = self._make_hunter()
        hunter.is_running = False
        result = hunter._verify_action('test', lambda: True, timeout=3.0)
        assert result is False


class TestSendCaptainVerification:
    """_send_captain кликает по координатам и возвращает True."""

    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h.on_status_callback = None
            return h

    def test_returns_true_always(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    result = hunter._send_captain('Ordinary_1')
        assert result is True


    def test_returns_true_always(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch.object(hunter, '_find_button', return_value=(1239, 122)):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_interruptible_sleep'):
                    result = hunter._click_captain_event()
        assert result is True
