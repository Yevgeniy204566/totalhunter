# Сундуки — конвейер распознавания имён игроков: портативность, бережный clean_name, буквальное чтение диакритики

Дата: 2026-06-22

## Контекст

Владелец проверил выгрузку сундуков клана 229/BERS и нашёл реально существующего игрока с
стилизованным именем («Marisha»-тип с диакритикой), которое распознаётся либо разнесённым по
буквам через пробел («M A R I S H A»), либо вообще теряется. После брейнсторма с Gemini
зафиксирован следующий объём работ (Gemini явно отбросил гипотезы про утечку лейбла «От:» и
чистый OCR-мусор — калибровка зон `SENDER_REF_RECT`/`SOURCE_REF_RECT` не трогается, эти зоны
**не входят** в эту правку):

1. Портативность Tesseract — убрать хардкод дев-пути.
2. Бережный `clean_name()` — не пожирать буквы разнесённых пробелами имён.
3. Буквальное посимвольное чтение для имени игрока (отключить словари + расширенные языки).

Технически проверено мной перед написанием спеки (живые тесты на этой машине):
- `chest_reader.py` и `navigator.py` хардкодят `C:\Program Files\Tesseract-OCR\tesseract.exe`
  (путь дев-машины). `roy/exchange_reader.py` уже делает это правильно — `frozen`→
  `tesseract_bin/tesseract.exe` рядом с EXE, `dev`→автопоиск по PATH/стандартным путям.
- Файл `script/Latin.traineddata` (полный охват всех латинских языков мира — диакритика
  скандинавских/польских/румынских и т.д. имён разом) скачан и проверен живым прогоном:
  `tesseract.exe --tessdata-dir tesseract_bin/tessdata --list-langs` → `script\Latin` распознаётся
  как валидный язык; тестовый OCR с `-l eng+rus+script/Latin --psm 7 -c load_system_dawg=0 -c
  load_freq_dawg=0` корректно прочитал синтетическое изображение со словом "Marisha".
- Размер файла: **89 384 811 байт (~89 МБ)** — решение принято осознанно владельцем после того,
  как первая оценка (15-20 МБ) оказалась ошибочной; цена признана приемлемой для десктопного
  приложения, устанавливаемого один раз.
- `rus.traineddata` (3 861 738 байт, ~3.9 МБ) уже использовался в рантайме (`lang='rus+eng'`), но
  **никогда не входил в `tesseract_bin/`** — то есть на реальной клиентской сборке (не дев-машине)
  русский язык OCR не работал вовсе для модулей, использующих хардкод-путь (см. пункт выше).

## A. Портативность Tesseract — общий модуль `tesseract_setup.py`

**Новый файл:** `tesseract_setup.py` (корень проекта, рядом с `chest_reader.py`/`navigator.py`).

Логика 1:1 скопирована из уже работающего `roy/exchange_reader.py::_find_tesseract()`, выделена в
переиспользуемый модуль, чтобы не плодить третью копию хардкода:

```python
"""tesseract_setup.py — резолвит путь к tesseract.exe: портативный tesseract_bin/ рядом
с EXE в собранном релизе, системный PATH/стандартные пути установки в dev-режиме.

Единый источник истины — до этого файла chest_reader.py и navigator.py хардкодили
дев-путь напрямую, а roy/exchange_reader.py независимо реализовывал то же самое —
рассинхронизация привела к тому, что хардкод-копии никогда не подхватывали портативный
tesseract_bin на клиентских сборках.
"""
import os
import shutil
import sys


def find_tesseract():
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(os.path.dirname(sys.executable), "tesseract_bin", "tesseract.exe")
        return bundled if os.path.isfile(bundled) else None

    found = shutil.which("tesseract")
    if found:
        return found
    for path in [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]:
        if os.path.isfile(path):
            return path
    return None


def configure_pytesseract(pytesseract_module, log=print):
    path = find_tesseract()
    if path:
        pytesseract_module.pytesseract.tesseract_cmd = path
        return True
    if getattr(sys, 'frozen', False):
        log("КРИТИЧЕСКАЯ ОШИБКА: tesseract_bin не найден рядом с TotalHunter.exe. "
            "Проверьте целостность сборки — папка tesseract_bin должна быть рядом с EXE.")
    else:
        log("КРИТИЧЕСКАЯ ОШИБКА: Tesseract OCR не найден на ПК. "
            "Установите Tesseract для работы бота. "
            "Скачайте: https://github.com/UB-Mannheim/tesseract/wiki")
    return False
```

**`chest_reader.py`** и **`navigator.py`**: заменить строку
`pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'` на:

```python
from tesseract_setup import configure_pytesseract
configure_pytesseract(pytesseract)
```

**`roy/exchange_reader.py` не трогаем** — он уже работает правильно, живёт в отдельном пакете
`roy/`, рефакторинг туда не входит в эту правку (не создаём риск для уже рабочего модуля без
прямой необходимости).

## B. `clean_name()` — бережная очистка, без пожирания пробельных имён

**Файл:** `chest_reader.py:100-112`.

**Текущая проблема:** строка `re.sub(r'\s+\S{1,3}$', '', text)` плюс цикл
`while True: re.sub(r'\s+(?:\d{1,3}|\S{1})$', ...)` были задуманы для отрезания мусорных
хвостов (цифры уровня силы, обрывок значка) — но `\S{1}`-ветка не отличает «мусорная
одиночная буква» от «настоящая буква разнесённого пробелами стилизованного имени», и
рекурсивно съедает имя целиком вплоть до одного символа («M A R I S H A» → «M»).

**Новая логика — отрезаем только то, в чём действительно нет сомнений (цифровые хвосты),
буквы никогда не трогаем:**

```python
def clean_name(text):
    """Strip OCR artifacts from a player name. Only strips a leading [clan tag]
    prefix and trailing digit groups (power-level/tag noise) — never strips trailing
    letters, since stylized space-separated names (e.g. "M A R I S H A") must survive
    intact rather than being eaten down to a single character."""
    text = re.sub(r'^\[.*?\]\s*', '', text)
    text = re.sub(r'(?:\s+\d{1,3})+$', '', text)
    text = re.sub(r'[^\w]+$', '', text, flags=re.UNICODE)
    return text.strip()
```

Поведение: `"PlayerName 123"` → `"PlayerName"` (как раньше). `"Tess'"` → `"Tess"` (как раньше,
существующий тест `test_read_sender_name_applies_clean_name_artifact_stripping` не меняется).
`"M A R I S H A"` → `"M A R I S H A"` (раньше схлопывалось до `"M"` — это и есть фикс).

**Вне рамок:** `tournament_reader.py` имеет собственную идентичную копию `clean_name` — не
трогаем (отдельный, не собираемый в релиз CLI-инструмент, явно вне рамок по решению из чата).

## C. Буквальное чтение диакритики — только для имени игрока

**Файл:** `chest_reader.py`.

`ocr_text()` (строки 94-97) получает новый необязательный параметр `extra_config`:

```python
def ocr_text(roi, psm=7, lang='rus+eng', extra_config=''):
    processed = preprocess_for_ocr(roi)
    config = f'--psm {psm} {extra_config}'.strip()
    return pytesseract.image_to_string(processed, config=config, lang=lang, timeout=5).strip()
```

`read_fixed_field()` (строки 115-121) прокидывает `lang`/`extra_config` дальше в `ocr_text`:

```python
def read_fixed_field(frame, ref_rect, offset_name=None, lang='rus+eng', extra_config=''):
    x, y, w, h = coord_manager.to_region_dialog(*ref_rect)
    if offset_name is not None:
        dx, dy = coord_manager.get_ui_offset(offset_name)
        x, y = x + dx, y + dy
    roi = frame[y:y + h, x:x + w]
    return clean_name(ocr_text(roi, lang=lang, extra_config=extra_config))
```

Новые константы и обновлённый `read_sender_name`:

```python
# Имя игрока: стилизованное/непредсказуемое — словари только мешают (заставляют Tesseract
# "подгонять" незнакомые формы под known dictionary word, разбивая имя по буквам). Полное
# отключение DAWG + широкий охват латиницы script/Latin читает диакритику буквально.
SENDER_OCR_LANG = 'rus+eng+script/Latin'
SENDER_OCR_CONFIG = '-c load_system_dawg=0 -c load_freq_dawg=0'


def read_sender_name(frame):
    return read_fixed_field(frame, SENDER_REF_RECT, "chest_sender",
                            lang=SENDER_OCR_LANG, extra_config=SENDER_OCR_CONFIG)
```

`read_chest_type()` **не меняется** — тип сундука это фиксированная игровая фраза
(«Эпический отряд нежити»), словари там помогают распознаванию целых слов, отключать их не нужно
(решено в чате явно).

## D. Дистрибутив `tesseract_bin` — новый состав

**Добавить в `tesseract_bin/tessdata/`:**
- `rus.traineddata` (3 861 738 байт) — скопирован из системной установки Tesseract на машине
  разработчика (`C:\Program Files\Tesseract-OCR\tessdata\rus.traineddata`), идентичен тому, что
  уже используется в рантайме (`lang='rus+eng'`), просто никогда не был частью дистрибутива.
- `tessdata/script/Latin.traineddata` (89 384 811 байт) — скачан из
  `https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/script/Latin.traineddata`,
  кладётся в подпапку `script/` (обязательно — Tesseract резолвит язык `script/Latin` именно по
  этому пути), проверен живым `--list-langs` + тестовым OCR-прогоном (см. «Контекст» выше).

**Обновить `CLAUDE.md`** (раздел 0, чек-лист перед сборкой) — заменить строку
`Эталонный состав tesseract_bin: 56 DLL + tessdata/eng.traineddata = 72 МБ` на:

```
# 3. Эталонный состав tesseract_bin: 56 DLL + tessdata/{eng,rus}.traineddata +
#    tessdata/script/Latin.traineddata = ~165 МБ
# Источник: C:\Program Files\Tesseract-OCR\ (все *.dll + eng/rus.traineddata)
#           + https://github.com/tesseract-ocr/tessdata_fast (script/Latin.traineddata)
```

`build_release.py` не требует изменений — он копирует `tesseract_bin/` целиком рекурсивно
(включая подпапки), новый файл в `tessdata/script/` подхватится автоматически.

## Тестирование

**TDD, `test_chest_reader.py`:**
1. Новые юнит-тесты `clean_name()` (чистая функция, без OCR-зависимости):
   - `clean_name("M A R I S H A") == "M A R I S H A"` (главный регресс-тест бага).
   - `clean_name("PlayerName 123") == "PlayerName"` (цифровой хвост всё ещё режется).
   - `clean_name("Tess'") == "Tess"` (существующее поведение не ломается).
   - `clean_name("[ABC] Niduel") == "Niduel"` (тег клана всё ещё режется).
2. Обновить/добавить тест на `read_sender_name`, проверяющий что `ocr_text` вызывается с
   `lang=SENDER_OCR_LANG, extra_config=SENDER_OCR_CONFIG` (через `monkeypatch` captured kwargs,
   как уже делают существующие тесты в файле).
3. Новый тест на `read_chest_type`, проверяющий что `lang`/`extra_config` остаются дефолтными
   (`'rus+eng'`, `''`) — явно фиксирует решение «только имя игрока, не тип сундука».
4. Прогнать **весь** `test_chest_reader.py`, включая существующий живой интеграционный
   `test_read_top_row_on_fixture` (реальный OCR на `Сундуки_1.png`, ожидает `"Gray Cardinal"`) —
   убедиться, что новые lang/config не сломали распознавание простого ASCII-имени.
5. Новый модуль `tesseract_setup.py` — юнит-тесты на `find_tesseract()` с `monkeypatch` на
   `sys.frozen`/`os.path.isfile`/`shutil.which` (без реального обращения к диску/Tesseract).

## Вне рамок

- Утечка лейбла «От:» и чистый OCR-мусор (а/еее/м/о) — отброшено явно, зоны кропа калиброваны и
  не трогаются.
- `tournament_reader.py` — собственная копия `clean_name`, не используется в релизе, не трогается.
- `roy/exchange_reader.py` — уже работает правильно, не рефакторится.
- Изменение `read_chest_type()` — словари там остаются включёнными.
