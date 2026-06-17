# Nav Card + Oil Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить карточку "Навигация" с 3 главными ползунками в Биржах, расширить TTL следов до 20 мин, добавить HSV-детект диалога масла в Склепах.

**Architecture:** UI-изменения — только main.py (перемещение виджетов, новый CTkFrame). Логика масла — только crypt_hunter.py (новый метод `_detect_oil_buttons` + вызов в `_send_captain`). Никакие другие файлы не трогаем.

**Tech Stack:** CustomTkinter, OpenCV (cv2.inRange HSV), numpy, pytest/unittest.mock

---

## Файлы

| Файл | Что меняем |
|---|---|
| `main.py` | Создаём `nav_main_frame` (карточка «Навигация»), перемещаем 3 слайдера, TTL→1200, label в минутах |
| `crypt_hunter.py` | Добавляем `_detect_oil_buttons()`, `_check_oil_dialog()`, правим `_send_captain()` |
| `test_crypt_hunter.py` | Добавляем `TestDetectOilButtons`, обновляем `TestSendCaptainVerification` |

---

## Task 1: TDD — _detect_oil_buttons()

**Files:**
- Modify: `test_crypt_hunter.py`
- Modify: `crypt_hunter.py`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `test_crypt_hunter.py` после `TestSendCaptainVerification`:

```python
class TestDetectOilButtons:
    """
    _detect_oil_buttons(img_bgr) -> bool
    True если в img_bgr достаточно зелёных (масло на складе)
    или синих (кнопка "Купить") пикселей.
    Порог: 100 пикселей.
    """

    def _make_hunter(self):
        from unittest.mock import patch, MagicMock
        with patch('crypt_hunter.YOLO', return_value=MagicMock()):
            from crypt_hunter import CryptHunter
            h = CryptHunter.__new__(CryptHunter)
            h.is_running = True
            h.on_status_callback = None
            return h

    def _solid_bgr(self, bgr, h=100, w=200):
        """Создаём numpy BGR изображение одного цвета."""
        import numpy as np
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :] = bgr
        return img

    def test_black_image_returns_false(self):
        hunter = self._make_hunter()
        img = self._solid_bgr((0, 0, 0))
        assert hunter._detect_oil_buttons(img) is False

    def test_green_button_returns_true(self):
        # BGR зелёного "Использовать": примерно (30, 180, 60) = чистый зелёный
        hunter = self._make_hunter()
        img = self._solid_bgr((30, 180, 60))
        assert hunter._detect_oil_buttons(img) is True

    def test_blue_button_returns_true(self):
        # BGR синего "Купить": примерно (200, 120, 60) = medium blue в BGR
        hunter = self._make_hunter()
        img = self._solid_bgr((200, 120, 60))
        assert hunter._detect_oil_buttons(img) is True

    def test_red_image_returns_false(self):
        # Красный — не масляный диалог
        hunter = self._make_hunter()
        img = self._solid_bgr((0, 0, 200))
        assert hunter._detect_oil_buttons(img) is False

    def test_few_green_pixels_returns_false(self):
        # Менее 100 зелёных пикселей — шум, не диалог
        import numpy as np
        hunter = self._make_hunter()
        img = self._solid_bgr((0, 0, 0), h=100, w=200)
        img[0:5, 0:10] = (30, 180, 60)   # 50 пикселей — ниже порога
        assert hunter._detect_oil_buttons(img) is False

    def test_enough_green_pixels_returns_true(self):
        # Более 100 зелёных пикселей — диалог обнаружен
        import numpy as np
        hunter = self._make_hunter()
        img = self._solid_bgr((0, 0, 0), h=100, w=200)
        img[0:10, 0:20] = (30, 180, 60)  # 200 пикселей — выше порога
        assert hunter._detect_oil_buttons(img) is True
```

- [ ] **Step 2: Убедиться что тесты падают**

```
cd C:\BattleBot
python -m pytest test_crypt_hunter.py::TestDetectOilButtons -v
```

Ожидаем: `FAILED` с `AttributeError: '_detect_oil_buttons'`

- [ ] **Step 3: Реализовать `_detect_oil_buttons()` в crypt_hunter.py**

Добавить метод в класс `CryptHunter` после `_find_button()` (строка ~661):

```python
def _detect_oil_buttons(self, img_bgr: 'np.ndarray') -> bool:
    """
    Ищет зелёные (использовать) или синие (купить) кнопки в BGR-изображении.
    Возвращает True если найдено ≥ 100 таких пикселей → масляный диалог.
    HSV scale: H 0-180, S 0-255, V 0-255 (OpenCV convention).
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # Зелёная кнопка «Использовать» (масло на складе)
    green_mask = cv2.inRange(
        hsv,
        np.array([35,  80,  80]),
        np.array([85, 255, 220]),
    )
    # Синяя кнопка «Купить» (покупка масла)
    blue_mask = cv2.inRange(
        hsv,
        np.array([100,  80,  80]),
        np.array([130, 255, 230]),
    )
    return int(green_mask.sum() // 255 + blue_mask.sum() // 255) >= 100
```

- [ ] **Step 4: Прогнать тесты**

```
python -m pytest test_crypt_hunter.py::TestDetectOilButtons -v
```

Ожидаем: 6 тестов `PASSED`.

- [ ] **Step 5: Прогнать все тесты — убедиться ничего не сломали**

```
python -m pytest test_crypt_hunter.py -v
```

Ожидаем: 35 тестов `PASSED` (29 старых + 6 новых).

- [ ] **Step 6: Коммит**

```
git add test_crypt_hunter.py crypt_hunter.py
git commit -m "feat: add _detect_oil_buttons() with HSV detection for oil dialog"
```

---

## Task 2: _check_oil_dialog() + модификация _send_captain()

**Files:**
- Modify: `crypt_hunter.py`
- Modify: `test_crypt_hunter.py`

- [ ] **Step 1: Написать падающий тест на _check_oil_dialog()**

Добавить в `test_crypt_hunter.py` в конец класса `TestDetectOilButtons`:

```python
    def test_check_oil_dialog_returns_true_when_buttons_found(self):
        from unittest.mock import patch
        import numpy as np
        hunter = self._make_hunter()
        # Мокаем скриншот — возвращаем зелёное изображение (кнопка масла)
        green_img = self._solid_bgr((30, 180, 60), h=420, w=550)
        with patch.object(hunter, '_screenshot', return_value=green_img):
            result = hunter._check_oil_dialog()
        assert result is True

    def test_check_oil_dialog_returns_false_when_no_buttons(self):
        from unittest.mock import patch
        import numpy as np
        hunter = self._make_hunter()
        black_img = self._solid_bgr((0, 0, 0), h=420, w=550)
        with patch.object(hunter, '_screenshot', return_value=black_img):
            result = hunter._check_oil_dialog()
        assert result is False
```

- [ ] **Step 2: Написать падающий тест на _send_captain() с маслом**

Обновить класс `TestSendCaptainVerification` — добавить новый тест (старый `test_returns_true_always` оставить):

```python
    def test_returns_false_when_oil_dialog_detected(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    with patch.object(hunter, '_interruptible_sleep'):
                        with patch.object(hunter, '_check_oil_dialog', return_value=True):
                            with patch.object(hunter, '_emergency_stop') as mock_stop:
                                result = hunter._send_captain('Ordinary_1')
        assert result is False
        mock_stop.assert_called_once_with("OIL_LOW: масло закончилось")

    def test_returns_true_when_no_oil_dialog(self):
        from unittest.mock import patch
        hunter = self._make_hunter()
        with patch('crypt_hunter._VISUAL_NAV_AVAILABLE', False):
            with patch.object(hunter, '_click'):
                with patch.object(hunter, '_random_pause'):
                    with patch.object(hunter, '_interruptible_sleep'):
                        with patch.object(hunter, '_check_oil_dialog', return_value=False):
                            result = hunter._send_captain('Ordinary_1')
        assert result is True
```

- [ ] **Step 3: Убедиться что тесты падают**

```
python -m pytest test_crypt_hunter.py::TestDetectOilButtons::test_check_oil_dialog_returns_true_when_buttons_found test_crypt_hunter.py::TestDetectOilButtons::test_check_oil_dialog_returns_false_when_no_buttons test_crypt_hunter.py::TestSendCaptainVerification::test_returns_false_when_oil_dialog_detected test_crypt_hunter.py::TestSendCaptainVerification::test_returns_true_when_no_oil_dialog -v
```

Ожидаем: `FAILED` — `AttributeError: '_check_oil_dialog'`

- [ ] **Step 4: Реализовать `_check_oil_dialog()` в crypt_hunter.py**

Добавить после `_detect_oil_buttons()`:

```python
OIL_DIALOG_REGION = (580, 280, 550, 420)   # (x, y, w, h) в 1920×1080

def _check_oil_dialog(self) -> bool:
    """
    Делает скриншот центра экрана и проверяет наличие кнопок диалога масла.
    Вызывается из _send_captain() через 1.5с после клика «Исследовать».
    Не зависит от языка игры — ищет цвет кнопок, не текст.
    """
    img = self._screenshot(OIL_DIALOG_REGION)
    return self._detect_oil_buttons(img)
```

Добавить константу `OIL_DIALOG_REGION` в блок констант вверху файла (после `ACCEL_TIME_REGION`):

```python
# Центральный регион экрана где появляется диалог масла
OIL_DIALOG_REGION = (580, 280, 550, 420)   # (x, y, w, h) в 1920×1080
```

- [ ] **Step 5: Изменить `_send_captain()` в crypt_hunter.py**

Заменить метод `_send_captain()` целиком (строки ~565-572):

```python
def _send_captain(self, crypt_type: str) -> bool:
    """Нажать «Исследовать». Возвращает False если появился диалог масла."""
    self._random_pause()
    self._status("Нажимаю «Исследовать»...")
    sc = scale_dialog(*CRYPT_STUDY_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_STUDY_BTN
    self._click(*sc, raw=True)
    self._interruptible_sleep(1.5)
    if self._check_oil_dialog():
        self._emergency_stop("OIL_LOW: масло закончилось")
        return False
    self._random_pause(0.3, 0.8)
    return True
```

- [ ] **Step 6: Прогнать все тесты**

```
python -m pytest test_crypt_hunter.py -v
```

Ожидаем: 37 тестов `PASSED`.

- [ ] **Step 7: Коммит**

```
git add crypt_hunter.py test_crypt_hunter.py
git commit -m "feat: stop crypt bot when oil dialog detected after Исследовать"
```

---

## Task 3: UI — Карточка «Навигация» с 3 главными ползунками

**Files:**
- Modify: `main.py` (функция `setup_hunt_tab`, строки ~265–551)

Задача: создать новый `nav_main_frame` после `nn_frame`, переместить туда Шаг/Скорость/Глубина нырка, убрать их из `nav_frame`.

- [ ] **Step 1: Создать nav_main_frame сразу после nn_frame**

Найти в `setup_hunt_tab()` строку после `self.speed_slider.pack(...)` (конец nn_frame, строка ~327):

```python
        self.speed_slider.pack(padx=12, pady=(2, 10), fill="x")
```

После неё вставить:

```python

        # ─── Карточка «Навигация» — три главных ползунка ─────────────────────
        nav_main_frame = ctk.CTkFrame(self.tab_hunt, fg_color=MD3["elevated"],
                                      corner_radius=12, border_width=1,
                                      border_color=MD3["outline"])
        nav_main_frame.pack(fill="x", padx=20, pady=(4, 4))
        ctk.CTkLabel(nav_main_frame, text="Навигация",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MD3["on_surface"]).pack(anchor="w", padx=12, pady=(8, 2))

        # Шаг джойстика
        self.nav_step_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_step_frame.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(self.nav_step_frame, text="Шаг:",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
        self.nav_step_val = ctk.CTkLabel(self.nav_step_frame, text="13 px",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=MD3["value_text"])
        self.nav_step_val.pack(side="right")
        self.nav_step_slider = ctk.CTkSlider(nav_main_frame, from_=10, to=20,
                                              number_of_steps=10,
                                              command=self._update_nav_labels_and_dot,
                                              button_color=MD3["primary"],
                                              button_hover_color=MD3["primary_dim"],
                                              progress_color=MD3["primary"])
        self.nav_step_slider.set(13)
        self.nav_step_slider.pack(padx=12, pady=(2, 4), fill="x")

        # Скорость (ожидание после шага)
        self.nav_wait_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_wait_frame.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(self.nav_wait_frame, text="Скорость (сек/шаг):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
        self.nav_wait_val = ctk.CTkLabel(self.nav_wait_frame, text="2.0 с",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=MD3["value_text"])
        self.nav_wait_val.pack(side="right")
        self.nav_wait_slider = ctk.CTkSlider(nav_main_frame, from_=0.5, to=5.0,
                                             command=self._update_nav_labels,
                                             button_color=MD3["primary"],
                                             button_hover_color=MD3["primary_dim"],
                                             progress_color=MD3["primary"])
        self.nav_wait_slider.set(2.0)
        self.nav_wait_slider.pack(padx=12, pady=(2, 4), fill="x")

        # Глубина нырка
        self.nav_inland_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_inland_frame.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(self.nav_inland_frame, text="Глубина нырка (экранов):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
        self.nav_inland_val = ctk.CTkLabel(self.nav_inland_frame, text="5",
                                           font=ctk.CTkFont(size=14, weight="bold"),
                                           text_color=MD3["value_text"])
        self.nav_inland_val.pack(side="right")
        self.nav_inland_slider = ctk.CTkSlider(
            nav_main_frame, from_=1, to=10, number_of_steps=9,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_inland_slider.set(5)
        self.nav_inland_slider.pack(padx=12, pady=(2, 8), fill="x")
```

- [ ] **Step 2: Удалить старые блоки Шаг/Скорость/Глубина нырка из nav_frame**

Найти и удалить из `setup_hunt_tab()` следующие блоки (они теперь в nav_main_frame):

**Удалить** блок "Шаг джойстика" (строки ~385–401):
```python
        # Шаг джойстика
        self.nav_step_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        ...
        self.nav_step_slider.pack(padx=10, pady=(0, 2), fill="x")
```

**Удалить** блок "Скорость (ожидание после шага)" (строки ~403–419):
```python
        # Скорость (ожидание после шага)
        self.nav_wait_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        ...
        self.nav_wait_slider.pack(padx=10, pady=(0, 2), fill="x")
```

**Удалить** из `nav_sliders_frame` блок "Глубина нырка" (строки ~429–446):
```python
        # Глубина нырка (экранов)
        self.nav_inland_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        ...
        self.nav_inland_slider.pack(padx=10, pady=(0, 2), fill="x")
```

- [ ] **Step 3: Переименовать заголовок nav_frame**

Найти строку (около ~337):
```python
        self.nav_lb = ctk.CTkLabel(self.nav_header_frame,
                                   text="Навигация (мини-карта)",
```
Изменить text:
```python
        self.nav_lb = ctk.CTkLabel(self.nav_header_frame,
                                   text="Дополнительно",
```

- [ ] **Step 4: Убедиться что _on_nav_toggle() корректен**

Найти `_on_nav_toggle()` (строка ~1096):
```python
    def _on_nav_toggle(self):
        enabled = self.nav_enabled_var.get()
        state = "normal" if enabled else "disabled"
        for w in (self.nav_step_slider, self.nav_wait_slider,
                  self.nav_cx_entry, self.nav_cy_entry):
            w.configure(state=state)
```
Оставить как есть — `self.nav_step_slider` и `self.nav_wait_slider` по-прежнему доступны через self.

- [ ] **Step 5: Запустить приложение и проверить UI**

```
cd C:\BattleBot
python main.py
```

Проверить визуально:
- Карточка "Нейросеть" видна (acc + speed sliders)
- Карточка "Навигация" видна под ней (Шаг, Скорость, Глубина нырка)
- Под ней "Дополнительно" с Center X/Y и scrollable frame
- В scrollable frame: Граница, Водоём, Диагональ, Конус, Память следов
- Шаг slider ходит от 10 до 20
- Кнопка ЗАПУСТИТЬ ОХОТУ видна внизу

- [ ] **Step 6: Коммит**

```
git add main.py
git commit -m "feat: new Навигация card with 3 main sliders (Шаг to=20, Скорость, Глубина)"
```

---

## Task 4: UI — Память следов → 20 минут

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Обновить nav_footprint_slider**

Найти в `nav_sliders_frame` секцию "Память следов" (строка ~524):

```python
        self.nav_footprint_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=10, to=300, number_of_steps=29,
```

Заменить на:

```python
        self.nav_footprint_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=60, to=1200, number_of_steps=19,
```

- [ ] **Step 2: Обновить default label и set()**

Найти строки рядом с footprint_slider:
```python
        self.nav_footprint_val = ctk.CTkLabel(self.nav_footprint_frame, text="120 с",
```
Заменить на:
```python
        self.nav_footprint_val = ctk.CTkLabel(self.nav_footprint_frame, text="2 мин",
```

`self.nav_footprint_slider.set(120)` — оставить (120 сек = 2 мин, попадает в диапазон 60–1200).

- [ ] **Step 3: Обновить _update_nav_labels() для минутного отображения**

Найти в `_update_nav_labels()` (строка ~1112):
```python
        self.nav_footprint_val.configure(text=f"{int(self.nav_footprint_slider.get())} с")
```
Заменить на:
```python
        ttl = int(self.nav_footprint_slider.get())
        self.nav_footprint_val.configure(
            text=f"{ttl // 60} мин" if ttl >= 60 else f"{ttl} с"
        )
```

- [ ] **Step 4: Обновить _load_settings() — защита от старых значений**

Найти строку (около ~1190):
```python
            self.nav_footprint_slider.set(cfg.get("nav_footprint_ttl", 120))
```
Заменить на:
```python
            raw_ttl = cfg.get("nav_footprint_ttl", 120)
            self.nav_footprint_slider.set(max(60, min(1200, int(raw_ttl))))
```

- [ ] **Step 5: Запустить и проверить**

```
python main.py
```

- Во вкладке БИРЖИ прокрутить "Дополнительно" → Память следов
- Slider должен ходить от 60 (1 мин) до 1200 (20 мин)
- При движении label показывает "X мин"
- Default = "2 мин"

- [ ] **Step 6: Коммит**

```
git add main.py
git commit -m "feat: expand footprint TTL slider to 20 min with minute display"
```

---

## Self-Review

**Spec coverage:**
- ✅ Карточка "Навигация" (styled как Нейросеть) с 3 слайдерами — Task 3
- ✅ Шаг: label "Шаг:", to=20, number_of_steps=10 — Task 3
- ✅ Память следов to=1200, display в минутах — Task 4
- ✅ `_detect_oil_buttons()` HSV зелёный + синий, порог 100px — Task 1
- ✅ `_check_oil_dialog()` screenshot + вызов детекта — Task 2
- ✅ `_send_captain()` interruptible_sleep(1.5) + check + emergency_stop — Task 2
- ✅ GUI OIL_LOW уже обрабатывается в on_crypt_stop() — не трогаем

**Placeholder scan:** нет TBD/TODO

**Type consistency:**
- `_detect_oil_buttons(img_bgr: np.ndarray) -> bool` — используется в Task 1 тестах и Task 2 `_check_oil_dialog()`
- `OIL_DIALOG_REGION` — константа, определена в Task 2 Step 4 в блоке констант файла
- `self.nav_step_slider`, `self.nav_wait_slider`, `self.nav_inland_slider` — определены в Task 3 Step 1 (nav_main_frame), читаются в `_save_settings`, `_load_settings`, `toggle_bot`, `_on_nav_toggle`, `_update_nav_labels` — все через `self.xxx`, родительский виджет не важен ✅
