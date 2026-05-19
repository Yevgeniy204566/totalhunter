# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-05-19 (сессия: v1.3.1 — ROY event gate + AFK защита + debug Telegram + гайд)

**Frontend URL:** https://total-hunter.com (Vercel + Cloudflare)
**Backend URL:** https://api.total-hunter.com → GCP 34.68.86.57:8000 (Nginx + SSL)

**Frontend Deploy:** forceNew API (НЕ hook — кешируется!) + alias
- Token: в `.claude/settings.local.json` → env.VERCEL_TOKEN (не в репо!)
- команда: `POST /v13/deployments?forceNew=1` с gitSource repoId=1215361801

---

## Статус модулей

| Модуль | Файл | Статус | Дата |
|---|---|---|---|
| **Платежи** | server/payments.py | ✅ NOWPayments (крипто). IPN raw bytes HMAC-SHA512. Работает. | 2026-05-07 |
| **Long-poll синхронизация** | server/vault.py | ✅ GET /vault/sync/{hwid} — мгновенный обмен баланса бот↔сайт | 2026-05-07 |
| **Колесо Фортуны** | server/earn.py + web/EarnPage.jsx | ✅ **Fortuna Royale v7** — SVG-колесо (20 секторов), фото-текстуры (бархат×4 + красное дерево), неоновое кольцо, заклёпки CSS-градиент, LED-chase, указатель с physics, easeOutSmooth 7-8s. Звук: только победный аккорд (тики убраны). Лимит 5/день, безлимит для owner (ievgeniy2011@gmail.com). Кнопка +5 ведёт на /dashboard/earn. Призы: 5◆(78%) 7◆(12%) 15◆(6%) 30◆(3%) 50◆(1%). | 2026-05-18 |
| **GUI main.py — навигация** | main.py | ✅ Порядок вкладок: СКЛЕПЫ→БИРЖИ→РОЙ→РЕФЕРАЛЫ. Таймер «Торговые Пути» в БИРЖИ и РОЙ (якорь 20.05.2026 20:00 Киев, цикл 5 дней, 24ч). Кнопки СТАРТ/СТОП в вкладке РОЙ (дублируют БИРЖИ). Переводы на 19 языков. | 2026-05-18 |
| **Рекламные слоты** | web/AdSlot.jsx | ⛔ PopAds убран (pop-under — не подходит). Ждём сеть с баннерами (BitMedia и др. — высокий порог вывода). | 2026-05-15 |
| **Система РОЙ** | roy/ + server/roy.py + engine.py | ✅ event_active gate (засчитывается ТОЛЬКО во время Торговых Путей), AFK защита (миникарта ≥15% diff), звук при новых координатах в пуле, Server API 4 эндпоинта, OCR, GUI. | 2026-05-19 |
| **Версия в заголовке** | main.py | ✅ `f"Total Hunter v{VERSION}"` — автоматически обновляется | 2026-05-07 |
| **Версия в админке** | server/admin/index.html | ✅ Колонка "Версия бота" в таблице пользователей | 2026-05-07 |
| **Combo** | combiner.py | ⛔ ЗАМОРОЖЕН | 2026-05-02 |
| **Авто-калибровка** | auto_calibration.py | ✅ 2 этапа, 13 тестов | 2026-05-03 |
| **Движок бирж** | engine.py + navigator.py | ✅ 54 теста, smooth_alpha=0.70. Рефакторинг 16.05.26: один ползунок bot_speed, честный динамический sleep, единый кадр (mss→crop, убран pyautogui.screenshot из hot path) | 2026-05-16 |
| **CryptHunter** | crypt_hunter.py | ✅ Anti-groundhog, конец списка cv2.absdiff, статусы. Swing1 применяется к кнопке «Открыть» редких склепов (как у «Исследовать»). | 2026-05-19 |
| **GUI — 19 языков** | main.py | ✅ PIL-флаги (LangPopupButton), EN→UA→RU→..., Carter/EndOfList статусы→EN | 2026-05-12 |
| **OG-превью** | web/public/img/og-v3.jpg | ✅ Night Blue фон, лого+свечение, градиент текст. Telegram кеш: менять имя файла → og-v4.jpg и т.д. | 2026-05-12 |
| **Auto-update** | updater.py | ✅ v1.3.1 текущая. ZIP только. EXE убран. | 2026-05-19 |
| **Debug Reporter** | debug_reporter.py + server/debug_router.py | ✅ Fire-and-forget FIND+DIALOG скрины → GCP → Telegram @total_hunter_debug_bot. YOLO conf на bbox. Без сохранения на диск. python-multipart установлен на GCP. | 2026-05-19 |
| **Гайд сайта — ROY секция** | web/src/guide_content.js + .en.js + GuidePage.jsx | ✅ Раздел «Система РОЙ 🐝» (RU+EN): механика баланса, event gate, AFK защита, инструкция 4 шага. | 2026-05-19 |
| **Динамическое окно** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо. Работает на любом разрешении. | 2026-05-12 |
| **SEO** | web/ | ✅ useMeta hook (title+desc+OG per page), FAQ Schema JSON-LD (6 вопросов), sitemap обновлён | 2026-05-12 |
| **Статистика лендинга** | server/web_routes.py | ✅ Накопительная: base 300 бирж + 5000 склепов + реальные данные. Только растёт. | 2026-05-12 |
| **Installer** | installer.iss | ✅ v1.1.2: Win10+ gate, 64-bit check, авто-язык RU/EN | 2026-05-09 |
| **Silent Observer** | main.py + server/web_routes.py | ✅ crash reporter: crash_report.txt + POST /web/crash_report + вкладка Краши в админке | 2026-05-09 |
| **Snap-right fix** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо сразу | 2026-05-12 |
| **Mobile OAuth** | web_routes.py + LoginPage.jsx | ✅ /auth/google/start + /callback, детект мобилки, JWT в URL | 2026-05-10 |
| **Guide — точность детекции** | guide_content.js/en.js + GuidePage.jsx | ✅ Биржи 80%, Склепы 30%, предупреждение про скорость нейросети | 2026-05-10 |
| **Скачать в хедере** | Layout.jsx | ✅ кнопка ↓ Скачать бота рядом с балансом, видна на всех страницах | 2026-05-10 |
| **Admin Panel** | server/admin/index.html | ✅ adjust_credits по user_id + вкладка Краши (crash reports) | 2026-05-09 |
| **Реф-безопасность** | server/web_routes.py | ✅ ref_bonus_claimed — бонус только при новом HWID | 2026-05-08 |
| **Лендинг** | web/LandingPage.jsx | ✅ 3D скриншоты, кнопка ZIP v1.2.2, мобильный хедер (Гайд/RU/Войти) | 2026-05-12 |
| **Мобильный сайт** | web/src/styles/mobile.css | ✅ Единая ширина всех страниц. Гайд: TOC dropdown + Windows-баннер. Рефералы: кнопка под инпутом. | 2026-05-12 |
| **MLM Реферальное дерево** | web/src/pages/ReferralTreePage.jsx + web/src/components/ReferralTree.jsx | ✅ Отдельная страница /dashboard/tree. Pan+zoom (drag мышью + колесо). Org-chart ПК, аккордеон мобилка. L1→L2→L3. Backend: GET /web/referral/tree, 3 async-запроса, index на invited_by_id. | 2026-05-13 |
| **Guide Settings** | web/GuidePage.jsx + guide_content*.js | ✅ Раздел "Настройки бота": 16 слайдеров RU/EN с диапазонами | 2026-05-09 |
| **Безопасность** | server/main.py | ✅ atomic /use_credit, backup_db.sh | 2026-05-04 |

---

## Текущие ключи и токены (хранить только здесь)

### Admin API
- `ADMIN_SECRET_KEY`: `[в systemd override.conf на GCP]` ⚠️ НЕ хранить здесь
- ⚠️ Нужно добавить `ADMIN_TOKEN=` в override.conf (сейчас работает дефолт `dev-admin-token` — небезопасно!)
- Команда обновления версии: `curl -X POST "https://api.total-hunter.com/admin/version/update?version=X.X.X" -H "Authorization: Bearer <ADMIN_TOKEN>"`

### NOWPayments
- API Key: `[в systemd override.conf на GCP — NOWPAYMENTS_API_KEY]` ⚠️ НЕ хранить здесь
- IPN Secret: `[в systemd override.conf на GCP — NOWPAYMENTS_IPN_SECRET]` ⚠️ НЕ хранить здесь
- Public Key: `8d82b5f6-61b6-48e5-9656-19ed7eb68c4b`
- IPN URL: `https://api.total-hunter.com/web/payment/webhook`

### Реклама
- **Coinzilla** — ОТКАЗ. Принимают только Web3/крипто-проекты.
- **A-Ads** — ОТКАЗ. Мин. вывод 0.002 BTC (~$160) через Lightning — слишком высокий.
- **PopAds** — 🟡 На модерации (до 3 дней). Мин. вывод $5 USDT TRC20. Формат: Pop-under.
- **Лучшие альтернативы:** BitMedia ($20 BTC/USDT, баннеры), BidVertiser ($10 BTC)

### Vercel
- Token: `[см. .claude/settings.local.json → env.VERCEL_TOKEN]` — название токена: **16.05.2026** ⚠️ НЕ хранить сам токен здесь (публичный репо!)
- Team: `team_CkkRPXdwtRtsL9YCk8n4Fzla`
- Project: `prj_mWtcb6hJCkl40YLWheeIlxD5NmXj`
- GitHub repoId: `1215361801`

---

## 🔧 GCP — важные факты
- VM: `total-hunter-backend`, zone=`us-central1-f`, project=`digital-arcade-274010` (Debian 12)
- SSH: через Cloud Shell → `gcloud compute ssh total-hunter-backend --zone=us-central1-f`
- FK_* переменные (Free-Kassa) удалены из `/etc/systemd/system/totalhunter.service` 2026-05-09
- Все env vars в порядке: GOOGLE_CLIENT_ID ✅, JWT_SECRET_KEY ✅, NOWPAYMENTS ✅

## 🔍 Конкурент-разведка mercexchangefinder.com
- Crowd-sourced модель: клиенты сканируют → отправляют на сервер → WS дашборд
- API: `coords: null` в публичном ответе — координаты только за кредиты
- Их слабость: нет автонавигации, координаты платные, данные устаревают быстро
- Строить свой пул смысла нет — биржи живут 2-5 мин, не накопишь

## ✅ v1.3.1 — ВЫПУЩЕН (2026-05-19)

- Собран с MSVC 14.3, 10 модулей Nuitka ✅ (добавлен debug_reporter)
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.3.1
- Сервер: /version/latest → 1.3.1 ✅
- ZIP загружен в GitHub Release ✅

### Что нового в v1.3.1
- CryptHunter: swing1 применяется к кнопке «Открыть» редких склепов
- ROY: сканирование засчитывается ТОЛЬКО во время ивента «Торговые Пути»
- ROY: AFK защита — миникарта должна меняться ≥15% за 30 сек
- ROY: звук при появлении новых координат в пуле
- Debug: автоматические FIND+DIALOG скрины с YOLO conf → Telegram разработчику

---

## ✅ v1.3.0 — ВЫПУЩЕН (2026-05-17)

- Собран с MSVC 14.3 (SSE2 baseline, без AVX2), 9 модулей Nuitka ✅
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.3.0
- Сервер: /version/latest → 1.3.0 ✅
- ZIP загружен в GitHub Release ✅ (доступен по прямой ссылке)
- Сервер обновлён: /version/latest → 1.3.0 ✅
- GCP: git pull + systemctl restart ✅

### Что нового в v1.3.0
- Змейка продолжается после находки биржи (не останавливается)
- YOLO guard: 10-секундная блокировка после любой детекции
- Карточка «Последняя биржа» в GUI вкладки Биржи
- DPI awareness: SetProcessDpiAwareness(2) — фикс HiDPI
- .gitignore создан, __pycache__ убраны из git
- 8 новых TDD-тестов (8/8 ✅)

---

## ✅ v1.2.8 — ВЫПУЩЕН И ПРОВЕРЕН (2026-05-15)

- Собран с MSVC 14.3 (SSE2 baseline, без AVX2)
- 9 модулей скомпилированы через Nuitka+MSVC
- Проверен на i5-3470 (Ivy Bridge) — 0xc000001d больше не воспроизводится ✅
- Проверен на машине разработчика — работает ✅
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.2.8
- Сервер: /version/latest → 1.2.8 ✅

---

## ✅ Сделано 16.05.2026

- **Миграции в репо**: 3 файла (22864ea6408d, 575bdc292d9e, 14e8d8e2a95a) — crash_reports, link_codes, hwid_history
- **Сервер**: swap 1GB добавлен, cron-очистка каждое воскресенье 03:00
- **Безопасность**: Vercel token утёк через STATE.md → аннулирован → заменён. Токены убраны из STATE.md
- **bot_speed**: один ползунок вместо scan_interval+move_wait. Честный динамический sleep
- **Оптимизация**: single-frame pipeline (убрали pyautogui.screenshot из hot path), dynamic sleep
- **РОЙ клик**: stop→sleep(0.1-0.2)→click bbox→sleep(0.4-0.6)→OCR
- **GUI вкладки**: РЕФЕРАЛЫ в полном слове. Двухрядная навигация: 4 вкладки (CTkSegmentedButton) + Калибровка по центру снизу (CTkButton) — без CTkTabview, чистый grid. tab_cal и tab_roy переведены на все 19 языков.
- **Telegram канал**: шаблоны постов записаны в буфер

## ✅ Сделано 17.05.2026

- **v1.3.0**: змейка не останавливается, YOLO guard 10с, карточка «Последняя биржа», DPI awareness
- **TDD**: 8 тестов test_exchange_guard.py (8/8 ✅)
- **.gitignore**: создан, __pycache__ убраны из git-индекса навсегда
- **GCP**: git pull + restart ✅, конфликт untracked migrations решён через rm

## ✅ Сделано 18.05.2026

- **Fortune Wheel v1→v6**: итеративная разработка, 6 версий за сессию
  - Бэкенд: новая таблица призов (78/12/6/3/1%), SECTORS[], pick_sector(), sector_to_angle(), sector_index+angle в response. 7 TDD тестов.
  - Фронтенд: 4-слойный canvas (metallic base + neon disc + glass + pointer), физика трения, ratchet-звук через Web Audio noise burst, spring pointer physics, 2×DPR
  - Текстуры: Unsplash photo-1546484396/photo-1736506159893 (дерево) + photo-1545873509 (золото), загружаются crossOrigin='anonymous', fallback gradient если CORS блок
  - v6 исправил тёмные цвета секторов и тяжёлый лаковый overlay
- **GCP deploy команда** исправлена в CLAUDE.md: `cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main`
- **Кнопка бота**: "+5" зелёная оставлена как была (изменение откатано)

## 🔴 Задачи (приоритет по порядку)

### 1. 🎮 Живой тест v1.3.0
- Запустить бота → найти биржу → проверить:
  - Карточка «Последняя биржа» обновилась
  - Бот продолжил змейку (не остановился)
  - `GET /roy/pool` вернул запись

### 2. 🎰 Fortune Wheel — доработка визуала
- Unsplash текстуры CORS-blocked — нужно либо проверить другой источник, либо смириться с fallback
- Колесо_4 (v4) было признано пользователем неудовлетворительным. v6 исправляет яркость — ждём финальную оценку
- Возможное направление: подготовить реальные PNG-ассеты (нарисованные дизайнером) и положить в `web/public/img/wheel/`

### 3. 📢 Реклама
- **Adsterra** — нативные баннеры, вывод от $5 WebMoney/Paxum. Позиционировать как "Game Tools"
- Позиционировать: "Game Tools & Automation", не "bot"

### 4. 🔧 Технический долг
- Миграции в репо уже есть (22864ea6408d, 575bdc292d9e, 14e8d8e2a95a) ✅
- Баг «бот выкидывает в магазин» — не диагностирован, следить

## ⚠️ ИЗВЕСТНЫЕ БАГИ
- **Скорость бирж на CPU** — async YOLO запланирован на v1.2.7. Сейчас workaround: scan_interval >= 3с.
- **Баг: выкидывает в магазин** — не диагностирован, жалоба от клиента.

## 📋 На будущее (не к спеху)
1. **Discord-бот/ветка** — полноценная интеграция Total Hunter с Discord-сервером

---

## Архитектура платежей и синхронизации (нерушимо)

- **NOWPayments IPN**: raw bytes HMAC-SHA512 (НЕ json.loads/dumps)
- **Long-poll**: `/vault/sync/{hwid}` + `notify_balance_changed(hwid)` после commit
- **Earn endpoint**: `/web/earn/reward` + `/web/earn/status`, лимит 5/день
- **SQLAlchemy**: flush() + один commit() — никогда два db.begin()
