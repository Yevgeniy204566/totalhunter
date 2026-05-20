# ХАНГОФ #62 — Total Hunter
### Дата: 2026-05-20 | ROY фиксы + биржа линейный workflow → v1.4.1

---

## ✅ ЧТО БЫЛО СДЕЛАНО ЗА СЕССИЮ

### Фикс 1 — ROY event gate (engine.py)
- `self.event_active` (GUI-флаг) заменён на `_is_trade_routes_active()` — функция вычисляет активность ивента напрямую каждые 30 сек
- Причина бага: флаг устанавливался только из GUI-тика (раз в 60с), при старте движка = False → скан не засчитывался

### Фикс 2+3 — Ползунки beacon-режима (engine.py)
- `smooth_alpha` и `return_delta_px` не передавались в `CoastalSnakeNavigatorBeacon` и `PacmanEngine` при `use_beacon=True`
- Добавлены в оба конструктора beacon-ветки

### Фикс 4+5+6 — Линейный workflow после нахождения биржи (navigator.py + engine.py)
- ROY `_roy_on_found()` стал синхронным (было: background thread, OCR читал пока навигация шла)
- `time.sleep(10)` после OCR — бот стоит на месте
- `_trigger_yolo_block(20)` перенесён ПОСЛЕ sleep(10) — запускается пока бот уходит
- `loop_start = time.time()` сброс после возврата из `_exchange_detected()` — первый шаг нормальной скорости

### Итог
- Версия: 1.4.0 → **1.4.1**
- Релиз: GitHub v1.4.1, GCP API обновлён

---

## ТЕКУЩЕЕ СОСТОЯНИЕ ПРОДУКТА

| Что | Версия/Статус |
|---|---|
| Сервер /version/latest | **1.4.1** ✅ |
| Код в репо | **1.4.1** ✅ |
| GitHub Latest Release | v1.4.1 ✅ |
| ZIP структура | Плоская (exe в корне) ✅ |
| Сайт total-hunter.com | ✅ последняя версия |
| GCP бэкенд | ✅ работает (серверный код не менялся) |

---

## ЧТО ОСТАЛОСЬ / СЛЕДУЮЩИЕ ЗАДАЧИ

- Протестировать ROY в живую: нашёл биржу → координаты в пул → баланс начисляется
- Пул заполняется только когда биржи реально найдены — ивент продолжается до 21.05.2026 20:00 Киев
- Ползунок «Живость хода» — проверить в beacon-режиме после фикса

---

---

## ✅ ЧТО БЫЛО СДЕЛАНО ЗА СЕССИЮ

### Проблема
Хангоф #60 оставил нерешённой стратегию выкатки v1.3.4 — сервер стоял на 1.3.2 из-за петли обновлений.

### Корень проблемы (диагностика)
- v1.3.2 и ранее: ZIP плоский (`TotalHunter.exe` в корне), xcopy = `extract_dir\*` → всё работало
- v1.3.3: ZIP стал вложенным (`TotalHunter/TotalHunter.exe`), xcopy остался `extract_dir\*` → копировал папку → нестинг → петля
- v1.3.4: xcopy исправлен на `extract_dir\TotalHunter\*` — верно для вложенного ZIP, но недостижимо через автообновление
- Сервер откатан на 1.3.2 → все пользователи на 1.3.2

### Решение (элегантный хак от Gemini)
Вернуть ZIP к плоскому формату для v1.4.0:
- Старый xcopy у клиентов 1.3.2: `extract_dir\*` → плоский ZIP → копирует файлы напрямую → ✅ работает
- Новый updater v1.4.0 тоже использует `extract_dir\*` (плоский стандарт навсегда)

### Что сделано
- `updater.py` строка 70: `extract_dir\TotalHunter\*` → `extract_dir\*` ✅
- `version.py`: `1.3.4` → `1.4.0` ✅
- Сборка: 10 модулей Nuitka + PyInstaller ✅
- ZIP: плоский 391 MB, `TotalHunter.exe` в корне ✅
- GitHub Release v1.4.0 + ZIP загружен ✅
- Сервер: `/version/latest` → `1.4.0` ✅
- `ANTI-PATTERNS.md`: исправлена неверная запись AP-UPDATER ✅

---

## ТЕКУЩЕЕ СОСТОЯНИЕ ПРОДУКТА

| Что | Версия/Статус |
|---|---|
| Сервер /version/latest | **1.4.0** ✅ |
| Код в репо | **1.4.0** ✅ |
| GitHub Latest Release | v1.4.0 ✅ |
| ZIP структура | Плоская (exe в корне) ✅ |
| Сайт total-hunter.com | ✅ последняя версия |
| GCP бэкенд | ✅ работает (серверный код не менялся) |

---

## GCP override.conf — текущее содержимое

```
[Service]
Environment="NOWPAYMENTS_API_KEY=XCBYC3W-2YXM19X-HMPNC1D-CG43J28"
Environment="NOWPAYMENTS_IPN_SECRET=qh32j9yylaWieAlRrbSnUDTqNIGYuldG"
Environment="ADMIN_TOKEN=0fb55141605437f975daa95a44b99fb7498faf0cee8ba0675999af6e21b8e5ab"
Environment="GOOGLE_CLIENT_SECRET=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"
[Service]
Environment="TELEGRAM_DEBUG_TOKEN=8872506039:AAEA8SCBFPVffh8FVLEYNfHuYHuo_Gn3Lr0"
Environment="TELEGRAM_DEBUG_CHAT_ID=578374730"
Environment="JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2"
Environment="OWNER_EMAIL=ievgeniy2011@gmail.com"
```

---

## НЕРУШИМЫЙ СТАНДАРТ UPDATER (v1.4.0+)

```
ZIP:   7z a -tzip TotalHunter.zip "dist/TotalHunter/*"     ← плоский
xcopy: xcopy /s /y /e "{extract_dir}\*" "{exe_dir}\"        ← плоский
```

Менять одно без другого = петля. Проверка: `7z l TotalHunter.zip | grep TotalHunter.exe` должно показать путь без вложенной папки.

---

## ЧТО ОСТАЛОСЬ (следующая сессия)

### 🟡 ТЕХНИЧЕСКИЙ ДОЛГ (из хангофа #60, не трогали)
- server/payments.py: race condition в webhook (with_for_update())
- crypt_hunter.py: _detect_fail_streak без максимума → возможный бесконечный цикл
- engine.py + crypt_hunter.py: YOLO try-except при загрузке моделей
- updater.py: disk full не обрабатывается
- Main old Packmen.py: убрать из репо

### 🟢 ПРОДУКТОВЫЕ ИДЕИ
- Живой тест РОЙ v1.3.1 (ивент «Торговые Пути» — якорь 20.05.2026 20:00 Киев, цикл 5 дней)
- Fortune Wheel: PNG-текстуры в web/public/img/wheel/ (Unsplash CORS блочит)
- Adsterra реклама: нативные баннеры, позиционировать как "Game Tools"
