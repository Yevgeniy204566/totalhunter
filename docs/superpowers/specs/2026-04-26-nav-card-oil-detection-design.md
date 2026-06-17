# Design Spec: Nav Card + Oil Detection
**Date**: 2026-04-26  
**Status**: Approved

---

## 1. Биржа — Новая карточка «Навигация»

### Что делаем
Создать новую карточку `nav_main_frame` под `nn_frame` («Нейросеть»), стиль идентичен:
```python
fg_color=MD3["elevated"], corner_radius=12, border_width=1, border_color=MD3["outline"]
```

### Содержимое карточки (3 слайдера)
| Слайдер | Старое место | Изменения |
|---|---|---|
| «Шаг» | nav_frame, вне scroll | Переезжает в карточку; label «Шаг джойстика» → «Шаг»; `to=17` → `to=20`, `number_of_steps=10` |
| «Скорость (сек/шаг)» | nav_frame, вне scroll | Переезжает в карточку; без изменений |
| «Глубина нырка» | nav_sliders_frame (scroll) | Вытаскивается в карточку; без изменений |

### Изменения в nav_frame
- Заголовок: «Навигация (мини-карта)» → «Дополнительно»
- Убрать из него: Шаг, Скорость, Глубина нырка (переехали)
- Оставить: Center X/Y entries + nav_toggle, и scrollable frame с 5 слайдерами:
  - Граница океан/суша
  - Мин. размер водоёма
  - Коэф. диагонали возврата
  - Конус детекции берега
  - Память следов (TTL)

### Память следов — расширение
- `from_=60, to=1200, number_of_steps=19` (шаг 60 сек)
- Display: `f"{v // 60} мин"` если `v >= 60`, иначе `f"{v} с"`
- Default отображение: «2 мин» (120s)

### Сохранение/загрузка
- `_save_settings()` / `_load_settings()` — без изменений (ключи те же, просто слайдеры переехали)
- `toggle_bot()` читает те же переменные — без изменений

---

## 2. Склепы — Детект диалога масла

### Проблема
`_send_captain()` кликает «Исследовать» и всегда возвращает `True`. Если масло закончилось — игра показывает диалог пополнения (зелёная/синяя кнопка), а бот продолжает кликать вслепую.

### Решение: `_check_oil_dialog() -> bool`
После клика «Исследовать» ждём 1.5 с, затем:
1. Screenshot центрального региона (raw 1920×1080 ref): `x=580, y=280, w=550, h=420`
2. Convert to HSV
3. Ищем **зелёную кнопку** (масло на складе): `H∈[35,85], S∈[80,255], V∈[80,220]`
4. ИЛИ **синюю кнопку** (купить): `H∈[100,130], S∈[80,255], V∈[80,230]`
5. Если `pixel_count > 200` → oil dialog detected → вернуть `True`

Регион масштабируется через `scale_region()` если `_VISUAL_NAV_AVAILABLE`.

### Изменение в `_send_captain()`
```python
def _send_captain(self, crypt_type: str) -> bool:
    self._random_pause()
    self._status("Нажимаю «Исследовать»...")
    sc = scale_dialog(*CRYPT_STUDY_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_STUDY_BTN
    self._click(*sc, raw=True)
    self._interruptible_sleep(1.5)          # ← NEW: ждём диалог масла
    if self._check_oil_dialog():            # ← NEW
        self._emergency_stop("OIL_LOW: масло закончилось")
        return False
    self._random_pause(0.3, 0.8)           # остаток паузы
    return True
```

### GUI (уже готово)
`on_crypt_stop()` в main.py уже обрабатывает `OIL_LOW:` — показывает «Добавь масла» оранжевым.

---

## 3. Не меняем
- `toggle_bot()` в main.py — аргументы без изменений
- `engine.py` / `navigator.py` / `coord_manager.py` — не трогаем
- Логика footprint в navigator.py — не трогаем (TTL управляется через GUI)

---

## Файлы для изменений
1. `main.py` — новая карточка, перемещение 3 слайдеров, TTL up to 1200
2. `crypt_hunter.py` — `_check_oil_dialog()` + изменение `_send_captain()`
