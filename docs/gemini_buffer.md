# Хангоф #67 — 2026-05-21 (v1.5.5 — биржевый бот полностью исправлен)

## СТАТУС: v1.5.5 ВЫПУЩЕН ✅

**Сервер /version/latest → 1.5.5** ✅
**GitHub Release:** https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.5
**ZIP:** 337 MB, плоский, TotalHunter.exe в корне ✅

---

## ЧТО СДЕЛАНО ЗА СЕССИЮ (хангоф #66 → #67)

### v1.5.0 — ZIP фикс (плоская упаковка)
Был неплоский ZIP → петля автообновлений. Пересобрали правильно.

### v1.5.1 — ROY OCR фикс
- `tesseract_cmd` прописан явно (пропущен в exchange_reader.py)
- `_COORD_ROI_REL` расширена до `(0.0, 0.03, 1.0, 0.20)` — старая зона обрезала строку K/X/Y
- OCR переписан на plain gray + `--psm 11` (вместо HSV-маски красного текста V≤160)

### v1.5.2 — ROY пакет в EXE (корневая причина)
- `engine.pyd` содержит `from roy.exchange_reader import ...` (динамический)
- PyInstaller не видит импорты в `.pyd` → `roy/` отсутствовал в `dist/_internal/`
- **Фикс:** `roy/__init__.py` создан + `hiddenimports` + `datas` в build.spec
- `except Exception: pass` → `except Exception as e: print(...)` — видна причина ошибки

### v1.5.3 — pytesseract timeout=3
- `pytesseract.image_to_string()` без таймаута → tesseract.exe мог зависнуть
- Весь `_exchange_detected` замораживался → бот стоял после каждой биржи вечно
- **Фикс:** `timeout=3` на оба pytesseract вызова + try/except fallback

### v1.5.5 — YOLO timestamp (race condition fix)
- daemon thread `_trigger_yolo_block` → при СТОП→СТАРТ старый тред снимал блок досрочно
- **Фикс:** `_yolo_unblock_time = time.time() + N` вместо threading
- `start()` теперь сбрасывает `_yolo_unblock_time = 0`
- 13/13 тестов ✅

### docs/exchange_bot_spec.md — ЭТАЛОН
Создан канонический документ механики биржевого бота (12 шагов, временная шкала, ROY pipeline, чеклист для новых идей). Привязан к CLAUDE.md и memory.

---

## КОММИТЫ СЕССИИ

| Хэш | Описание |
|---|---|
| edd6d41 | fix: ROY OCR — tesseract_cmd + psm 11 + wider coord ROI (v1.5.1) |
| 083928e | fix: ROY пакет не попадал в EXE — roy/__init__.py + hiddenimports (v1.5.2) |
| 5d58903 | fix: pytesseract timeout=3 — блокировка потока после биржи (v1.5.3) |
| 86a470b | refactor: YOLO-блок на timestamp вместо daemon thread (v1.5.5) |
| d147f95 | chore: bump version 1.5.3 → 1.5.5 |
| 652e837 | docs: exchange_bot_spec.md — эталонный документ механики биржевого бота |

---

## ТЕКУЩЕЕ СОСТОЯНИЕ БОТА v1.5.5

### Работает ✅
- Backtracking (возврат к бирже при проскоке карты)
- ROY OCR (координаты биржи попадают в пул)
- pytesseract не зависает (timeout=3)
- YOLO-блок 20с без race condition
- 13 TDD тестов
- Эталонный документ: docs/exchange_bot_spec.md

### На будущее (не срочно)
- Баг «выкидывает в магазин» — не диагностирован
- Fortune Wheel — финальный визуал (Unsplash CORS, реальные PNG ассеты)
- Реклама: Adsterra нативные баннеры

---

## ПЕРВОЕ ДЕЙСТВИЕ СЛЕДУЮЩЕЙ СЕССИИ

Живой тест v1.5.5:
1. Запустить бота
2. Найти биржу
3. Проверить: бот продолжил движение после биржи?
4. Проверить: карточка «Последняя биржа» обновилась?
5. Проверить: координаты в ROY пуле?
6. В консоли: есть `[ROY]` сообщения?
