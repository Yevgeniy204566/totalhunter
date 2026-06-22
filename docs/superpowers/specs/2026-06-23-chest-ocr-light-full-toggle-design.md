# Сундуки — тумблер Light/Full для распознавания имени игрока

Дата: 2026-06-23

## Контекст

После расширения OCR имени игрока до 19 языков (Cyrillic, Arabic, Japanese, Chinese×2, Korean,
вне рамок этой спеки — уже реализовано, не собрано в релиз) выяснилось живым замером, что полный
набор языков заметно медленнее узкого:

- Старый набор (`rus+eng+script/Latin`): **~0.39 сек** на вызов (замерено на реальном размере поля
  имени `SENDER_REF_RECT` = 361×24px, 5 прогонов).
- Новый набор (8 языков): **~1.0 сек** на вызов — **в 2.5 раза медленнее**, +0.6 сек на каждый
  прочитанный сундук.

При типичной выгрузке (1734 сундука за раз, реальные данные клана 229/BERS) это +17 минут к
сессии сбора. Большинству кланов (латиница/кириллица) полный набор не нужен — решено дать
владельцу/админу клана выбор через тумблер в интерфейсе.

## Архитектура

**Принцип:** флаг `full_lang: bool` прокидывается явным параметром через всю цепочку вызовов —
от GUI (`main.py`) через `collect_chests()` → `read_top_row()` → `read_sender_name()`. Без
глобальных переменных, по той же схеме, что уже работает для `pause_range` (скорость клика).

### `chest_reader.py`

Текущая константа `SENDER_OCR_LANG` разделяется на две:

```python
LIGHT_SENDER_OCR_LANG = 'rus+eng+script/Latin'
FULL_SENDER_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'
SENDER_OCR_CONFIG = '-c load_system_dawg=0 -c load_freq_dawg=0'  # без изменений


def read_sender_name(frame, full_lang=False):
    lang = FULL_SENDER_OCR_LANG if full_lang else LIGHT_SENDER_OCR_LANG
    return read_fixed_field(frame, SENDER_REF_RECT, "chest_sender",
                            lang=lang, extra_config=SENDER_OCR_CONFIG)


def read_top_row(frame, full_lang=False):
    chest_type = read_chest_type(frame)
    sender = read_sender_name(frame, full_lang=full_lang)
    return chest_type, sender


def collect_chests(stop_flag, on_update=None, db_path=DB_PATH,
                   pause_range=ANTI_DETECT_PAUSE_RANGE, full_lang=False):
    ...
    chest_type, sender = read_top_row(frame, full_lang=full_lang)
    ...
```

(Точные сигнатуры и места вызова — в плане реализации, с учётом текущего кода `collect_chests`.)

`read_chest_type()` не меняется — словари там остаются включёнными, как и раньше.

### `main.py` — вкладка СУНДУКИ

Новый `CTkSwitch` рядом с существующим `chest_speed_slider` (паттерн 1:1 с уже существующим
`self._roy_switch` в вкладке РОЙ):

- Подписи **буквально "Light" / "Full"** — английские слова, не переводятся на 19 языков
  интерфейса бота (решено в чате явно — упрощает поддержку UI, понятно любому админу клана).
- Сохраняется в `gui_config.json["chest_full_lang_ocr"]` (bool), читается при построении вкладки
  (`self._load_gui_config().get("chest_full_lang_ocr", False)`), сохраняется на изменение через
  `self._save_gui_config_key(...)` — тот же паттерн, что у `chest_click_pause`.
- **По умолчанию `False` (Light)** — решено в чате: большинство кланов не нуждаются в полном
  наборе, явный осознанный выбор для тех, кому нужно.
- Значение читается в `toggle_chest_bot()` в момент старта (`full_lang = self.chest_full_lang_switch.get()`)
  и передаётся в `chest_reader.collect_chests(..., full_lang=full_lang)`.

## Тестирование

TDD, `test_chest_reader.py`:
- `read_sender_name(frame, full_lang=False)` использует `LIGHT_SENDER_OCR_LANG`.
- `read_sender_name(frame, full_lang=True)` использует `FULL_SENDER_OCR_LANG`.
- `read_top_row(frame, full_lang=True)` прокидывает флаг в `read_sender_name` (через monkeypatch).
- `collect_chests` прокидывает `full_lang` дальше (через monkeypatch на `read_top_row`).
- Полный прогон файла, включая живой `test_read_top_row_on_fixture` (по умолчанию `full_lang=False`
  → должен использовать `LIGHT_SENDER_OCR_LANG`, как и до этой спеки).

GUI (`main.py`) — без автотестов (как и весь остальной GUI-код проекта), ручная проверка владельцем
после сборки: переключение Light/Full сохраняется между перезапусками бота.

## Вне рамок

- Изменение самого набора языков (`FULL_SENDER_OCR_LANG`, `LIGHT_SENDER_OCR_LANG` значения) —
  взяты как есть из уже реализованной (но не выпущенной) 19-языковой спеки.
- `read_chest_type()` — не меняется.
- Перевод подписей "Light"/"Full" — решено не переводить, английские слова остаются как есть на
  всех языках интерфейса.
