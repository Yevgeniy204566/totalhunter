# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-06-02 **v1.6.6** — OCR пауза 0.6с перед первым захватом (диалог успевает отрисоваться); регламент чеклиста сборки в CLAUDE.md.

**Frontend URL:** https://total-hunter.com (Vercel + Cloudflare)
**Backend URL:** https://api.total-hunter.com → GCP 34.68.86.57:8000 (Nginx + SSL)

**Frontend Deploy:** hook + alias (работает стабильно, без forceNew)
- Token: в `.claude/settings.local.json` → env.VERCEL_TOKEN (не в репо!)
- hook: `POST /v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw`
- ⚠️ Vercel Analytics подхватывается ТОЛЬКО новым билдом. Включить сервис → сразу редеплой.

---

## Статус модулей

| Модуль | Файл | Статус | Дата |
|---|---|---|---|
| **Платежи** | server/payments.py | ✅ NOWPayments (крипто). IPN raw bytes HMAC-SHA512. Работает. | 2026-05-07 |
| **Long-poll синхронизация** | server/vault.py | ✅ GET /vault/sync/{hwid} — мгновенный обмен баланса бот↔сайт | 2026-05-07 |
| **Колесо Фортуны** | server/earn.py + web/EarnPage.jsx | ✅ **Fortuna Royale v7** — SVG-колесо (20 секторов), фото-текстуры (бархат×4 + красное дерево), неоновое кольцо, заклёпки CSS-градиент, LED-chase, указатель с physics, easeOutSmooth 7-8s. Звук: только победный аккорд (тики убраны). Лимит 5/день, безлимит для owner (ievgeniy2011@gmail.com). Кнопка +5 ведёт на /dashboard/earn. Призы: 5◆(78%) 7◆(12%) 15◆(6%) 30◆(3%) 50◆(1%). | 2026-05-18 |
| **GUI main.py — навигация** | main.py | ✅ Порядок вкладок: СКЛЕПЫ→БИРЖИ→РОЙ→РЕФЕРАЛЫ. Таймер «Торговые Пути» в БИРЖИ и РОЙ (якорь 20.05.2026 20:00 Киев, цикл 5 дней, 24ч). Кнопки СТАРТ/СТОП в вкладке РОЙ (дублируют БИРЖИ). Переводы на 19 языков. change_lang полностью обновляет все ROY-метки. | 2026-05-23 |
| **Рекламные слоты** | web/AdSlot.jsx | ⏸ **ОТЛОЖЕНО до 500+ DAU (2026-05-29).** AdSlot.jsx удалён, мета-теги Coinzilla/BitMedia убраны из index.html. Два пути на будущее: 1) Баннеры (BitMedia/A-Ads) 2) Rewarded Video в рулетке (Lootably S2S callback). Подробности → MEMORY/project_ads_strategy.md | 2026-05-29 |
| **Система РОЙ** | roy/ + server/roy.py + engine.py | ✅ **v1.6.5:** OCR fix — динамический ROI (центр 60% monitors[1]), автопоиск Tesseract (PATH→C:→D:), portable tesseract_bin/ 72МБ полный (56 DLL + eng.traineddata). Не зависит от калибровки. Event gate 144ч. Пул: MM:SS возраст. | 2026-06-02 |
| **Версия в заголовке** | main.py | ✅ `f"Total Hunter v{VERSION}"` — автоматически обновляется | 2026-05-07 |
| **Версия в админке** | server/admin/index.html | ✅ Колонка "Версия бота" в таблице пользователей | 2026-05-07 |
| **Combo** | combiner.py | ⛔ ЗАМОРОЖЕН | 2026-05-02 |
| **Авто-калибровка** | auto_calibration.py | ✅ 2 этапа, 13 тестов | 2026-05-03 |
| **Движок бирж** | engine.py + navigator.py + roy/ | ✅ **v1.6.5:** ESC = абсолютная остановка (`after_cancel(_auto_restart_id)` + `_esc_stopped`). Фикс клика (moveTo+click). tesseract_bin портативный в сборке. | 2026-06-02 |
| **ROY real-time** | main.py `_start_roy_sse_listener` + server/roy.py | ✅ SSE подписка в боте. При находке биржи любым участником → мгновенное обновление пула. **v1.6.2:** собственные находки не дают двойной звук (`_roy_self_reported`). GCP задеплоен. | 2026-06-01 |
| **Telegram OCR отчёт** | engine.py + debug_reporter.py + server/debug_router.py | ✅ После каждой биржи: `✅ OCR: K:X X:Y Y:Z — P%` или `❌ OCR: не распознаны`. Эндпоинт `/api/debug/send-text` на GCP. | 2026-06-01 |
| **CryptHunter** | crypt_hunter.py | ✅ **v1.6.0:** `scroll_clicks` — настраиваемые тики скролла (1–200). Chrome=100+, Client=3. GUI слайдер в СКЛЕПЫ, сохранение в профиль. Дальность марша от 1 мин. | 2026-06-01 |
| **Тюнинг кликов (D-Pad)** | coord_manager.py + main.py + crypt_hunter.py | ✅ **v1.6.3:** Секция «Тюнинг кликов» в КАЛИБРОВКА переведена на все 19 языков (`cal_tune_title/wt_icon/carter/top_accel/march_accel/reset`). Выбор хранится по индексу (0–3) — не сбрасывается при смене языка. | 2026-06-02 |
| **Калибровка** | calibration_ui.py + main.py | ✅ **v1.5.12:** клик в лупе работает. `win.after` перенесён в начало `_refresh`, `_update_dot` в try/except, `win.focus_force()`, `iconify()` вместо `withdraw()`. | 2026-05-31 |
| **GUI — 19 языков** | main.py | ✅ PIL-флаги (LangPopupButton), EN→UA→RU→..., Carter/EndOfList статусы→EN | 2026-05-12 |
| **OG-превью** | web/public/img/og-v3.jpg | ✅ Night Blue фон, лого+свечение, градиент текст. Telegram кеш: менять имя файла → og-v4.jpg и т.д. | 2026-05-12 |
| **Auto-update** | updater.py | ✅ v1.4.1. ZIP плоский (exe в корне). xcopy `extract_dir\*`. Петля устранена. | 2026-05-20 |
| **Debug Reporter** | debug_reporter.py + server/debug_router.py | ✅ Fire-and-forget FIND+DIALOG скрины → GCP → Telegram @total_hunter_debug_bot. YOLO conf на bbox. Без сохранения на диск. python-multipart установлен на GCP. | 2026-05-19 |
| **Гайд сайта — ROY секция** | web/src/guide_content.js + .en.js + GuidePage.jsx | ✅ Раздел «Система РОЙ 🐝» (RU+EN): механика баланса, event gate, AFK защита, инструкция 4 шага. | 2026-05-19 |
| **Динамическое окно** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо. Работает на любом разрешении. | 2026-05-12 |
| **SEO** | web/ | ✅ **Полный SEO-спринт (2026-05-25):** URL-локализация (EN=default, RU=/ru prefix), 12 prerender-маршрутов (6EN+6RU) с html[lang]/title/desc/og, hreflang x-default+en+ru (статика prerender + динамика useMeta), FAQ JSON-LD EN+RU, sitemap.xml 12 URL xhtml:link, Vercel Analytics ✅, track(Register_Started + Referral_Link_Copied). Dashboard сохраняет lang через localStorage. **2026-05-29:** откат поломок Gemini — vite base, .vercelignore, sitemap 4 несуществующих URL удалены. **Фикс GSC «Вариант страницы с тегом canonical»:** `useMeta.js` теперь динамически обновляет `<link rel="canonical">` на текущий URL каждой страницы (ранее все страницы отдавали статичный `https://total-hunter.com` из index.html → Google считал их дублями главной). | 2026-05-29 |
| **Статистика лендинга** | server/web_routes.py | ✅ Накопительная: base 300 бирж + 5000 склепов + реальные данные. Только растёт. | 2026-05-12 |
| **Installer** | installer.iss | ✅ v1.1.2: Win10+ gate, 64-bit check, авто-язык RU/EN | 2026-05-09 |
| **Silent Observer** | main.py + server/web_routes.py | ✅ crash reporter: crash_report.txt + POST /web/crash_report + вкладка Краши в админке | 2026-05-09 |
| **Snap-right fix** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо сразу | 2026-05-12 |
| **Mobile OAuth** | web_routes.py + LoginPage.jsx | ✅ /auth/google/start + /callback, детект мобилки, JWT в URL | 2026-05-10 |
| **Guide — точность детекции** | guide_content.js/en.js + GuidePage.jsx | ✅ Биржи 80%, Склепы 30%, предупреждение про скорость нейросети | 2026-05-10 |
| **Скачать в хедере** | Layout.jsx | ✅ кнопка ↓ Скачать бота рядом с балансом, видна на всех страницах | 2026-05-10 |
| **Admin Panel** | server/admin/index.html | ✅ adjust_credits по user_id + вкладка Краши (crash reports). **HTTP Basic Auth на GET /admin** (браузер-диалог) + Bearer на все /admin/* API. | 2026-05-27 |
| **Реферальная система** | server/web_routes.py | ✅ **Полный TDD-аудит (2026-05-26):** BUG-1 (+50 invited безусловно даже если inviter забанен), BUG-2 (db.begin→begin_nested в /activate), BUG-3 (cycle detection ≤3 хопов), BUG-4 (naive/aware datetime в hwid/reset). 57 тестов зелёных. notify_balance_changed в /activate. | 2026-05-26 |
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
- Public Key: `7cfa559f-b834-4d2e-9200-c29f921d1b5e`
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

## ✅ ФИНАЛЬНЫЙ АУДИТ — ПРОЙДЕН (2026-05-27)

**5 независимых агентов проверили весь проект. Все критические баги исправлены.**
Коммит: `1e37687` | GCP задеплоен ✅

### Что исправлено по аудиту:
1. **engine.py** — якорь ивента синхронизирован с сервером: `1780333200` (2026-06-01 17:00 UTC), цикл 144ч. Старый якорь (2026-05-20) давал расхождение ~12 дней между ботом и сервером.
2. **server/main.py** — GET `/admin` теперь требует `require_admin`. Ранее HTML-страница админки была доступна без токена.
3. **auth.py** — голые `except:` заменены на `except Exception:` в 3 местах (spend_credit, heartbeat, log_error_to_server). Голый except глотает KeyboardInterrupt → бот не закрывался по Ctrl+C.
4. **.gitignore** — добавлены `*.pyd`, `*.so`, `*.exe`. Nuitka-модули больше не попадут в git случайно.

### Пост-аудит фикс (2026-05-27):
5. **server/main.py** — Аудит повесил Bearer на GET `/admin`, но браузер не умеет отправлять Bearer при прямом переходе по URL → 403 навсегда. Исправлено: GET `/admin` → **HTTP Basic Auth** (браузер показывает системное окно логина: `admin` / `ADMIN_TOKEN`). Все `/admin/*` API-эндпоинты по-прежнему защищены Bearer. Коммит: `5efb4db`.

### Что НЕ является проблемой (решено или legacy):
- Масло в crypt_hunter.py — механика масла не используется, код legacy, игнорируем
- Rate limits — желательно, не критично для текущего объёма
- Пустые server-тесты — технический долг, не баг
- CompassNavigator — legacy, не используется активно

---

## ✅ v1.5.9 — ВЫПУЩЕН (2026-05-27) ← ТЕКУЩИЙ

**БОТ ФУНКЦИОНАЛЬНО ЗАВЕРШЁН** — весь запланированный функционал реализован.
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.9
- Сервер /version/latest → 1.5.9 ✅
- ZIP: 354 МБ, 10 Nuitka .pyd модулей (MSVC 14.3, SSE2 baseline) ✅

### Что нового в v1.5.9:
1. **ROY браузер-совместимость:** OCR ROI увеличен до 600×200px — координаты биржи читаются у Chrome/Firefox игроков (~85px смещение поглощается)
2. **Trade Routes — реальный цикл:** is_trade_routes_active() на сервере (anchor 2026-06-01 17:00 UTC, 144ч цикл = 24ч ивент + 120ч пауза). Убрана заглушка «ивент всегда активен»
3. **Таймер пула MM:SS:** countdown до истечения каждого лота (TTL 20 мин). Зелёный >10мин → жёлтый → красный → серый
4. **Backtrack тайминг:** после шага назад ожидание = move_wait (2.0с) вместо 0.3с → карта успевает остановиться до повторного YOLO-скана
5. **Client-side ивент таймер:** GUI показывает «🟢 ИДЁТ — до конца: Xч MMмин» или «до начала: Xч MMмин» с live обновлением

---

## ✅ v1.5.8 — ВЫПУЩЕН (2026-05-27)

### Что нового в v1.5.8:
1. Ghost YOLO: скорость бота одинакова до/после рестарта биржи — `_last_yolo_inference_time` симулирует нагрузку во время 5с YOLO-блока
2. Tkinter-based restart: каскад повторных рестартов устранён, `restart_after_exchange` удалён
3. Guard `if not self.is_running: break` перед `joystick.step()` — нет лишнего шага после детекции
4. Пауза клик→OCR: 0.5с → 1.0с (запас для медленных ПК)
5. 28 TDD тестов зелёных

---

## ✅ v1.5.7 — ВЫПУЩЕН (2026-05-23)

**Сервер /version/latest → 1.5.7** ✅
**ZIP: ~338 МБ**
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.7

### Что нового в v1.5.7:
1. Фикс: смена языка (change_lang) теперь обновляет все 8 статических меток вкладки РОЙ
2. `_roy_refresh_balance()` повторно вызывается при смене языка → единицы мин/сек переключаются
3. GCP: таблица `roy_kingdom_members` подтверждена, GRANT → hunter ✅

---

## ✅ v1.5.6 — ВЫПУЩЕН (2026-05-23)

**Сервер /version/latest → 1.5.6** ✅
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.6

### Что нового в v1.5.6:
1. Вкладка РОЙ переведена на все 19 языков (были пропущены JA, ZH, ZH_TW, KO, UK, ID)
2. 12 новых ключей LANGS: roy_title, roy_subtitle, roy_balance_title, roy_join, roy_kingdom_label, roy_coords_title, roy_refresh, roy_no_data, roy_error, roy_empty_pool, roy_pool_empty, roy_pool_count
3. GUI-функции _roy_refresh_pool/_roy_refresh_balance/_roy_update_list используют LANGS вместо хардкода

---

## ✅ v1.5.0 — ВЫПУЩЕН (2026-05-21)

**Сервер /version/latest → 1.5.0** ✅
**ZIP плоский** ✅
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.5.0

### Что нового в v1.5.0:
1. Backtracking в _exchange_detected: шаг назад если биржа улетела за край экрана
2. CoastalSnakeNavigator._click_vec записывает _last_move_vec
3. PacmanEngine._backtrack_step() — инвертирует вектор движения
4. build_release.py автоматически создаёт плоский ZIP + валидирует структуру
5. ANTI-PATTERNS.md: AP-UPDATER-NESTING

---

## ✅ v1.4.3 — ВЫПУЩЕН (2026-05-21)

**Сервер /version/latest → 1.4.3** ✅
**ZIP: 338 МБ** (10 Nuitka модулей MSVC 14.3)
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.4.3
- Клиенты с v1.4.2 обновятся автоматически

### Что нового в v1.4.3:
1. Биржа: fallback на исходный bbox если свежий YOLO промахнулся → бот ВСЕГДА останавливается
2. Биржа: пауза 0.15с → 0.5с перед повторным YOLO — карта успевает остановиться
3. Два фото в Telegram гарантированы (FIND + DIALOG)

---

## ✅ v1.4.2 — ВЫПУЩЕН (2026-05-21)

**Сервер /version/latest → 1.4.2** ✅
**ZIP: 338 МБ** (polars excluded, 10 Nuitka модулей MSVC 14.3)
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.4.2
- Клиенты с v1.4.1 обновятся автоматически

---

## ✅ v1.4.0 — АКТИВЕН (2026-05-20)

- updater.py: xcopy возвращён к плоскому ZIP (`extract_dir\*`)
- ZIP пакуется плоско (TotalHunter.exe в корне без вложенной папки)
- Петля автообновления (День Сурка) полностью устранена
- Клиенты с v1.3.2 обновятся автоматически при следующем запуске
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.4.0
- Сервер: /version/latest → 1.4.0 ✅

## ⚠️ v1.3.3 — СЛОМАН (петля обновлений, 2026-05-19)

- updater.py с багом xcopy → бесконечный цикл обновлений
- НЕ делать этот релиз последним никогда
- GitHub Release существует: v1.3.3

## ✅ v1.3.2 — АКТИВНЫЙ РЕЛИЗ (2026-05-19)

- README.txt в ZIP, золотые ползунки GUI, lightbox для картинок
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.3.2
- Сервер: /version/latest → 1.3.2 ✅

---

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

## ✅ Сделано 29.05.2026

- **Фикс Google Search Console «Вариант страницы с тегом canonical»:** `useMeta.js` теперь динамически обновляет `<link rel="canonical">` при каждом переходе. Раньше все страницы отдавали статичный canonical главной из index.html → Google считал их дублями.
- **Удалена вся реклама с сайта:** AdSlot.jsx удалён, мета-теги Coinzilla/BitMedia убраны. Монетизация реклмой отложена до 500+ DAU.
- **Стратегия рекламы записана в MEMORY** (project_ads_strategy.md): два пути — баннеры и rewarded video рулетка (Lootably S2S).

---

## ✅ v1.5.12 — ВЫПУЩЕН (2026-05-31) ← ТЕКУЩИЙ

### Что нового в v1.5.12:
1. **Фикс калибровки** — клик в лупе теперь двигает точку. Root cause: `_update_dot()` в `_refresh()` стоял ДО `win.after(...)` без try/except → при withdrawn-родителе падал → цикл обновлений обрывался навсегда
2. **`win.after(REFRESH_MS, _refresh)` теперь первый** — цикл переживает любое исключение внутри
3. **`win.focus_force()` + `win.lift()`** — окно гарантированно получает фокус
4. **`iconify()` вместо `withdraw()`** в `_calibrate()` — minimiz не ломает дочерние Toplevel

**Инструкция клиенту:** Скачайте v1.5.12. Нажмите КАЛИБРОВАТЬ → кликайте в лупе → Зафиксировать → СОХРАНИТЬ.

---

## ✅ v1.5.11 — ВЫПУЩЕН (2026-05-31)

### Что нового в v1.5.11:
1. **scale_ui_coord()** — новая функция пропорционального масштабирования UI (не карта). Все статичные кнопки меню (WT_ICON, WT_CRYPTS_TAB, WT_ARENA_TAB, WT_SCROLL_AREA, WT_GOTO_BTN_X, CARTER_EVENT_BAR, ACCEL_USE_BTN) отвязаны от coord_manager и масштабируются пропорционально разрешению экрана.
2. **Центр экрана** — hardcode `960,540` заменён на `pyautogui.size()//2` в `_detect_on_map()`
3. **YOLO imgsz** — `1280→640` в обоих местах navigator.py (×4 быстрее на старых CPU)
4. **Ghost YOLO cap** — sleep ограничен `min(inference_t, move_wait×0.8)` — убирает тормоза на слабых CPU
5. **Авто-сохранение калибровки** — КАЛИБРОВАТЬ теперь сразу сохраняет профиль (не нужна вторая кнопка)
6. **DPI-диагностика** — статус-бар показывает `tk=W×H / mss=W×H`
7. **Предупреждение при сбое загрузки профиля** — вместо молчащего pass

**Инструкция клиенту:** Скачайте v1.5.11, разверните игру на весь экран, нажмите КАЛИБРОВАТЬ.

---

## 🔴 Задачи (приоритет по порядку)

### 1. 🐝 Живой тест Системы РОЙ
- Ждёт ивент «Торговые Пути» (цикл 5 дней от 20.05.2026 20:00 Киев)
- Проверить: серый→зелёный кружок на сайте, координаты у других участников в пуле

### 2. 🎰 Fortune Wheel — доработка визуала
- Unsplash текстуры CORS-blocked — нужно либо проверить другой источник, либо смириться с fallback
- Колесо_4 (v4) было признано пользователем неудовлетворительным. v6 исправляет яркость — ждём финальную оценку
- Возможное направление: подготовить реальные PNG-ассеты (нарисованные дизайнером) и положить в `web/public/img/wheel/`

### 3. 📢 Реклама
- **Adsterra** — нативные баннеры, вывод от $5 WebMoney/Paxum. Позиционировать как "Game Tools"
- Позиционировать: "Game Tools & Automation", не "bot"

### 4. 🐝 ROY — OCR координат из диалога биржи
- **Задача:** При обнаружении биржи (YOLO-детекция) → открывается диалог → OCR читает координаты X/Y из диалогового окна → передаёт в РОЙ-пул вместо/вместе с текущим OCR через `exchange_reader.py`
- Текущее состояние: OCR биржи синхронный (до 4с) есть, но привязан к `_roy_on_found()` в engine.py — нужно проверить что именно читается (координаты из диалога или позиция на миникарте)
- Приоритет: средний

### 5. 🔧 Технический долг
- Миграции в репо уже есть (22864ea6408d, 575bdc292d9e, 14e8d8e2a95a) ✅
- Баг «бот выкидывает в магазин» — не диагностирован, следить

## ⚠️ ИЗВЕСТНЫЕ БАГИ
- **Скорость бирж на CPU** — async YOLO запланирован на v1.2.7. Сейчас workaround: scan_interval >= 3с.
- **Баг: выкидывает в магазин** — не диагностирован, жалоба от клиента.

## 📋 На будущее (не к спеху)
1. **Discord-бот/ветка** — полноценная интеграция Total Hunter с Discord-сервером ✅ СДЕЛАНО (см. Discord Community)

## ✅ Discord Community — запущено (2026-05-19)
- Сервер создан, Carl-bot настроен (reaction roles ✅ → роль «Охотник»)
- Структура: #правила / #анонсы / #скачать-бота / #общение / #ошибки-и-баги / #предложения / #скрины-охоты
- GitHub webhook → Discord #анонсы: автоматически при `gh release create`
- Инвайт: https://discord.gg/7dJQdF2pBG (бессрочный)
- Чейнджлог v1.1→v1.3.1 запощен в Discord
- Иконка Discord (pngwing.com.png) добавлена на лендинг (футер) и в кабинет (шапка)
- На v1.3.2: в авто-пост GitHub добавить кнопку → total-hunter.com/download

---

## Архитектура платежей и синхронизации (нерушимо)

- **NOWPayments IPN**: raw bytes HMAC-SHA512 (НЕ json.loads/dumps)
- **Long-poll**: `/vault/sync/{hwid}` + `notify_balance_changed(hwid)` после commit
- **Earn endpoint**: `/web/earn/reward` + `/web/earn/status`, лимит 5/день
- **SQLAlchemy**: flush() + один commit() — никогда два db.begin()
