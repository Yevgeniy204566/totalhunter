# Combiner Module — Design Spec
**Date:** 2026-04-30  
**Status:** Approved by Gemini Architect + User

---

## 1. Цель

Модуль автоматизирует процесс комбинирования (повышения качества) игровых материалов в окне «Комбинирование» Total Battle. Пользователь открывает окно вручную, нажимает Старт — бот обходит сетку и кликает карточки.

---

## 2. Правила обработки карточек

- **Единое правило:** OCR читает число с карточки. Если `число >= 4` — кликаем `число // 4` раз. Если `число < 4` или число не распознано — пропускаем.
- **Правая карточка в ряду** (индекс `MAX_COLS - 1`) — всегда пропускается. Это карточка высшего качества (жёлтая/золотая).
- Направление обхода: слева→направо, сверху→вниз.
- После обработки всех видимых рядов — скролл вниз, затем повтор.
- Стоп: после скролла новых карточек не появилось.

---

## 3. Архитектура

### Новые файлы
| Файл | Назначение |
|------|-----------|
| `combiner.py` | `CombinerEngine` — вся логика |
| `test_combiner.py` | TDD-тесты |

### Изменения
| Файл | Изменение |
|------|-----------|
| `main.py` | Вкладка Combo после БИРЖИ, `setup_combo_tab()` |
| `LANGS` dict | Ключ `"tab_combo": "Combo"` (RU и EN одинаково) |

### CombinerEngine API
```python
class CombinerEngine:
    delay: float                        # сек между кликами (0.05–0.5)
    _stop_requested: bool

    def run(self, status_callback)      # главный цикл
    def stop()                          # флаг остановки
    def scan_row(row_idx) -> list[CardInfo]
    def parse_number(text: str) -> int  # "4.1k"→4100, "1.2M"→1200000
    def click_card(card, n_clicks)      # с рандомизацией 3-5px + флаг внутри цикла
    def _zoom_ocr(region) -> str        # upscale x2 + инверсия + tesseract
    def _scroll_down()                  # pyautogui.scroll(-500) + sleep(1)
    def _check_window_visible() -> bool # anti-stuck
```

---

## 4. Детали реализации

### OCR (Zoom-OCR)
1. Вырезать область числа — фиксированный offset от угла карточки
2. Упскейл ×2 через `cv2.resize` (INTER_CUBIC)
3. Конвертация в grayscale → инверсия (`cv2.bitwise_not`) → threshold
4. `pytesseract.image_to_string(config='--psm 7 -c tessedit_char_whitelist=0123456789kKmM.,')` 
5. `parse_number()` → `int`

### parse_number
- Поддерживаемые форматы: `4.1k`, `4,1k`, `1.2M`, `500`, `1.0k`
- `4.1k // 4 = 1025`
- Если строка не парсится → возвращает `0` (карточка пропускается)

### click_card
```python
def click_card(self, card: CardInfo, n_clicks: int):
    for _ in range(n_clicks):
        if self._stop_requested:
            return
        dx = random.randint(-5, 5)
        dy = random.randint(-5, 5)
        pyautogui.click(card.click_x + dx, card.click_y + dy)
        time.sleep(self.delay)
```

### Скролл
- `pyautogui.scroll(-500)` на области сетки
- `time.sleep(1.0)` для стабилизации
- Сравниваем хэш региона до/после скролла — если одинаковый, стоп

### Anti-Stuck
- Перед каждым рядом — `_check_window_visible()`
- Ищем пиксель заголовка окна (характерный цвет)
- Если окно перекрыто: пауза 2 сек, повтор, затем `stop()`

---

## 5. GUI — вкладка Combo

- Позиция: после БИРЖИ, перед РЕФЕРАЛЫ
- Компоненты:
  - `CTkButton` — «ЗАПУСТИТЬ COMBO» / «СТОП»
  - `CTkSlider` — задержка 0.05–0.5 сек, default 0.1 сек
  - `CTkLabel` — статус: `«Ряд 2, карточка 3 — 128 кликов»`
- Стиль: MD3, `fg_color=MD3["elevated"]`, аналогично другим вкладкам

---

## 6. TDD — test_combiner.py

Обязательные тесты:
```
test_parse_4_1k       → 4100
test_parse_1_2M       → 1200000  
test_parse_500        → 500
test_parse_1_0k       → 1000
test_parse_4_1k_div4  → 1025
test_parse_invalid    → 0
test_parse_lt4        → пропуск
test_stop_flag        → прерывание внутри цикла кликов
test_skip_last_col    → правая карточка всегда пропускается
```

---

## 7. Стек

Python 3.13, CustomTkinter, OpenCV, pytesseract, pyautogui, MSS
