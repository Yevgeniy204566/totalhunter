# Сундуки — полное покрытие 19 языков игры для OCR имени игрока

Дата: 2026-06-22

## Контекст

После релиза v1.8.2 (портативность Tesseract + безопасный `clean_name` + `script/Latin` для
диакритики) владелец спросил: а распознаются ли азиатские/арабские имена? Ответ — нет, `script/Latin`
покрывает только латиницу. После обсуждения объёма (полный Unicode мира = +219 МБ против покрытия
только реальных языков самой игры = +39 МБ) выбран второй вариант: покрыть ровно те 19 языков,
которые уже поддерживает интерфейс бота (`main.py::LANGS`) — это и есть реальный список языков
аудитории Total Battle.

## Языки → файлы

| Языки из `LANGS` | Скрипт | Файл | Размер |
|---|---|---|---|
| RU, UK | Кириллица | `script/Cyrillic.traineddata` | 29 252 466 байт |
| EN, DE, ES, FR, IT, NL, NO, PL, PT, SV, TR, ID | Латиница (уже есть) | `script/Latin.traineddata` | — (уже в v1.8.2) |
| AR | Арабский | `ara.traineddata` | 1 432 056 байт |
| JA | Японский | `jpn.traineddata` | 2 471 260 байт |
| ZH | Китайский (упрощённый) | `chi_sim.traineddata` | 2 469 156 байт |
| ZH_TW | Китайский (традиционный) | `chi_tra.traineddata` | 2 366 642 байт |
| KO | Корейский | `kor.traineddata` | 1 677 415 байт |

Все размеры подтверждены живым скачиванием (не оценка). Итого новых данных: ~39 МБ. Архив вырастет
с 406 МБ (v1.8.2) до ~445 МБ.

**`rus.traineddata` удаляется** — `script/Cyrillic` покрывает русский как подмножество (плюс
украинский, которого `rus` не покрывал вовсе), хранить оба избыточно.

## Техническая проверка (живая, не предположение)

```
tesseract --tessdata-dir tesseract_bin/tessdata --list-langs
→ ara, chi_sim, chi_tra, eng, jpn, kor, script\Cyrillic, script\Latin (8 языков)
```

Тестовый OCR с полной строкой `-l "eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor"`
корректно прочитал синтетическое изображение со словом "Marisha", время выполнения **1.1 секунды**
(в пределах текущего `timeout=5` в `ocr_text()`, вызывается один раз на сундук, не в горячем цикле
кадров — допустимо).

## Изменение кода

**Файл:** `chest_reader.py`, константа `SENDER_OCR_LANG` (введена в v1.8.2).

Было:
```python
SENDER_OCR_LANG = 'rus+eng+script/Latin'
```

Станет:
```python
SENDER_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'
```

`SENDER_OCR_CONFIG` (отключённые словари) не меняется — те же причины актуальны для всех языков.

`read_chest_type()` не меняется (решение из прошлой спеки подтверждено — тип сундука это
фиксированная игровая фраза на языке клиента, не нуждается в этом наборе).

## Дистрибутив `tesseract_bin`

- Удалить: `tesseract_bin/tessdata/rus.traineddata`
- Добавить: `tesseract_bin/tessdata/script/Cyrillic.traineddata`,
  `tesseract_bin/tessdata/ara.traineddata`, `tesseract_bin/tessdata/jpn.traineddata`,
  `tesseract_bin/tessdata/chi_sim.traineddata`, `tesseract_bin/tessdata/chi_tra.traineddata`,
  `tesseract_bin/tessdata/kor.traineddata`
- Обновить `CLAUDE.md` чек-лист (эталонный состав tesseract_bin) — новый список файлов и размер.
- Те же файлы зеркалируются в системный Tesseract на деве (`C:\Program Files\Tesseract-OCR\tessdata\`)
  для живого теста `test_read_top_row_on_fixture`, как и в прошлый раз.

## Тестирование

- Обновить существующий тест на `read_sender_name` (из v1.8.2,
  `test_read_sender_name_uses_literal_diacritic_config`) — новое ожидаемое значение `lang`.
- Полный прогон `test_chest_reader.py`, включая живой `test_read_top_row_on_fixture`.

## Вне рамок

- Остальные 25 скриптов Tesseract (Tibetan, Khmer, Cherokee, Canadian_Aboriginal и т.д.) — явно
  отклонено владельцем, в Total Battle не встречаются.
- Любые изменения `read_chest_type()`.
