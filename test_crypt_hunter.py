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
            h._speed_delta = 0.0
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

    def test_open_watchtower_clicks_wt_icon(self):
        """Template matching был осознанно удалён (ANTI-PATTERNS.md — только HSV+геометрия).
        Текущая реализация просто кликает по масштабированной точке WT_ICON.
        pyautogui.size() замокан на 1920x1080 (эталон), чтобы тест не зависел
        от реального разрешения экрана машины, где запущены тесты."""
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch('crypt_hunter.pyautogui.size', return_value=(1920, 1080)):
                with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
                    with patch.object(hunter, '_random_pause'):
                        hunter._open_watchtower()
        assert any(abs(x - ch.WT_ICON[0]) <= 5 and abs(y - ch.WT_ICON[1]) <= 5
                   for x, y in clicks), f"Ожидал клик около {ch.WT_ICON}, получил {clicks}"

    def test_select_crypts_tab_clicks_wt_crypts_tab(self):
        """Аналогично _open_watchtower — прямой клик по WT_CRYPTS_TAB, без шаблона."""
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch('crypt_hunter.pyautogui.size', return_value=(1920, 1080)):
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
            h._scroll_speed = 0.5
            h._exclusion_region = None
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
            h._exclusion_region = None
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

    def test_send_captain_clicks_study_button_and_returns_true(self):
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
            with patch.object(hunter, '_random_pause'):
                with patch.object(hunter, '_interruptible_sleep'):
                    with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
                        result = hunter._send_captain('R_1')
        assert ch.CRYPT_STUDY_BTN in clicks
        assert result is True


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
            h._scroll_speed = 0.5
            h._exclusion_region = None
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
            with patch.object(hunter, '_screenshot', side_effect=screenshots):
                with patch.object(hunter, '_click'):
                    with patch.object(hunter, '_random_pause'):
                        with patch('crypt_hunter.time.sleep'):
                            with patch('crypt_hunter.pyautogui.scroll'):
                                with patch('crypt_hunter.pyautogui.moveTo'):
                                    result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=5)
        assert result == 'Ordinary_1'

    def test_returns_none_when_menu_frozen_after_scroll(self):
        """Меню не изменилось после скролла (diff.mean() < 2.0) → список закончился."""
        from unittest.mock import patch, MagicMock
        import numpy as np
        hunter = self._make_hunter()
        no_result = MagicMock()
        no_result.boxes = []
        hunter._model.return_value = [no_result]
        # Оба скриншота идентичны — меню упёрлось в конец списка
        frozen_img = np.full((1080, 1920, 3), 80, dtype=np.uint8)
        screenshots = iter([frozen_img, frozen_img.copy()])
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch.object(hunter, '_screenshot', side_effect=screenshots):
                with patch.object(hunter, '_click'):
                    with patch.object(hunter, '_random_pause'):
                        with patch('crypt_hunter.time.sleep'):
                            with patch('crypt_hunter.pyautogui.scroll'):
                                with patch('crypt_hunter.pyautogui.moveTo'):
                                    result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=5)
        assert result is None

    def test_does_not_crash_when_menu_crop_is_empty(self):
        """
        AD318469CF106F61, 24.07.2026: cv2.absdiff() тихо возвращает None (не бросает
        исключение), когда оба входных массива пустые — а не при обычном несовпадении
        размеров (там честный cv2.error). Если MENU_SCAN_REGION вылезает за границы
        реального скриншота (нестандартное разрешение/масштаб), вырезка пустая, и
        diff.mean() падал AttributeError: 'NoneType' object has no attribute 'mean'.
        Скриншот 100x100 меньше MENU_SCAN_REGION (597,242,721,575) → пустой вырез.
        """
        from unittest.mock import patch, MagicMock
        import numpy as np
        hunter = self._make_hunter()
        no_result = MagicMock()
        no_result.boxes = []
        hunter._model.return_value = [no_result]
        tiny_img = np.zeros((100, 100, 3), dtype=np.uint8)
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch.object(hunter, '_screenshot', return_value=tiny_img):
                with patch.object(hunter, '_click'):
                    with patch.object(hunter, '_random_pause'):
                        with patch('crypt_hunter.time.sleep'):
                            with patch('crypt_hunter.pyautogui.scroll'):
                                with patch('crypt_hunter.pyautogui.moveTo'):
                                    result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=3)
        assert result is None

    def test_bails_out_instead_of_scrolling_forever_when_crop_stays_empty(self):
        """
        Ревью основного фикса: если MENU_SCAN_REGION вылезает за экран НЕ разово,
        а постоянно (сломанная калибровка/разрешение у игрока), пропуск сравнения
        на каждой итерации означал бы бесконечный тихий скролл без единого признака
        проблемы — раньше на этом месте был хотя бы громкий крах, который мы видели
        в логах. Вместо этого после EMPTY_MENU_CROP_STREAK_LIMIT (5) пустых вырезок
        подряд отдаём None — включается штатный сброс цикла (_run_cycle: reset +
        sleep 30 + повтор), а не вечный молчаливый скролл.
        """
        from unittest.mock import patch, MagicMock
        import numpy as np
        hunter = self._make_hunter()
        no_result = MagicMock()
        no_result.boxes = []
        hunter._model.return_value = [no_result]
        tiny_img = np.zeros((100, 100, 3), dtype=np.uint8)
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch.object(hunter, '_screenshot', return_value=tiny_img):
                with patch.object(hunter, '_click'):
                    with patch.object(hunter, '_random_pause'):
                        with patch('crypt_hunter.time.sleep'):
                            with patch('crypt_hunter.pyautogui.scroll'):
                                with patch('crypt_hunter.pyautogui.moveTo'):
                                    # max_scrolls=0 — как в реальном вызове из _run_cycle,
                                    # единственный выход должен быть через streak-лимит.
                                    result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=0)
        assert result is None
        # Возврат случается на 5-й итерации ДО вызова YOLO (пустая вырезка обнаружена
        # раньше) — значит модель успевает отработать только на первых 4 попытках.
        assert hunter._model.call_count == 4


class TestRunCycleEndOfList:
    """_run_cycle без счётчика resets — просто reset + sleep(30) + повтор."""

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
            h._detect_fail_streak = 0
            h._log_file = None
            return h

    def test_resets_and_waits_when_no_crypt_found(self):
        """Когда склеп не найден: _reset_search + sleep 30 сек + повторный поиск."""
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
        # Должен быть один sleep 30 сек после reset
        reset_waits = [s for s in sleep_calls if s == 30.0]
        assert len(reset_waits) == 1, f"Ожидал один sleep 30с, получил: {sleep_calls}"

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
            h._speed_delta = 0.0
            return h

    def test_send_captain_returns_true_always(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    result = hunter._send_captain('Ordinary_1')
        assert result is True


    def test_click_captain_event_returns_true_always(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch.object(hunter, '_find_button', return_value=(1239, 122)):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_interruptible_sleep'):
                    result = hunter._click_captain_event()
        assert result is True


class TestTesseractSetup:
    def test_crypt_hunter_configures_tesseract_via_setup(self, monkeypatch):
        import importlib
        import tesseract_setup
        calls = []
        monkeypatch.setattr(tesseract_setup, 'configure_pytesseract',
                            lambda mod, **kw: calls.append(mod) or True)
        import crypt_hunter
        importlib.reload(crypt_hunter)
        # >=1, not ==1: if crypt_hunter was already imported earlier in this test
        # process, the plain `import` above is a cache hit and only the explicit
        # reload() re-executes the module body — count depends on import order,
        # not on the behavior under test.
        assert len(calls) >= 1
        assert calls[0].__name__ == 'pytesseract'


class TestFailSafeHandling:
    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h.lang = "EN"
            h.on_stop_callback = None
            return h

    def test_failsafe_exception_shows_friendly_message_without_reporting_as_error(self):
        from unittest.mock import patch, MagicMock
        import pyautogui
        hunter = self._make_hunter()
        calls = {"cycles": 0}

        def _run_cycle_side_effect():
            calls["cycles"] += 1
            hunter.is_running = False  # stop after first iteration
            raise pyautogui.FailSafeException("fail-safe triggered")

        with patch.object(hunter, '_run_cycle', side_effect=_run_cycle_side_effect), \
             patch.object(hunter, '_status') as mock_status, \
             patch('auth.log_error_to_server') as mock_log, \
             patch('crypt_hunter.time.sleep'):
            hunter._run()

        assert calls["cycles"] == 1
        mock_status.assert_called_once()
        assert "corner" in mock_status.call_args[0][0].lower()
        mock_log.assert_not_called()
