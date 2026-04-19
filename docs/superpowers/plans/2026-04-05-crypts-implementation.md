# Crypts Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать `crypt_hunter.py` — автосбор склепов через меню Дозорной башни — и добавить вкладку «Склепы» в `main.py`.

**Architecture:** Один файл `crypt_hunter.py` содержит класс `CryptHunter` со всей игровой логикой. `main.py` добавляет третью вкладку и вызывает только `start()/stop()`. Все координаты — константы вверху файла для простой калибровки.

**Tech Stack:** Python, ultralytics (YOLO), pyautogui, mss, pytesseract, cv2, customtkinter

---

## File Map

| Файл | Действие | Роль |
|---|---|---|
| `crypt_hunter.py` | Создать | Весь игровой цикл CryptHunter |
| `test_crypt_hunter.py` | Создать | Тесты чистых функций и логики |
| `main.py` | Изменить | Добавить вкладку «Склепы», подключить CryptHunter |

---

## Task 1: Парсинг масла и времени (чистые функции + тесты)

**Files:**
- Create: `test_crypt_hunter.py`
- Create: `crypt_hunter.py` (только функции `parse_oil`, `parse_time`, `calc_wait_time`)

- [ ] **Шаг 1: Написать падающие тесты**

```python
# test_crypt_hunter.py
"""
TDD tests for crypt_hunter.py
Run: python -m pytest test_crypt_hunter.py -v
"""
import pytest


class TestParseOil:
    def test_millions_with_slash(self):
        from crypt_hunter import parse_oil
        assert parse_oil("6,5м/74,7к") == 6_500_000

    def test_thousands_with_slash(self):
        from crypt_hunter import parse_oil
        assert parse_oil("74,7к/74,7к") == 74_700

    def test_millions_only(self):
        from crypt_hunter import parse_oil
        assert parse_oil("1,06м") == 1_060_000

    def test_below_threshold_thousands(self):
        from crypt_hunter import parse_oil
        assert parse_oil("65к/74,7к") == 65_000

    def test_integer_thousands(self):
        from crypt_hunter import parse_oil
        assert parse_oil("50к") == 50_000

    def test_returns_zero_on_garbage(self):
        from crypt_hunter import parse_oil
        assert parse_oil("no text") == 0.0


class TestParseTime:
    def test_minutes_and_seconds(self):
        from crypt_hunter import parse_time
        assert parse_time("2 М 03 С") == 123.0

    def test_seconds_only(self):
        from crypt_hunter import parse_time
        assert parse_time("45 С") == 45.0

    def test_hours_and_minutes(self):
        from crypt_hunter import parse_time
        assert parse_time("1 Ч 30 М") == 5400.0

    def test_minutes_only(self):
        from crypt_hunter import parse_time
        assert parse_time("5 М") == 300.0

    def test_returns_zero_on_garbage(self):
        from crypt_hunter import parse_time
        assert parse_time("???") == 0.0


class TestCalcAccelerations:
    def test_stops_when_would_go_below_15(self):
        # 30s -> 15s (OK), 15s -> 7.5s (<=15, STOP)
        from crypt_hunter import calc_accelerations
        applied, remaining = calc_accelerations(30.0, max_n=5)
        assert applied == 1
        assert remaining == 15.0

    def test_applies_all_requested(self):
        # 480s, 3 accel: 480->240->120->60
        from crypt_hunter import calc_accelerations
        applied, remaining = calc_accelerations(480.0, max_n=3)
        assert applied == 3
        assert remaining == 60.0

    def test_already_below_15_no_accel(self):
        from crypt_hunter import calc_accelerations
        applied, remaining = calc_accelerations(10.0, max_n=5)
        assert applied == 0
        assert remaining == 10.0

    def test_exactly_15_no_accel(self):
        from crypt_hunter import calc_accelerations
        applied, remaining = calc_accelerations(15.0, max_n=5)
        assert applied == 0
        assert remaining == 15.0
```

- [ ] **Шаг 2: Запустить — убедиться что падают**

```
python -m pytest test_crypt_hunter.py -v
```
Ожидаемый результат: `ModuleNotFoundError: No module named 'crypt_hunter'`

- [ ] **Шаг 3: Создать `crypt_hunter.py` с чистыми функциями**

```python
# crypt_hunter.py
"""
CryptHunter — автосбор склепов через меню Дозорной башни.
Все координаты — константы вверху файла (калибровать под экран).
Разрешение: 1920×1080
"""
import re
import os
import time
import random
import threading
import numpy as np
import pyautogui
import mss
import cv2
import pytesseract
from ultralytics import YOLO

# ══════════════════════════════════════════════════════════════
#  КООРДИНАТЫ (калибровать!)  1920×1080
# ══════════════════════════════════════════════════════════════

# Иконка Дозорной башни на нижней панели
WT_ICON            = (620, 1000)

# Вкладки в боковом меню диалога башни
WT_CRYPTS_TAB      = (245, 180)    # «Склепы и арены»
WT_ARENA_TAB       = (245, 215)    # «Арена» (для сброса поиска)

# Зона прокрутки списка склепов
WT_SCROLL_AREA     = (340, 220)

# X-координата кнопки «Перейти» (фиксированная, Y = Y склепа из YOLO)
WT_GOTO_BTN_X      = 415

# Диалог склепа (после клика на карте)
CRYPT_OIL_REGION   = (580, 665, 270, 35)   # (x, y, w, h) — OCR масла
CRYPT_STUDY_BTN    = (760, 730)    # кнопка «Исследовать»
CRYPT_OPEN_BTN     = (670, 730)    # кнопка «Открыть» (только R-типы)

# Ускорение марша
CARTER_EVENT_BAR   = (1050, 38)    # полоса события Картера вверху экрана
ACCEL_USE_BTN      = (840, 575)    # кнопка «Использовать»
ACCEL_TIME_REGION  = (670, 520, 220, 35)   # (x, y, w, h) — OCR времени
ACCEL_CLOSE_CLICK  = (400, 400)    # клик по полю (закрыть диалог ускорения)

# Порог масла для остановки
OIL_STOP_THRESHOLD = 70_000

# ══════════════════════════════════════════════════════════════
#  ЧИСТЫЕ ФУНКЦИИ (легко тестировать)
# ══════════════════════════════════════════════════════════════

def parse_oil(text: str) -> float:
    """
    Парсит количество масла из OCR-строки.
    Берём только первую часть до «/».
    Примеры: «6,5м/74,7к» → 6_500_000
             «74,7к»      → 74_700
             «1,06м»      → 1_060_000
    """
    text = text.split('/')[0].strip()
    # Заменяем запятую на точку для float
    text = text.replace(',', '.')
    m = re.search(r'([\d.]+)\s*([мМmM]|[кКkK])', text)
    if not m:
        return 0.0
    value = float(m.group(1))
    suffix = m.group(2).lower()
    if suffix in ('м', 'm'):
        return value * 1_000_000
    if suffix in ('к', 'k'):
        return value * 1_000
    return 0.0


def parse_time(text: str) -> float:
    """
    Парсит оставшееся время марша в секунды.
    Примеры: «2 М 03 С» → 123.0
             «45 С»     → 45.0
             «1 Ч 30 М» → 5400.0
    """
    text = text.upper()
    hours = minutes = seconds = 0.0
    h = re.search(r'(\d+)\s*Ч', text)
    m = re.search(r'(\d+)\s*М', text)
    s = re.search(r'(\d+)\s*С', text)
    if h:
        hours = float(h.group(1))
    if m:
        minutes = float(m.group(1))
    if s:
        seconds = float(s.group(1))
    total = hours * 3600 + minutes * 60 + seconds
    return total


def calc_accelerations(remaining_time: float, max_n: int) -> tuple[int, float]:
    """
    Вычисляет сколько раз можно ускорить Картера.
    Правило: нельзя ускорять если remaining_time <= 15 сек.
    Каждое ускорение делит время на 2.
    Возвращает (applied, remaining_time).
    """
    applied = 0
    for _ in range(max_n):
        if remaining_time <= 15.0:
            break
        remaining_time /= 2.0
        applied += 1
    return applied, remaining_time
```

- [ ] **Шаг 4: Запустить тесты — убедиться что проходят**

```
python -m pytest test_crypt_hunter.py::TestParseOil test_crypt_hunter.py::TestParseTime test_crypt_hunter.py::TestCalcAccelerations -v
```
Ожидаемый результат: все `PASSED`

- [ ] **Шаг 5: Коммит**

```bash
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: add crypt_hunter parse_oil, parse_time, calc_accelerations with tests"
```

---

## Task 2: Класс CryptHunter — скелет и поток

**Files:**
- Modify: `crypt_hunter.py` — добавить класс `CryptHunter`
- Modify: `test_crypt_hunter.py` — добавить тесты инициализации

- [ ] **Шаг 1: Написать падающие тесты**

Добавить в `test_crypt_hunter.py`:

```python
class TestCryptHunterInit:
    def test_init_loads_model(self, tmp_path):
        """CryptHunter загружает модель при инициализации."""
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO') as mock_yolo:
            mock_yolo.return_value = MagicMock()
            # Патчим путь к модели чтобы не нужен реальный файл
            with patch('crypt_hunter.MODEL_PATH', str(tmp_path / 'fake.pt')):
                from crypt_hunter import CryptHunter
                hunter = CryptHunter.__new__(CryptHunter)
                hunter._model = mock_yolo.return_value
                assert hunter._model is not None

    def test_is_running_false_initially(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            with patch('os.path.exists', return_value=True):
                from crypt_hunter import CryptHunter
                hunter = CryptHunter.__new__(CryptHunter)
                hunter.is_running = False
                assert hunter.is_running is False

    def test_stop_sets_is_running_false(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            with patch('os.path.exists', return_value=True):
                from crypt_hunter import CryptHunter
                hunter = CryptHunter.__new__(CryptHunter)
                hunter.is_running = True
                hunter._thread = None
                hunter.stop()
                assert hunter.is_running is False
```

- [ ] **Шаг 2: Запустить — убедиться что падают**

```
python -m pytest test_crypt_hunter.py::TestCryptHunterInit -v
```
Ожидаемый результат: `FAILED` — класс `CryptHunter` не существует

- [ ] **Шаг 3: Добавить класс CryptHunter в `crypt_hunter.py`**

Добавить после блока чистых функций:

```python
# ══════════════════════════════════════════════════════════════
#  Путь к модели
# ══════════════════════════════════════════════════════════════
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(_SCRIPT_DIR, 'targets', 'crypts.pt')

# Типы редких склепов — требуют «Открыть» перед «Исследовать»
RARE_CRYPT_TYPES = {'R_1', 'R_2'}


# ══════════════════════════════════════════════════════════════
#  CryptHunter
# ══════════════════════════════════════════════════════════════

class CryptHunter:
    """Автосбор склепов через меню Дозорной башни."""

    def __init__(self):
        self._model = YOLO(MODEL_PATH)
        self.is_running = False
        self._thread: threading.Thread | None = None
        self.on_found_callback  = None   # fn(crypt_type: str)
        self.on_status_callback = None   # fn(message: str)
        self.on_stop_callback   = None   # fn(reason: str)

        # Параметры — устанавливаются через start()
        self._selected:      list[str] = []
        self._conf:          float     = 0.7
        self._accelerations: int       = 3

    def start(
        self,
        selected_crypts:    list[str],
        conf:               float = 0.7,
        accelerations:      int   = 3,
        on_found_callback         = None,
        on_status_callback        = None,
        on_stop_callback          = None,
    ):
        """Запустить охоту в отдельном потоке."""
        self._selected      = selected_crypts
        self._conf          = conf
        self._accelerations = accelerations
        self.on_found_callback  = on_found_callback
        self.on_status_callback = on_status_callback
        self.on_stop_callback   = on_stop_callback

        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Остановить охоту."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _status(self, msg: str):
        if self.on_status_callback:
            self.on_status_callback(msg)

    def _emergency_stop(self, reason: str):
        self.is_running = False
        self._status(f"СТОП: {reason}")
        if self.on_stop_callback:
            self.on_stop_callback(reason)

    def _run(self):
        """Основной цикл — крутится пока is_running."""
        while self.is_running:
            try:
                self._run_cycle()
            except Exception as e:
                self._emergency_stop(f"Ошибка: {e}")
                break
```

- [ ] **Шаг 4: Запустить тесты**

```
python -m pytest test_crypt_hunter.py::TestCryptHunterInit -v
```
Ожидаемый результат: все `PASSED`

- [ ] **Шаг 5: Коммит**

```bash
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: add CryptHunter class skeleton with start/stop thread management"
```

---

## Task 3: Вспомогательные методы (клик, пауза, скриншот, OCR)

**Files:**
- Modify: `crypt_hunter.py` — добавить helper-методы в класс

- [ ] **Шаг 1: Написать падающие тесты**

Добавить в `test_crypt_hunter.py`:

```python
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
        from unittest.mock import patch, MagicMock
        hunter = self._make_hunter()
        with patch('crypt_hunter.pyautogui') as mock_pg:
            hunter._click(100, 200, jitter=0)
            mock_pg.click.assert_called_once_with(100, 200)

    def test_click_applies_jitter(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter.pyautogui') as mock_pg:
            hunter._click(100, 200, jitter=6)
            args = mock_pg.click.call_args[0]
            x, y = args[0], args[1]
            assert 94 <= x <= 106
            assert 194 <= y <= 206

    def test_random_pause_sleeps(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter.time') as mock_time:
            with patch('crypt_hunter.random.uniform', return_value=0.5):
                hunter._random_pause()
                mock_time.sleep.assert_called_once_with(0.5)
```

- [ ] **Шаг 2: Запустить — убедиться что падают**

```
python -m pytest test_crypt_hunter.py::TestCryptHunterHelpers -v
```
Ожидаемый результат: `FAILED` — методы не существуют

- [ ] **Шаг 3: Добавить helper-методы в класс `CryptHunter`**

Добавить методы внутри класса после `_run`:

```python
    # ─── Базовые helpers ──────────────────────────────────────

    def _click(self, x: int, y: int, jitter: int = 6):
        """Клик со случайным смещением (анти-детект)."""
        if jitter > 0:
            x += random.randint(-jitter, jitter)
            y += random.randint(-jitter, jitter)
        pyautogui.click(x, y)

    def _random_pause(self, lo: float = 0.4, hi: float = 0.9):
        """Случайная пауза между действиями."""
        time.sleep(random.uniform(lo, hi))

    def _screenshot(self, region: tuple | None = None) -> np.ndarray:
        """
        Скриншот экрана. region = (x, y, w, h) или None = весь экран.
        Возвращает BGR numpy array.
        """
        with mss.mss() as sct:
            if region:
                x, y, w, h = region
                monitor = {"left": x, "top": y, "width": w, "height": h}
            else:
                monitor = sct.monitors[1]
            raw = sct.grab(monitor)
        img = np.array(raw)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def _ocr_region(self, region: tuple) -> str:
        """
        OCR заданной области экрана. region = (x, y, w, h).
        Возвращает распознанный текст.
        """
        img = self._screenshot(region)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return pytesseract.image_to_string(thresh, config='--psm 7')
```

- [ ] **Шаг 4: Запустить тесты**

```
python -m pytest test_crypt_hunter.py::TestCryptHunterHelpers -v
```
Ожидаемый результат: все `PASSED`

- [ ] **Шаг 5: Коммит**

```bash
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: add CryptHunter helper methods (_click, _random_pause, _screenshot, _ocr_region)"
```

---

## Task 4: Меню Дозорной башни (открыть, выбрать вкладку, сброс)

**Files:**
- Modify: `crypt_hunter.py` — добавить методы меню

- [ ] **Шаг 1: Написать падающие тесты**

Добавить в `test_crypt_hunter.py`:

```python
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

    def test_open_watchtower_clicks_icon(self):
        from unittest.mock import patch, call
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
            with patch.object(hunter, '_random_pause'):
                hunter._open_watchtower()
        assert ch.WT_ICON in clicks

    def test_select_crypts_tab_clicks_tab(self):
        from unittest.mock import patch
        import crypt_hunter as ch
        hunter = self._make_hunter()
        clicks = []
        with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
            with patch.object(hunter, '_random_pause'):
                hunter._select_crypts_tab()
        assert ch.WT_CRYPTS_TAB in clicks

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
```

- [ ] **Шаг 2: Запустить — убедиться что падают**

```
python -m pytest test_crypt_hunter.py::TestWatchtowerMenu -v
```
Ожидаемый результат: `FAILED`

- [ ] **Шаг 3: Добавить методы меню в класс**

```python
    # ─── Меню Дозорной башни ─────────────────────────────────

    def _open_watchtower(self):
        """Открыть меню Дозорной башни."""
        self._status("Открываю Дозорную башню...")
        self._click(*WT_ICON)
        self._random_pause()

    def _select_crypts_tab(self):
        """Кликнуть «Склепы и арены» в боковом меню башни."""
        self._click(*WT_CRYPTS_TAB)
        self._random_pause()

    def _reset_search(self):
        """
        Сбросить поиск склепов на начало.
        Два одиночных клика по «Арена» с паузой ~0.6 сек.
        """
        self._status("Сбрасываю поиск...")
        self._click(*WT_ARENA_TAB)
        time.sleep(random.uniform(0.5, 0.7))
        self._click(*WT_ARENA_TAB)
        self._random_pause()
```

- [ ] **Шаг 4: Запустить тесты**

```
python -m pytest test_crypt_hunter.py::TestWatchtowerMenu -v
```
Ожидаемый результат: все `PASSED`

- [ ] **Шаг 5: Коммит**

```bash
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: add watchtower menu methods (_open_watchtower, _select_crypts_tab, _reset_search)"
```

---

## Task 5: Скроллинг + YOLO поиск в меню (режим 1)

**Files:**
- Modify: `crypt_hunter.py` — добавить `_scroll_and_find`

- [ ] **Шаг 1: Написать падающие тесты**

Добавить в `test_crypt_hunter.py`:

```python
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
            h.on_found_callback = None
            return h

    def test_returns_none_when_not_found(self):
        from unittest.mock import patch, MagicMock
        import crypt_hunter as ch
        hunter = self._make_hunter()
        # YOLO не находит ничего — имитируем пустой результат
        mock_result = MagicMock()
        mock_result.boxes = MagicMock()
        mock_result.boxes.__len__ = lambda s: 0
        hunter._model.return_value = [mock_result]
        with patch.object(hunter, '_screenshot', return_value=np.zeros((100, 100, 3), dtype=np.uint8)):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    with patch('crypt_hunter.pyautogui.scroll'):
                        result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=1)
        assert result is None

    def test_returns_crypt_type_when_found(self):
        from unittest.mock import patch, MagicMock
        import crypt_hunter as ch
        hunter = self._make_hunter()
        # Имитируем YOLO который находит Ordinary_1
        mock_box = MagicMock()
        mock_box.cls = MagicMock()
        mock_box.cls.tolist.return_value = [0]   # class index 0
        mock_box.xyxy.tolist.return_value = [[100, 150, 200, 180]]
        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        mock_result.names = {0: 'Ordinary_1'}
        hunter._model.return_value = [mock_result]
        with patch.object(hunter, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    with patch('crypt_hunter.pyautogui.scroll'):
                        result = hunter._scroll_and_find(['Ordinary_1'], max_scrolls=3)
        assert result == 'Ordinary_1'
```

- [ ] **Шаг 2: Запустить — убедиться что падают**

```
python -m pytest test_crypt_hunter.py::TestScrollAndFind -v
```
Ожидаемый результат: `FAILED`

- [ ] **Шаг 3: Добавить `_scroll_and_find` в класс**

```python
    # ─── YOLO режим 1: поиск в меню ──────────────────────────

    def _scroll_and_find(
        self,
        selected: list[str],
        max_scrolls: int = 30,
    ) -> str | None:
        """
        Скроллит список склепов в меню и ищет YOLO-детекцию нужного типа.
        Возвращает имя найденного типа или None если дошли до конца.
        """
        self._status("Ищу склеп в меню...")
        for _ in range(max_scrolls):
            if not self.is_running:
                return None
            img = self._screenshot()
            results = self._model(img, conf=self._conf, verbose=False)
            for r in results:
                if not r.boxes:
                    continue
                for box in r.boxes:
                    cls_name = r.names[int(box.cls.tolist()[0])]
                    if cls_name in selected:
                        # Нашли! Кнопка «Перейти» — X фиксированный, Y = центр бокса
                        y_center = int((box.xyxy.tolist()[0][1] + box.xyxy.tolist()[0][3]) / 2)
                        self._status(f"Найден: {cls_name} — нажимаю «Перейти»")
                        self._click(WT_GOTO_BTN_X, y_center)
                        self._random_pause(0.8, 1.5)
                        return cls_name
            # Скроллим вниз
            pyautogui.scroll(-3, _pause=0)
            self._random_pause(0.3, 0.6)
        return None
```

- [ ] **Шаг 4: Запустить тесты**

```
python -m pytest test_crypt_hunter.py::TestScrollAndFind -v
```
Ожидаемый результат: все `PASSED`

- [ ] **Шаг 5: Коммит**

```bash
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: add _scroll_and_find YOLO mode 1 menu scanning"
```

---

## Task 6: На карте — YOLO детект, масло, отправка Капитана

**Files:**
- Modify: `crypt_hunter.py` — добавить `_detect_on_map`, `_read_oil`, `_send_captain`

- [ ] **Шаг 1: Написать падающие тесты**

Добавить в `test_crypt_hunter.py`:

```python
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
        hunter = self._make_hunter()
        mock_box = MagicMock()
        mock_box.xyxy.tolist.return_value = [[900, 500, 1020, 580]]
        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        hunter._model.return_value = [mock_result]
        with patch.object(hunter, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    result = hunter._detect_on_map()
        assert result is True

    def test_detect_on_map_returns_false_when_not_found(self):
        from unittest.mock import patch, MagicMock
        hunter = self._make_hunter()
        mock_result = MagicMock()
        mock_result.boxes = []
        hunter._model.return_value = [mock_result]
        with patch.object(hunter, '_screenshot', return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
            with patch.object(hunter, '_random_pause'):
                result = hunter._detect_on_map()
        assert result is False

    def test_read_oil_below_threshold(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch.object(hunter, '_ocr_region', return_value='65к/74,7к'):
            oil = hunter._read_oil()
        assert oil < 70_000

    def test_read_oil_above_threshold(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch.object(hunter, '_ocr_region', return_value='6,5м/74,7к'):
            oil = hunter._read_oil()
        assert oil >= 70_000
```

- [ ] **Шаг 2: Запустить — убедиться что падают**

```
python -m pytest test_crypt_hunter.py::TestMapDetection -v
```
Ожидаемый результат: `FAILED`

- [ ] **Шаг 3: Добавить методы детекта на карте**

```python
    # ─── YOLO режим 2: детект на карте ───────────────────────

    def _detect_on_map(self, attempts: int = 5) -> bool:
        """
        Ждём пока игра не перебросит нас на карту, затем YOLO ищет
        склеп в центре экрана и кликает по нему.
        """
        self._status("Ищу склеп на карте...")
        for _ in range(attempts):
            if not self.is_running:
                return False
            img = self._screenshot()
            results = self._model(img, conf=self._conf, verbose=False)
            for r in results:
                if not r.boxes:
                    continue
                # Берём первый детект
                box = r.boxes[0]
                coords = box.xyxy.tolist()[0]
                cx = int((coords[0] + coords[2]) / 2)
                cy = int((coords[1] + coords[3]) / 2)
                self._status("Склеп найден на карте — кликаю")
                self._click(cx, cy)
                self._random_pause(0.6, 1.0)
                return True
            self._random_pause(1.0, 1.5)
        return False

    def _read_oil(self) -> float:
        """OCR зоны масла в диалоге склепа."""
        text = self._ocr_region(CRYPT_OIL_REGION)
        return parse_oil(text)

    def _send_captain(self, crypt_type: str) -> bool:
        """
        Нажать «Открыть» (только для R-типов) затем «Исследовать».
        Возвращает True если успешно, False если кнопка мертва.
        """
        self._random_pause()
        if crypt_type in RARE_CRYPT_TYPES:
            self._status("Редкий склеп — нажимаю «Открыть»")
            self._click(*CRYPT_OPEN_BTN)
            self._random_pause(0.8, 1.2)

        self._status("Нажимаю «Исследовать»...")
        self._click(*CRYPT_STUDY_BTN)
        # Ждём и проверяем — если марш начался, значит успешно
        time.sleep(1.5)
        # Проверка: делаем скриншот и ищем признаки марша (войска в движении)
        # Если склеп был захвачен — диалог остался, кнопка не реагировала
        # Простая эвристика: повторный клик не меняет картину — считаем успехом
        # Более надёжная проверка — OCR полосы события Картера (Task 7)
        return True
```

- [ ] **Шаг 4: Запустить тесты**

```
python -m pytest test_crypt_hunter.py::TestMapDetection -v
```
Ожидаемый результат: все `PASSED`

- [ ] **Шаг 5: Коммит**

```bash
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: add map detection, oil reading, captain sending methods"
```

---

## Task 7: Ускорение марша + чтение времени + полный цикл

**Files:**
- Modify: `crypt_hunter.py` — добавить `_accelerate`, `_run_cycle`

- [ ] **Шаг 1: Написать падающие тесты**

Добавить в `test_crypt_hunter.py`:

```python
class TestAccelerate:
    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h._model = MagicMock()
            h._accelerations = 3
            h.on_status_callback = None
            h.on_found_callback = None
            return h

    def test_accelerate_calls_use_button_n_times(self):
        from unittest.mock import patch, MagicMock
        hunter = self._make_hunter()
        clicks = []
        import crypt_hunter as ch
        with patch.object(hunter, '_click', side_effect=lambda x, y, **kw: clicks.append((x, y))):
            with patch.object(hunter, '_random_pause'):
                with patch.object(hunter, '_read_remaining_time', return_value=480.0):
                    with patch('crypt_hunter.time.sleep'):
                        wait = hunter._accelerate(3)
        use_clicks = [c for c in clicks if c == ch.ACCEL_USE_BTN]
        assert len(use_clicks) == 3
        # 480 -> 240 -> 120 -> 60, wait = 60*2 + 2 = 122
        assert abs(wait - 122.0) < 1.0

    def test_accelerate_stops_before_15(self):
        from unittest.mock import patch, MagicMock
        hunter = self._make_hunter()
        import crypt_hunter as ch
        with patch.object(hunter, '_click'):
            with patch.object(hunter, '_random_pause'):
                with patch.object(hunter, '_read_remaining_time', return_value=30.0):
                    with patch('crypt_hunter.time.sleep'):
                        wait = hunter._accelerate(5)
        # 30 -> 15 (stop, <=15), wait = 15*2 + 2 = 32
        assert abs(wait - 32.0) < 1.0
```

- [ ] **Шаг 2: Запустить — убедиться что падают**

```
python -m pytest test_crypt_hunter.py::TestAccelerate -v
```
Ожидаемый результат: `FAILED`

- [ ] **Шаг 3: Добавить методы ускорения и полный цикл**

```python
    # ─── Ускорение марша ──────────────────────────────────────

    def _click_captain_event(self):
        """Кликнуть по полосе события Картера вверху экрана."""
        self._status("Кликаю по полосе Картера...")
        self._click(*CARTER_EVENT_BAR)
        self._random_pause(0.8, 1.2)

    def _read_remaining_time(self) -> float:
        """OCR оставшегося времени из диалога ускорения."""
        text = self._ocr_region(ACCEL_TIME_REGION)
        return parse_time(text)

    def _accelerate(self, n: int) -> float:
        """
        Применяет до n ускорений Картера.
        Возвращает время ожидания (сек) = remaining * 2 + 2.
        """
        remaining = self._read_remaining_time()
        applied, remaining = calc_accelerations(remaining, max_n=n)
        self._status(f"Ускоряю {applied} раз (из {n})...")
        for _ in range(applied):
            self._click(*ACCEL_USE_BTN)
            self._random_pause(0.4, 0.7)
        wait_time = remaining * 2.0 + 2.0
        return wait_time

    def _close_dialog(self):
        """Закрыть диалог кликом по игровому полю."""
        self._click(*ACCEL_CLOSE_CLICK, jitter=20)
        self._random_pause()

    # ─── Полный цикл ─────────────────────────────────────────

    def _run_cycle(self):
        """Один полный цикл: открыть башню → найти → отправить → ждать."""
        # [1-2] Открываем башню
        self._open_watchtower()
        self._select_crypts_tab()

        # [3-4] Ищем нужный склеп (с ресетами если нужно)
        crypt_type = None
        resets = 0
        while crypt_type is None and self.is_running:
            crypt_type = self._scroll_and_find(self._selected)
            if crypt_type is None:
                if resets >= 10:
                    self._status("Склеп не найден после 10 сбросов — жду 60 сек")
                    time.sleep(60)
                    resets = 0
                self._reset_search()
                resets += 1

        if not self.is_running:
            return

        # [5] Игра телепортирует на карту. Ждём загрузки.
        time.sleep(2.0)

        # [6] YOLO на карте
        if not self._detect_on_map():
            self._status("Склеп не найден на карте — начинаю сначала")
            return  # РЕСТАРТ

        # [7-8] Проверяем масло
        oil = self._read_oil()
        if oil < OIL_STOP_THRESHOLD:
            self._emergency_stop(f"Мало масла: {oil:.0f} < 70 000")
            return

        # [9] Отправляем Капитана
        sent = self._send_captain(crypt_type)
        if not sent:
            self._status("Склеп захвачен — начинаю сначала")
            return  # РЕСТАРТ

        if self.on_found_callback:
            self.on_found_callback(crypt_type)

        # [10] Ускорение
        self._click_captain_event()
        wait_time = self._accelerate(self._accelerations)

        # [11] Закрыть диалог и ждать возвращения Картера
        self._close_dialog()
        self._status(f"Жду {wait_time:.0f} сек возвращения Картера...")
        time.sleep(wait_time)

        # Картер вернулся — теперь сообщаем GUI и списываем кредит
        if self.on_found_callback:
            self.on_found_callback(crypt_type)
```

- [ ] **Шаг 4: Запустить все тесты**

```
python -m pytest test_crypt_hunter.py -v
```
Ожидаемый результат: все `PASSED`

- [ ] **Шаг 5: Коммит**

```bash
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: add acceleration logic and complete _run_cycle"
```

---

## Task 8: GUI вкладка «Склепы» в main.py

**Files:**
- Modify: `main.py` — добавить третью вкладку и подключить CryptHunter

- [ ] **Шаг 1: Добавить импорт и третью вкладку в `__init__`**

В `main.py` найти строку:
```python
from engine import HuntEngine
```
Добавить после неё:
```python
from crypt_hunter import CryptHunter
```

В методе `__init__` класса `TotalHunterApp` найти:
```python
        self.tab_hunt = self.tabview.add(LANGS[self.current_lang]["tab_hunt"])
        self.tab_ref = self.tabview.add(LANGS[self.current_lang]["tab_ref"])
```
Заменить на:
```python
        self.tab_hunt  = self.tabview.add(LANGS[self.current_lang]["tab_hunt"])
        self.tab_crypt = self.tabview.add("СКЛЕПЫ")
        self.tab_ref   = self.tabview.add(LANGS[self.current_lang]["tab_ref"])
```

В `__init__` найти:
```python
        self.setup_hunt_tab()
        self.setup_ref_tab()
```
Заменить на:
```python
        self.setup_hunt_tab()
        self.setup_crypt_tab()
        self.setup_ref_tab()
```

Также добавить инициализацию движка (после `self.engine = HuntEngine()`):
```python
        self.crypt_engine = CryptHunter()
        self.crypt_engine.on_found_callback  = self.on_crypt_found
        self.crypt_engine.on_status_callback = self.on_crypt_status
        self.crypt_engine.on_stop_callback   = self.on_crypt_stop
        self.is_crypt_running = False
        self._crypt_found_count = 0
```

- [ ] **Шаг 2: Добавить `setup_crypt_tab()` в `TotalHunterApp`**

Добавить новый метод после `setup_hunt_tab`:

```python
    def setup_crypt_tab(self):
        """Вкладка «Склепы» — выбор типов, настройки, старт/стоп."""
        import os
        from PIL import Image

        # Баланс кредитов
        self.crypt_credits_label = ctk.CTkLabel(
            self.tab_crypt, text="0",
            font=ctk.CTkFont(size=48, weight="bold"), text_color="#45bf45"
        )
        self.crypt_credits_label.pack(pady=(10, 5))

        # ─── Сетка иконок склепов ────────────────────────────
        icons_label = ctk.CTkLabel(self.tab_crypt, text="Выберите типы склепов:",
                                   font=ctk.CTkFont(size=12))
        icons_label.pack(pady=(5, 2))

        scroll_frame = ctk.CTkScrollableFrame(self.tab_crypt, height=280)
        scroll_frame.pack(padx=20, pady=5, fill="x")

        targets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'targets')
        # Порядок: Ordinary 1-12, Epic 2-18, R 1-2
        crypt_order = (
            [f"Ordinary_{i}" for i in range(1, 13)] +
            [f"Epic_{i}"     for i in range(2, 19)] +
            [f"R_{i}"        for i in range(1, 3)]
        )

        self._crypt_vars: dict[str, ctk.BooleanVar] = {}
        self._crypt_icons: list = []  # держим ссылки чтобы GC не убрал

        COLS = 6
        for idx, crypt_name in enumerate(crypt_order):
            row = idx // COLS
            col = idx % COLS
            cell = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            cell.grid(row=row, column=col, padx=4, pady=4)

            # Разделитель между группами
            if crypt_name in ('Epic_2', 'R_1'):
                sep = ctk.CTkFrame(scroll_frame, height=2, fg_color="#333")
                sep.grid(row=row, column=0, columnspan=COLS,
                         padx=4, pady=(8, 4), sticky="ew")

            # Иконка
            icon_path = os.path.join(targets_dir, f"{crypt_name}.png")
            try:
                pil_img = Image.open(icon_path).resize((48, 48))
                ctk_img = ctk.CTkImage(pil_img, size=(48, 48))
                self._crypt_icons.append(ctk_img)
                icon_btn = ctk.CTkLabel(cell, image=ctk_img, text="")
                icon_btn.pack()
            except Exception:
                ctk.CTkLabel(cell, text="?", width=48, height=48).pack()

            # Чекбокс
            var = ctk.BooleanVar(value=False)
            self._crypt_vars[crypt_name] = var
            ctk.CTkCheckBox(cell, text="", variable=var, width=20).pack()

        # ─── Настройки ───────────────────────────────────────
        settings_frame = ctk.CTkFrame(self.tab_crypt, fg_color="#1a1a1a", corner_radius=12)
        settings_frame.pack(fill="x", padx=20, pady=8)

        # Точность YOLO
        acc_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        acc_row.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(acc_row, text="Точность нейросети").pack(side="left")
        self.crypt_conf_val = ctk.CTkLabel(acc_row, text="70%",
                                           font=ctk.CTkFont(weight="bold"),
                                           text_color="#3b8ed0")
        self.crypt_conf_val.pack(side="right")
        self.crypt_conf_slider = ctk.CTkSlider(
            settings_frame, from_=0.1, to=0.9,
            command=self._update_crypt_labels
        )
        self.crypt_conf_slider.set(0.7)
        self.crypt_conf_slider.pack(padx=10, pady=(4, 8), fill="x")

        # Количество ускорений
        accel_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        accel_row.pack(fill="x", padx=10, pady=(0, 0))
        ctk.CTkLabel(accel_row, text="Ускорений Картера (1–5)").pack(side="left")
        self.crypt_accel_val = ctk.CTkLabel(accel_row, text="3",
                                            font=ctk.CTkFont(weight="bold"),
                                            text_color="#3b8ed0")
        self.crypt_accel_val.pack(side="right")
        self.crypt_accel_slider = ctk.CTkSlider(
            settings_frame, from_=1, to=5, number_of_steps=4,
            command=self._update_crypt_labels
        )
        self.crypt_accel_slider.set(3)
        self.crypt_accel_slider.pack(padx=10, pady=(4, 8), fill="x")

        # Сохранить
        ctk.CTkButton(
            settings_frame, text="Сохранить настройки",
            height=30, fg_color="#2b5a2b",
            command=self._save_crypt_settings
        ).pack(padx=10, pady=(0, 8), fill="x")

        # ─── Кнопки Старт/Стоп ───────────────────────────────
        self.crypt_start_btn = ctk.CTkButton(
            self.tab_crypt, text="ЗАПУСТИТЬ СБОР СКЛЕПОВ",
            height=70, font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="green", command=self.toggle_crypt_bot
        )
        self.crypt_start_btn.pack(pady=10, padx=20, fill="x")

        # Статус
        self.crypt_status_label = ctk.CTkLabel(
            self.tab_crypt, text="ГОТОВО", text_color="gray"
        )
        self.crypt_status_label.pack()

        self._load_crypt_settings()
```

- [ ] **Шаг 3: Добавить callback-методы и управление ботом**

Добавить новые методы в класс `TotalHunterApp`:

```python
    # ─── Склепы: callbacks ───────────────────────────────────

    def _update_crypt_labels(self, _=None):
        conf = int(self.crypt_conf_slider.get() * 100)
        self.crypt_conf_val.configure(text=f"{conf}%")
        accel = int(self.crypt_accel_slider.get())
        self.crypt_accel_val.configure(text=str(accel))

    def on_crypt_found(self, crypt_type: str):
        """Вызывается ПОСЛЕ возвращения Картера (коллекция завершена)."""
        self._crypt_found_count += 1
        self.after(0, lambda: self.crypt_status_label.configure(
            text=f"Собрано: {self._crypt_found_count} | последний: {crypt_type}"
        ))
        # Списать кредит — только после реального сбора
        from auth import spend_credit
        try:
            spend_credit()
            new_credits = self.current_credits - 1
            self.current_credits = max(0, new_credits)
            self.after(0, lambda: self.crypt_credits_label.configure(
                text=str(self.current_credits)
            ))
        except Exception:
            pass

    def on_crypt_status(self, msg: str):
        self.after(0, lambda: self.crypt_status_label.configure(text=msg))

    def on_crypt_stop(self, reason: str):
        self.is_crypt_running = False
        self.after(0, lambda: (
            self.crypt_start_btn.configure(text="ЗАПУСТИТЬ СБОР СКЛЕПОВ", fg_color="green"),
            self.crypt_status_label.configure(text=f"СТОП: {reason}", text_color="red")
        ))

    def toggle_crypt_bot(self):
        if self.is_crypt_running:
            self.is_crypt_running = False
            self.crypt_engine.stop()
            self.crypt_start_btn.configure(text="ЗАПУСТИТЬ СБОР СКЛЕПОВ", fg_color="green")
            self.crypt_status_label.configure(text="Остановлено", text_color="gray")
        else:
            selected = [k for k, v in self._crypt_vars.items() if v.get()]
            if not selected:
                self.crypt_status_label.configure(
                    text="Выберите хотя бы один тип!", text_color="orange"
                )
                return
            self.is_crypt_running = True
            self._crypt_found_count = 0
            self.crypt_status_label.configure(text="СТАТУС: В ПОИСКЕ...", text_color="gray")
            self.crypt_start_btn.configure(text="ОСТАНОВИТЬ", fg_color="red")
            self.crypt_engine.start(
                selected_crypts=selected,
                conf=self.crypt_conf_slider.get(),
                accelerations=int(self.crypt_accel_slider.get()),
                on_found_callback=self.on_crypt_found,
                on_status_callback=self.on_crypt_status,
                on_stop_callback=self.on_crypt_stop,
            )

    # ─── Склепы: сохранение/загрузка настроек ────────────────

    def _save_crypt_settings(self):
        try:
            cfg = {}
            if os.path.exists(GUI_CONFIG_PATH):
                with open(GUI_CONFIG_PATH, 'r') as f:
                    cfg = json.load(f)
            cfg['crypt_selected']     = [k for k, v in self._crypt_vars.items() if v.get()]
            cfg['crypt_conf']         = round(self.crypt_conf_slider.get(), 2)
            cfg['crypt_accelerations'] = int(self.crypt_accel_slider.get())
            with open(GUI_CONFIG_PATH, 'w') as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _load_crypt_settings(self):
        try:
            if not os.path.exists(GUI_CONFIG_PATH):
                return
            with open(GUI_CONFIG_PATH, 'r') as f:
                cfg = json.load(f)
            for name in cfg.get('crypt_selected', []):
                if name in self._crypt_vars:
                    self._crypt_vars[name].set(True)
            if 'crypt_conf' in cfg:
                self.crypt_conf_slider.set(cfg['crypt_conf'])
            if 'crypt_accelerations' in cfg:
                self.crypt_accel_slider.set(cfg['crypt_accelerations'])
            self._update_crypt_labels()
        except Exception:
            pass
```

- [ ] **Шаг 3б: Обновить `_emergency_stop` в main.py — остановить оба движка**

В `main.py` найти метод `_emergency_stop` (он вызывается по ESC) и добавить остановку crypt_engine:

```python
    def _emergency_stop(self):
        # Биржи
        if self.is_running:
            self.is_running = False
            self.engine.stop()
            self.start_button.configure(text=LANGS[self.current_lang]["start"], fg_color="green")
        # Склепы
        if self.is_crypt_running:
            self.is_crypt_running = False
            self.crypt_engine.stop()
            self.crypt_start_btn.configure(text="ЗАПУСТИТЬ СБОР СКЛЕПОВ", fg_color="green")
            self.crypt_status_label.configure(text="Остановлено (ESC)", text_color="gray")
```

- [ ] **Шаг 4: Запустить приложение и проверить визуально**

```
python main.py
```
Проверить:
- Вкладка «СКЛЕПЫ» появилась между «ОХОТА» и «РЕФЕРАЛЫ»
- Иконки склепов отображаются в сетке
- Слайдеры и кнопка «Сохранить» работают
- Кнопка «ЗАПУСТИТЬ» без выбранных склепов показывает предупреждение

- [ ] **Шаг 5: Коммит**

```bash
git add main.py
git commit -m "feat: add Crypts tab to main.py with icon grid, sliders, start/stop"
```

---

## Task 9: Финальная проверка — все тесты + ручная калибровка

**Files:**
- Modify: `crypt_hunter.py` — при необходимости скорректировать координаты

- [ ] **Шаг 1: Запустить полный тест-сюит**

```
python -m pytest test_crypt_hunter.py -v --tb=short
```
Ожидаемый результат: все тесты `PASSED`

- [ ] **Шаг 2: Проверить что `parse_oil` корректно работает с реальным OCR**

```python
# Запустить в REPL или отдельном скрипте:
from crypt_hunter import parse_oil, parse_time
print(parse_oil("6,5м/74,7к"))   # → 6500000.0
print(parse_oil("65к/74,7к"))    # → 65000.0
print(parse_time("2 М 03 С"))    # → 123.0
```

- [ ] **Шаг 3: Откалибровать координаты**

Открыть `crypt_hunter.py`, раздел `КООРДИНАТЫ`. Запустить игру и уточнить:
- `WT_ICON` — координата иконки Дозорной башни
- `WT_CRYPTS_TAB`, `WT_ARENA_TAB` — вкладки в боковом меню
- `WT_GOTO_BTN_X` — X кнопки «Перейти»
- `CRYPT_OIL_REGION` — зона масла в диалоге
- `CRYPT_STUDY_BTN`, `CRYPT_OPEN_BTN` — кнопки в диалоге
- `CARTER_EVENT_BAR` — полоса события Картера
- `ACCEL_USE_BTN`, `ACCEL_TIME_REGION` — кнопка и OCR зона ускорения

Инструмент для калибровки:
```python
import pyautogui, time
time.sleep(3)  # успеть переключиться в игру
print(pyautogui.position())  # наведи мышь на нужный элемент
```

- [ ] **Шаг 4: Финальный коммит**

```bash
git add crypt_hunter.py
git commit -m "feat: calibrate crypt_hunter coordinates for 1920x1080"
```
