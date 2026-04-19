# Дизайн: 2-точечная калибровка координат

**Дата:** 2026-04-09  
**Статус:** Утверждён

---

## Цель

Заменить `window_scaler.py` (поиск окна по заголовку + раздельный scale X/Y) на `CoordinateManager` с явной пользовательской 2-точечной калибровкой. Это даёт точное позиционирование кликов на любом разрешении и в любом браузере/клиенте.

---

## Эталонные якоря (1920×1080)

| Точка | Координаты | Описание |
|-------|-----------|----------|
| A (лево-низ) | `(90, 925)` | Центр мини-карты (из CLAUDE.md CENTER_X/CENTER_Y) |
| B (право-верх) | `(648, 47)` | Центр крестика «+» при наведении на серебро (уточнить в игре) |

Эти значения — константы в коде. Пользователь не меняет их вручную.

---

## Математика (Подход 2 — раздельные scale_x / scale_y)

```
scale_x = (B_user_x - A_user_x) / (B_ref_x - A_ref_x)   # B_ref_x - A_ref_x = 648 - 90 = 558
scale_y = (B_user_y - A_user_y) / (B_ref_y - A_ref_y)   # B_ref_y - A_ref_y = 47 - 925 = -878

x_screen = A_user_x + (x_ref - A_ref_x) * scale_x
y_screen = A_user_y + (y_ref - A_ref_y) * scale_y
```

Раздельные коэффициенты компенсируют браузерные тулбары (Chrome/Firefox), которые делают Y-соотношение иным относительно X.

---

## Файлы

| Файл | Действие | Описание |
|------|----------|----------|
| `coord_manager.py` | НОВЫЙ | CoordinateManager: математика + профили |
| `calibration_ui.py` | НОВЫЙ | GUI лупы (Tkinter) |
| `profiles/` | НОВАЯ ПАПКА | JSON-профили |
| `window_scaler.py` | УДАЛИТЬ | Заменяется coord_manager |
| `main.py` | ИЗМЕНИТЬ | Новая вкладка «Калибровка» |
| `crypt_hunter.py` | ИЗМЕНИТЬ | scale_coord/scale_region → coord_manager |

---

## `CoordinateManager` (coord_manager.py)

```python
REF_A = (90, 960)
REF_B = (1543, 87)

class CoordinateManager:
    scale_x: float = 1.0
    scale_y: float = 1.0
    anchor_x: int  # A_user_x
    anchor_y: int  # A_user_y

    def calibrate(self, a_user, b_user): ...
    def to_screen(self, x, y) -> tuple[int, int]: ...
    def to_region(self, x, y, w, h) -> tuple[int, int, int, int]: ...
    def save(self, path): ...
    def load(self, path): ...

coord_manager = CoordinateManager()  # глобальный синглтон
```

**Замена в crypt_hunter.py:**
```python
# было:
from window_scaler import scale_coord, scale_region
# стало:
from coord_manager import coord_manager
scale_coord  = coord_manager.to_screen
scale_region = coord_manager.to_region
```

---

## Профили

3 файла в папке `profiles/`:
- `profile_client.json`
- `profile_chrome.json`
- `profile_firefox.json`

Структура JSON:
```json
{
  "name": "Chrome",
  "point_a": [102, 971],
  "point_b": [1543, 87]
}
```

---

## GUI Лупа (calibration_ui.py)

**Механика (Вариант C: клик + ручной ввод):**

1. Скриншот всего экрана через MSS
2. Tkinter-окно:
   - Зум-виджет 600% вокруг текущих X/Y (Canvas с увеличенным фрагментом)
   - Поля ввода X / Y (обновляются при клике в лупе, редактируемые вручную)
   - Красная точка 16×16 на реальном экране (`Toplevel`, `overrideredirect=True`)
   - Кнопка «Зафиксировать»
3. Клик в лупе → пересчёт в реальные координаты → обновление X/Y + красная точка
4. Ввод числа → красная точка двигается
5. «Зафиксировать» → Point A сохранён → то же самое для Point B
6. После обеих точек → `coord_manager.calibrate(a, b)`

---

## Вкладка «Калибровка» в main.py

- Dropdown: Client / Chrome / Firefox
- Кнопка «Загрузить профиль»
- Кнопка «Калибровать» → запускает calibration_ui.py
- Кнопка «Сохранить профиль»
- Статус-строка: `scale_x=0.83  scale_y=0.79  anchor=(102, 971)`
- Автозагрузка последнего профиля при старте

---

## Тесты

- `test_coord_manager.py` — unit-тесты `calibrate()`, `to_screen()`, `to_region()`, save/load
- Тест: эталонные точки A и B при calibrate с ref-значениями → to_screen возвращает ref-значения
- Тест: scale при 1920×1080 fullscreen → scale_x=1.0, scale_y=1.0

---

## Схема зависимостей

```
main.py
  └── calibration_ui.py → coord_manager.py
crypt_hunter.py → coord_manager.py
engine.py → navigator.py (без изменений)
```

`window_scaler.py` — удаляется после миграции всех импортов.
