# Auto-Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить кнопку АВТОКАЛИБРОВАТЬ, которая автоматически находит Point A (белый прямоугольник джойстика миникарты) и Point B (жёлто-зелёный "+" серебра через hover-diff) и открывает лупу уже на найденных координатах.

**Architecture:** Новый модуль `auto_calibration.py` содержит три чистые функции: `scale_ref`, `detect_point_a_in_region`, `detect_point_b_from_diff`, объединённые в `auto_detect_points`. `calibration_ui.py` получает два опциональных параметра `start_a`/`start_b`. В `main.py` добавляется одна кнопка АВТОКАЛИБРОВАТЬ над существующей.

**Tech Stack:** Python 3.13, OpenCV (cv2), mss, pyautogui, pytest, CustomTkinter

---

## File Map

| Файл | Действие | Ответственность |
|------|----------|-----------------|
| `auto_calibration.py` | **Создать** | Вся логика детекции |
| `test_auto_calibration.py` | **Создать** | Unit-тесты с синтетическими изображениями |
| `calibration_ui.py` | **Изменить** | Добавить `start_a`/`start_b` в `run_calibration()` |
| `main.py` | **Изменить** | Кнопка АВТОКАЛИБРОВАТЬ + handler `_auto_calibrate` |

---

## Task 1: calibration_ui.py — optional start_a / start_b

**Files:**
- Modify: `calibration_ui.py:191-225`

### Что делаем

`run_calibration()` сейчас всегда открывает лупу на `REF_A` и `REF_B`.
Добавляем параметры `start_a` и `start_b` — если переданы, лупа открывается на них.
Существующий вызов `run_calibration(parent=self)` — без изменений в поведении.

- [ ] **Step 1: Написать тест**

Создать файл `test_auto_calibration.py`:

```python
import tkinter as tk
from unittest.mock import patch
import calibration_ui
from coord_manager import REF_A, REF_B


def test_run_calibration_passes_start_a_to_point_dialog(monkeypatch):
    """Когда start_a передан — лупа открывается на start_a, не на REF_A."""
    calls = []

    def fake_calibrate_one(root, start_pos, label_text):
        calls.append(start_pos)
        return start_pos  # симулируем нажатие «Зафиксировать»

    monkeypatch.setattr(calibration_ui, "_calibrate_one_point", fake_calibrate_one)

    root = tk.Tk()
    root.withdraw()
    try:
        pa, pb = calibration_ui.run_calibration(
            parent=root, start_a=(111, 222), start_b=(333, 444)
        )
    finally:
        root.destroy()

    assert calls[0] == (111, 222), f"Point A start: expected (111,222), got {calls[0]}"
    assert calls[1] == (333, 444), f"Point B start: expected (333,444), got {calls[1]}"
    assert pa == (111, 222)
    assert pb == (333, 444)


def test_run_calibration_defaults_to_ref_when_no_start(monkeypatch):
    """Без start_a/start_b используются REF_A / REF_B."""
    calls = []

    def fake_calibrate_one(root, start_pos, label_text):
        calls.append(start_pos)
        return start_pos

    monkeypatch.setattr(calibration_ui, "_calibrate_one_point", fake_calibrate_one)

    root = tk.Tk()
    root.withdraw()
    try:
        calibration_ui.run_calibration(parent=root)
    finally:
        root.destroy()

    assert calls[0] == REF_A
    assert calls[1] == REF_B
```

- [ ] **Step 2: Запустить тест — убедиться что FAIL**

```
pytest test_auto_calibration.py::test_run_calibration_passes_start_a_to_point_dialog -v
```
Ожидаем: `TypeError` — `run_calibration() got unexpected keyword argument 'start_a'`

- [ ] **Step 3: Реализовать изменение в calibration_ui.py**

Найти строку 191:
```python
def run_calibration(parent: "tk.Misc | None" = None) -> "tuple[tuple[int,int]|None, tuple[int,int]|None]":
```

Заменить на:
```python
def run_calibration(
    parent: "tk.Misc | None" = None,
    start_a: "tuple[int,int] | None" = None,
    start_b: "tuple[int,int] | None" = None,
) -> "tuple[tuple[int,int]|None, tuple[int,int]|None]":
```

Найти строку (внутри функции):
```python
    point_a = _calibrate_one_point(
        root, REF_A,
        "Точка А — центр мини-карты (лево-низ)",
    )
```

Заменить на:
```python
    point_a = _calibrate_one_point(
        root, start_a if start_a is not None else REF_A,
        "Точка А — центр мини-карты (лево-низ)",
    )
```

Найти строку:
```python
    point_b = _calibrate_one_point(
        root, REF_B,
        "Точка Б — крестик серебра (право-верх)",
    )
```

Заменить на:
```python
    point_b = _calibrate_one_point(
        root, start_b if start_b is not None else REF_B,
        "Точка Б — крестик серебра (право-верх)",
    )
```

- [ ] **Step 4: Запустить тесты — убедиться что PASS**

```
pytest test_auto_calibration.py -v
```
Ожидаем: 2 PASSED

- [ ] **Step 5: Коммит**

```bash
git add calibration_ui.py test_auto_calibration.py
git commit -m "feat(calibration): run_calibration принимает start_a/start_b + тесты"
```

---

## Task 2: auto_calibration.py — scale_ref + detect_point_a_in_region

**Files:**
- Create: `auto_calibration.py`
- Modify: `test_auto_calibration.py`

### Что делаем

Создаём `auto_calibration.py` с двумя первыми функциями:
- `scale_ref(ref, screen_w, screen_h)` — масштабирует REF_A/REF_B на реальное разрешение
- `detect_point_a_in_region(img)` — ищет белый прямоугольный контур, возвращает его центр или None

- [ ] **Step 1: Написать тесты**

Добавить в `test_auto_calibration.py`:

```python
import cv2
import numpy as np
from auto_calibration import scale_ref, detect_point_a_in_region
from coord_manager import REF_A, REF_B


def test_scale_ref_identity_1920x1080():
    assert scale_ref(REF_A, 1920, 1080) == REF_A
    assert scale_ref(REF_B, 1920, 1080) == REF_B


def test_scale_ref_double_resolution():
    a = scale_ref(REF_A, 3840, 2160)
    assert a == (REF_A[0] * 2, REF_A[1] * 2)


def test_scale_ref_non_integer_rounds_down():
    # 90 * 2560/1920 = 120.0 exactly
    a = scale_ref((90, 925), 2560, 1440)
    assert a == (120, int(925 * 1440 / 1080))


def test_detect_point_a_finds_white_rectangle():
    """Синтетическое изображение: тёмный фон + белый прямоугольник."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (80, 100), (180, 200), (255, 255, 255), 3)
    result = detect_point_a_in_region(img)
    assert result is not None
    cx, cy = result
    assert abs(cx - 130) <= 10, f"Ожидали cx≈130, получили {cx}"
    assert abs(cy - 150) <= 10, f"Ожидали cy≈150, получили {cy}"


def test_detect_point_a_returns_none_when_no_rect():
    """Полностью тёмное изображение — прямоугольник не найден."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    assert detect_point_a_in_region(img) is None


def test_detect_point_a_ignores_small_contours():
    """Маленький прямоугольник (< 500 px²) игнорируется."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (148, 148), (152, 152), (255, 255, 255), 1)  # 4x4 = 16px²
    assert detect_point_a_in_region(img) is None
```

- [ ] **Step 2: Запустить тесты — убедиться что FAIL**

```
pytest test_auto_calibration.py::test_scale_ref_identity_1920x1080 test_auto_calibration.py::test_detect_point_a_finds_white_rectangle -v
```
Ожидаем: `ImportError: cannot import name 'scale_ref' from 'auto_calibration'` (файла ещё нет)

- [ ] **Step 3: Создать auto_calibration.py с первыми двумя функциями**

Создать файл `auto_calibration.py`:

```python
import time
import numpy as np
import cv2
import pyautogui
from mss import mss as _mss

from coord_manager import REF_A, REF_B

_SEARCH_RADIUS = 150   # px вокруг масштабированной ref-точки
_DIFF_THRESHOLD = 30   # минимальная яркость diff чтобы считать пиксель «новым»
_DIFF_MIN_PX = 100     # минимум новых пикселей для valid detection
_HOVER_WAIT = 0.4      # секунды ожидания после наведения курсора
_CONTOUR_MIN_AREA = 500  # px² — минимальный прямоугольный контур Point A


def scale_ref(ref: tuple[int, int], screen_w: int, screen_h: int) -> tuple[int, int]:
    """Масштабирует эталонную координату (1920x1080) на реальное разрешение."""
    return (int(ref[0] * screen_w / 1920), int(ref[1] * screen_h / 1080))


def detect_point_a_in_region(img: np.ndarray) -> tuple[int, int] | None:
    """
    Ищет белый прямоугольный контур в img (BGR).
    Возвращает (x, y) центра в координатах img, или None если не найден.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
        if cv2.contourArea(cnt) < _CONTOUR_MIN_AREA:
            break
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(cnt)
            return (x + w // 2, y + h // 2)
    return None
```

- [ ] **Step 4: Запустить тесты — убедиться что PASS**

```
pytest test_auto_calibration.py -k "scale_ref or detect_point_a" -v
```
Ожидаем: 6 PASSED

- [ ] **Step 5: Коммит**

```bash
git add auto_calibration.py test_auto_calibration.py
git commit -m "feat(auto-cal): scale_ref + detect_point_a_in_region с тестами"
```

---

## Task 3: auto_calibration.py — detect_point_b_from_diff

**Files:**
- Modify: `auto_calibration.py`
- Modify: `test_auto_calibration.py`

### Что делаем

`detect_point_b_from_diff(baseline, hover)` — сравнивает два скриншота, находит центр появившихся пикселей (игровой "+" крестик серебра).

- [ ] **Step 1: Написать тесты**

Добавить в `test_auto_calibration.py`:

```python
from auto_calibration import detect_point_b_from_diff


def test_detect_point_b_finds_plus_shape():
    """Синтетический hover: жёлто-зелёный блочный + появляется по центру."""
    baseline = np.zeros((300, 300, 3), dtype=np.uint8)
    hover = baseline.copy()
    # Вертикальная полоса: x=130..170, y=110..190
    cv2.rectangle(hover, (130, 110), (170, 190), (50, 200, 100), -1)
    # Горизонтальная полоса: x=110..190, y=130..170
    cv2.rectangle(hover, (110, 130), (190, 170), (50, 200, 100), -1)
    result = detect_point_b_from_diff(baseline, hover)
    assert result is not None
    cx, cy = result
    assert abs(cx - 150) <= 15, f"Ожидали cx≈150, получили {cx}"
    assert abs(cy - 150) <= 15, f"Ожидали cy≈150, получили {cy}"


def test_detect_point_b_returns_none_when_no_diff():
    """Одинаковые скриншоты — ничего не появилось."""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    assert detect_point_b_from_diff(img, img) is None


def test_detect_point_b_ignores_small_diff():
    """Менее 100 новых пикселей — игнорируется (шум, не крестик)."""
    baseline = np.zeros((300, 300, 3), dtype=np.uint8)
    hover = baseline.copy()
    hover[100:103, 100:103] = (255, 255, 255)  # 9 пикселей
    assert detect_point_b_from_diff(baseline, hover) is None
```

- [ ] **Step 2: Запустить тесты — убедиться что FAIL**

```
pytest test_auto_calibration.py::test_detect_point_b_finds_plus_shape -v
```
Ожидаем: `ImportError: cannot import name 'detect_point_b_from_diff'`

- [ ] **Step 3: Добавить функцию в auto_calibration.py**

Добавить после `detect_point_a_in_region`:

```python
def detect_point_b_from_diff(
    baseline: np.ndarray, hover: np.ndarray
) -> tuple[int, int] | None:
    """
    Находит центр появившихся пикселей (hover - baseline).
    Возвращает (x, y) в координатах img, или None если ничего не появилось.
    """
    diff = cv2.absdiff(baseline, hover)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, _DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    if cv2.countNonZero(mask) < _DIFF_MIN_PX:
        return None
    pts = cv2.findNonZero(mask)
    x, y, w, h = cv2.boundingRect(pts)
    return (x + w // 2, y + h // 2)
```

- [ ] **Step 4: Запустить тесты — убедиться что PASS**

```
pytest test_auto_calibration.py -k "detect_point_b" -v
```
Ожидаем: 3 PASSED

- [ ] **Step 5: Коммит**

```bash
git add auto_calibration.py test_auto_calibration.py
git commit -m "feat(auto-cal): detect_point_b_from_diff с тестами"
```

---

## Task 4: auto_calibration.py — auto_detect_points (полная функция)

**Files:**
- Modify: `auto_calibration.py`
- Modify: `test_auto_calibration.py`

### Что делаем

`auto_detect_points(screen_w, screen_h)` — оркестратор: захватывает экран, вызывает детекторы, конвертирует img-координаты в screen-координаты, применяет фоллбэк.

- [ ] **Step 1: Написать тесты**

Добавить в `test_auto_calibration.py`:

```python
from unittest.mock import patch, call
from auto_calibration import auto_detect_points
from coord_manager import REF_A, REF_B


def test_auto_detect_points_fallback_when_nothing_found():
    """Пустые скриншоты → оба детектора возвращают None → фоллбэк на масштабированный REF."""
    blank = np.zeros((300, 300, 3), dtype=np.uint8)
    with patch("auto_calibration._grab_region", return_value=blank), \
         patch("auto_calibration.pyautogui") as mock_pag, \
         patch("auto_calibration.time") as mock_time:
        pa, pb = auto_detect_points(1920, 1080)
    # На 1920x1080 фоллбэк = REF_A и REF_B
    assert pa == REF_A
    assert pb == REF_B


def test_auto_detect_points_returns_screen_coords_when_found():
    """Детекторы нашли точки → возвращаем screen-координаты, не img-координаты."""
    blank = np.zeros((300, 300, 3), dtype=np.uint8)

    # Для Point A: белый прямоугольник в центре региона (150,150) в img-координатах
    img_a = blank.copy()
    cv2.rectangle(img_a, (130, 120), (180, 180), (255, 255, 255), 3)

    # Для Point B: hover с блочным + в центре
    img_b_hover = blank.copy()
    cv2.rectangle(img_b_hover, (130, 110), (170, 190), (50, 200, 100), -1)
    cv2.rectangle(img_b_hover, (110, 130), (190, 170), (50, 200, 100), -1)

    grab_calls = [img_a, blank, img_b_hover]
    grab_iter = iter(grab_calls)

    with patch("auto_calibration._grab_region", side_effect=lambda *a, **kw: next(grab_iter)), \
         patch("auto_calibration.pyautogui"), \
         patch("auto_calibration.time"):
        pa, pb = auto_detect_points(1920, 1080)

    # Point A: img cx≈155, img cy≈150 → screen = (REF_A[0] - 150 + 155, REF_A[1] - 150 + 150)
    expected_ax = REF_A[0] - 150 + 155
    expected_ay = REF_A[1] - 150 + 150
    assert abs(pa[0] - expected_ax) <= 10
    assert abs(pa[1] - expected_ay) <= 10

    # Point B: img cx≈150 → screen ≈ REF_B
    assert abs(pb[0] - REF_B[0]) <= 15
    assert abs(pb[1] - REF_B[1]) <= 15
```

- [ ] **Step 2: Запустить тесты — убедиться что FAIL**

```
pytest test_auto_calibration.py::test_auto_detect_points_fallback_when_nothing_found -v
```
Ожидаем: `ImportError` или `AttributeError` — функция не определена

- [ ] **Step 3: Добавить вспомогательный _grab_region и auto_detect_points**

Добавить в `auto_calibration.py` после импортов и констант:

```python
def _grab_region(cx: int, cy: int, radius: int = _SEARCH_RADIUS) -> np.ndarray:
    """Захватывает квадратный регион экрана radius×2 вокруг (cx, cy). Возвращает BGR np.ndarray."""
    x1 = max(0, cx - radius)
    y1 = max(0, cy - radius)
    with _mss() as sct:
        mon = {"left": x1, "top": y1, "width": radius * 2, "height": radius * 2}
        shot = sct.grab(mon)
    return np.array(shot)[:, :, :3]
```

Добавить в конец файла:

```python
def auto_detect_points(
    screen_w: int, screen_h: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Автоматически определяет Point A (джойстик миникарты) и Point B (крестик серебра).
    Всегда возвращает координаты: либо найденные, либо масштабированный REF как фоллбэк.
    """
    r = _SEARCH_RADIUS

    # ── Point A — белый прямоугольник джойстика ──────────────────────────
    a_cx, a_cy = scale_ref(REF_A, screen_w, screen_h)
    img_a = _grab_region(a_cx, a_cy)
    found_a = detect_point_a_in_region(img_a)
    if found_a is not None:
        point_a = (a_cx - r + found_a[0], a_cy - r + found_a[1])
    else:
        point_a = (a_cx, a_cy)

    # ── Point B — hover-diff жёлто-зелёного крестика ─────────────────────
    b_cx, b_cy = scale_ref(REF_B, screen_w, screen_h)
    baseline = _grab_region(b_cx, b_cy)
    pyautogui.moveTo(b_cx, b_cy, duration=0.15)
    time.sleep(_HOVER_WAIT)
    hover_img = _grab_region(b_cx, b_cy)
    found_b = detect_point_b_from_diff(baseline, hover_img)
    if found_b is not None:
        point_b = (b_cx - r + found_b[0], b_cy - r + found_b[1])
    else:
        point_b = (b_cx, b_cy)

    return point_a, point_b
```

- [ ] **Step 4: Запустить все тесты auto_calibration**

```
pytest test_auto_calibration.py -v
```
Ожидаем: все тесты PASSED (минимум 11)

- [ ] **Step 5: Коммит**

```bash
git add auto_calibration.py test_auto_calibration.py
git commit -m "feat(auto-cal): auto_detect_points — полная функция с фоллбэком"
```

---

## Task 5: main.py — кнопка АВТОКАЛИБРОВАТЬ

**Files:**
- Modify: `main.py:1621-1652` (функция `setup_calibration_tab`)

### Что делаем

Добавляем handler `_auto_calibrate` и кнопку **АВТОКАЛИБРОВАТЬ** над существующей кнопкой КАЛИБРОВАТЬ.

- [ ] **Step 1: Добавить handler _auto_calibrate в setup_calibration_tab**

В `main.py`, найти блок (строка ~1621):
```python
        def _calibrate():
            from calibration_ui import run_calibration
```

Добавить **перед** `def _calibrate()`:

```python
        def _auto_calibrate():
            from auto_calibration import auto_detect_points
            from calibration_ui import run_calibration
            self.withdraw()
            try:
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                start_a, start_b = auto_detect_points(screen_w, screen_h)
                point_a, point_b = run_calibration(
                    parent=self, start_a=start_a, start_b=start_b
                )
            except Exception as e:
                messagebox.showerror(
                    "Авто-калибровка",
                    f"Не удалось: {e}\nИспользуйте ручную КАЛИБРОВАТЬ.",
                )
                return
            finally:
                self.deiconify()
            if point_a and point_b:
                coord_manager.calibrate(point_a, point_b)
                _update_status()

```

- [ ] **Step 2: Добавить кнопку АВТОКАЛИБРОВАТЬ над кнопкой КАЛИБРОВАТЬ**

Найти в `main.py` (строка ~1641):
```python
        # ── Кнопка Калибровать — главная (error tonal) ───────────────────
        ctk.CTkButton(
            self.tab_calibration,
            text="КАЛИБРОВАТЬ",
```

Добавить **перед** этим блоком:

```python
        ctk.CTkButton(
            self.tab_calibration,
            text="АВТОКАЛИБРОВАТЬ",
            command=_auto_calibrate,
            fg_color=MD3["blue_btn"],
            hover_color=MD3["blue_hover"],
            text_color=MD3["on_surface"],
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(fill="x", padx=40, pady=(8, 2))

```

- [ ] **Step 3: Запустить программу и проверить вкладку КАЛИБРОВКА**

```
python main.py
```

Проверить визуально:
- Вкладка КАЛИБРОВКА содержит кнопку **АВТОКАЛИБРОВАТЬ** (синяя, над красной)
- Существующая кнопка **КАЛИБРОВАТЬ** на месте, работает как раньше
- Нажать АВТОКАЛИБРОВАТЬ при запущенной игре → лупа открывается на найденных координатах

- [ ] **Step 4: Запустить все тесты проекта**

```
pytest test_auto_calibration.py test_coastal_snake.py test_crypt_hunter.py test_combiner.py -v
```
Ожидаем: все зелёные, ничего не сломалось

- [ ] **Step 5: Финальный коммит**

```bash
git add main.py
git commit -m "feat(gui): кнопка АВТОКАЛИБРОВАТЬ на вкладке КАЛИБРОВКА"
```

---

## Self-Review

### Spec coverage
- [x] `auto_calibration.py` — Task 2, 3, 4
- [x] `test_auto_calibration.py` — Tasks 1-4 (11+ тестов)
- [x] `calibration_ui.py` start_a/start_b — Task 1
- [x] `main.py` кнопка + handler — Task 5
- [x] Фоллбэк для обоих детекторов — Task 4 (test_auto_detect_points_fallback)
- [x] Масштабирование REF на любое разрешение — Task 2

### Типы и сигнатуры
- `scale_ref(ref, screen_w, screen_h) → tuple[int,int]` — использован в Task 2 и 4 ✓
- `detect_point_a_in_region(img) → tuple|None` — Task 2, 4 ✓
- `detect_point_b_from_diff(baseline, hover) → tuple|None` — Task 3, 4 ✓
- `auto_detect_points(screen_w, screen_h) → (tuple, tuple)` — Task 4, 5 ✓
- `run_calibration(parent, start_a, start_b)` — Task 1, 5 ✓
- `_grab_region(cx, cy, radius)` — определён в Task 4, используется только там ✓
