# Gemini Buffer — Total Hunter
**Дата:** 2026-05-19 | **Версия:** 1.3.1 | **Хангоф #57**

---

## ✅ Сделано в сессии 2026-05-19

### v1.3.1 — выпущен, задеплоен, доступен пользователям

**CryptHunter — фикс редких склепов:**
- `crypt_hunter.py`: swing1 теперь применяется к кнопке «Открыть» редких склепов (R_1, R_2) — как и к кнопке «Исследовать». Ранее swing1 игнорировался для этого клика.

**ROY — event gate + AFK защита:**
- `engine.py`: добавлен флаг `event_active` в `HuntEngine`. `_start_roy_scan()` полностью переписан: два условия для засчитывания скана — (1) ивент активен, (2) миникарта изменилась ≥15% за 30 сек.
- `main.py`: `_update_trade_routes_labels()` обновляет `engine.event_active` каждую минуту.
- Результат: сканирование засчитывается СТРОГО во время ивента «Торговые Пути» (якорь 20.05.2026 20:00 Киев, цикл 5 дней, 24ч).

**ROY — звук новых координат:**
- `main.py`: `_roy_pool_known_ids` (set кортежей kingdom/x/y). При каждом обновлении пула: если появились новые ID → играет звук биржи. Инициализируется в `setup_roy_tab()`.

**Debug Reporter — Telegram скрины:**
- `debug_reporter.py` (новый, компилируется Nuitka): fire-and-forget отправка FIND+DIALOG скринов на сервер → Telegram. Без сохранения на диск.
- `server/debug_router.py` (новый): `POST /api/debug/upload-shot` — принимает UploadFile + hwid + shot_type + conf, пересылает в Telegram Bot API в памяти.
- Telegram бот: `@total_hunter_debug_bot` (token+chat_id в GCP override.conf).
- На FIND-скрине: зелёный bbox + подпись `CONF: XX%` над прямоугольником.
- Подпись в Telegram: HWID | Тип | 🎯 Точность | Время (Киев).
- `navigator.py`: `_exchange_detected(box, frame=None)` — принимает frame, извлекает `box.conf[0]`, вызывает `report_find()` и `report_dialog()`.
- `server/requirements.txt`: добавлены `python-multipart==0.0.20` и `requests==2.32.3`.

**Гайд сайта:**
- `web/src/guide_content.js` + `guide_content.en.js`: новый раздел `roy` с TOC-записью «Система РОЙ 🐝» / «SWARM System 🐝».
- `web/src/pages/GuidePage.jsx`: рендер ROY секции (механика баланса, event gate, AFK защита, 4 шага использования).
- Задеплоено на Vercel → total-hunter.com.

**Инфраструктура:**
- `python-multipart` установлен на GCP venv.
- GCP рестарт выполнен, сервер активен.
- v1.3.1 на GitHub Releases, ZIP 391 МБ загружен вручную.
- `/version/latest` → 1.3.1.
- Telegram тест пройден: сообщение доставлено @Vusotskiy (chat_id=578374730).

---

## 🔴 Что осталось (приоритет)

### 1. 🎮 Живой тест v1.3.1 во время ивента
- Запустить бота во время «Торговых Путей» (следующий: 20.05.2026 20:00 Киев)
- Проверить: event_active флаг переключается, scan() засчитывается, AFK защита срабатывает
- Проверить: debug скрины приходят в Telegram при находке биржи

### 2. 🎰 Fortune Wheel — финализация визуала
- Unsplash CORS — текстуры не грузятся. Решение: локальные PNG в `web/public/img/wheel/`
- v6 исправил яркость — ждём финальной оценки пользователя

### 3. 📢 Реклама
- Adsterra — нативные баннеры, вывод от $5. Позиционировать как "Game Tools"

### 4. 🔧 Технический долг
- Баг «бот выкидывает в магазин» — не диагностирован, следить

---

## Ключевые параметры инфраструктуры

| Параметр | Значение |
|---|---|
| GCP | total-hunter-backend, us-central1-f, 34.68.86.57:8000 |
| Telegram Debug | @total_hunter_debug_bot, chat_id=578374630 |
| Vercel | prj_mWtcb6hJCkl40YLWheeIlxD5NmXj, team_CkkRPXdwtRtsL9YCk8n4Fzla |
| GitHub | Yevgeniy204566/totalhunter (ПУБЛИЧНЫЙ) |
| Версия | 1.3.1 (выпущена 2026-05-19) |
| Следующая | 1.3.2 (после живого теста РОЯ) |
