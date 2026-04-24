# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-04-25 (Хангоф #13)

---

## Статус модулей

| Модуль | Файл | Статус | Дата |
|---|---|---|---|
| GUI | main.py | ✅ Готов, 2 языка, 4 вкладки, 4 темы, Diamond Rebrand: ◆ справа от баланса, info_banner, кр→◆ | 2026-04-22 |
| Движок бирж | engine.py + navigator.py | ✅ Готов, EMA нормализация исправлена | 2026-04-20 |
| CoastalSnakeNavigator | navigator.py | ✅ Готов, 42 теста, EMA clamp убран | 2026-04-20 |
| MiniMap Reader | minimap_reader.py | ✅ Готов, 15 тестов | 2026-04-13 |
| CryptHunter (слепой склеп) | crypt_hunter.py | ✅ Готов, 23 теста, OCR масла удалён | 2026-04-24 |
| CoordManager | coord_manager.py | ✅ Готов, 14 тестов, верифицирован | 2026-04-09 |
| Cloud API (бэкенд) | server/ | ✅ Задеплоен на GCP, PostgreSQL, systemd | 2026-04-20 |
| Admin Panel | server/admin/index.html | ✅ Feedback badge + Leaderboard TOP-50 | 2026-04-21 |
| Web Platform (личный кабинет) | server/web_routes.py + web/ | ✅ Phase 2D + Diamond Rebrand: Guide gambling redesign, BalancePage алмазы, LITE/PRO/ULTRA | 2026-04-22 |
| Economy (Free-Kassa + рефералы) | server/payments.py | ✅ Phase 2B завершена, FK env vars добавлены в systemd | 2026-04-21 |

---

## Текущая работа (2026-04-25)

- **Бот 100% функционально завершён** — все модули работают
- **GCP деплой актуален** — FastAPI + PostgreSQL + systemd на `34.68.86.57:8000` ✅
- **Phase 2A/2B/2D — ЗАВЕРШЕНЫ** ✅ задеплоено на GCP + Vercel
- **Diamond Rebrand — ЗАВЕРШЁН** ✅ (коммиты `67aa5c1`, `3e80743`) — кредиты→алмазы на сайте и в программе
- **Ожидает:** прописать webhook URL в кабинете Free-Kassa: `http://34.68.86.57:8000/web/payment/webhook`
- **Phase 2C (Community)** — следующий этап

---

## Рабочие механизмы

### CryptHunter — Слепой склеп ✅
- OCR времени марша полностью удалён (2026-04-17)
- Формула: `T_one_way = T_max / 2^N`, где N = ползунок «Ускорение марша» (0–5)
- `_max_march_sec` = ползунок «Дальность марша» × 60 (default 900с = 15 мин)
- `total_wait = int(T_one_way * 2) + break_sec±20%`
- Детект конца списка: image-diff меню при скролле, `no_move_count >= 3`
- При None: 30с пауза → `_reset_search()` (2 клика по Арена) → повтор

### CoastalSnakeNavigator ✅
- Centroid воды → `water_angle = atan2(row, col)` → `inland_vec` ⊥ к берегу
- HOMING (зрячий) → DIVING (слепой, счётчик) → RETURNING (слепая + зрячая фазы)
- EMA: `self._coast_angle = (a + alpha * diff_raw) % (2 * np.pi)` — БЕЗ np.clip (убран!)
- `_steps_since_shift = 0` сбрасывается во всех переходах HOMING→DIVING и DIVING→RETURNING
- Мягкая диагональ: `blind_factor = 1.0 - angle_ratio * diagonal_blind_coeff`
- force_shift_after = счётчик-стена (0=выкл)
- EMA сглаживание угла: coast_ema_alpha=0.3

### Цветовые темы GUI ✅
- 4 утверждённые палитры: **Dark Mode**, **Deep Night**, **Ocean** (эталон), **Light** (Wet Asphalt & Sand)
- `THEMES` dict в `main.py`: ключи `value_text`, `checkbox`, `checkbox_hover` у каждой темы
- Deep Night: `value_text=#88AAFF`, `checkbox=#3D6EFF`, `on_surface=#FFFFFF`
- Шрифты ползунков: размер 13–14px, bold
- Тема сохраняется в `gui_config.json`, применяется после рестарта

### Координатная система ✅
- REF_A=(90,925), REF_B=(1149,88) — верифицировано пользователем
- dialog_offset_y — микроподстройка кликов для браузера (сохраняется в gui_config.json)
- Все 3 профиля работают: client, chrome, firefox

### Серверный API ✅
- Web: `/payment/create`, `/payment/webhook`, 10+ роутов /web/*, JWT, Google OAuth, HWID anti-fraud
- Bot: 18 роутов (bot API + admin API)
- Admin: `/admin/leaderboard?period=alltime|month|week`, `/admin/feedback/*` с badge
- HTTP 402 при нехватке кредитов
- Heartbeat: daemon thread, 12×10s sleep для мгновенной остановки
- **8 таблиц БД:** User, Transaction, Hunt, Log, Broadcast, AppSetting, Feedback, **Order**

### Web Platform ✅ (Phase 2A + 2B завершены)
- Vercel proxy `/api/*` → GCP:8000 (решает Mixed Content)
- Google Auth → ref_code cookie → invited_by_id в БД
- HWID anti-fraud: бонусы только при первом HWID (проверка по hwid_history)
- Страницы: Dashboard, Profile, Balance (**реальные пакеты lite/pro/ultra**), Hunts, Referrals, Feedback, Devices, Transactions, Guide, Legal
- BalancePage: 3 пакета ($1/$5/$10), кнопка → POST /payment/create → redirect FK
- Ad slots: top `.ad-slot` + footer `.ad-slot-footer` в Layout.jsx

### Economy ✅ (Phase 2B завершена)
- **Пакеты:** lite=$1/300cr, pro=$5/2000cr, ultra=$10/5000cr
- **Free-Kassa:** HMAC MD5 подпись (FK_SECRET_WORD для ссылки, FK_SECRET_WORD2 для вебхука)
- **Вебхук идемпотентен:** `order.status == "paid"` — защита от двойного зачисления
- **Реферальная каскад:** L1=10%, L2=5%, L3=1% от `credits_total` (включая бонусы)
- **Забаненный реферер** скипается, цепочка продолжается к следующему уровню
- **24 теста** — cascade, idempotency, webhook, leaderboard
- **Ожидает настройки:** FK_MERCHANT_ID/FK_SECRET_WORD/FK_SECRET_WORD2 в systemd + webhook URL в кабинете FK

---

## Известные баги / TODO

| Приоритет | Баг/TODO | Файл |
|---|---|---|
| **HIGH** | Прописать webhook URL в кабинете Free-Kassa: `http://34.68.86.57:8000/web/payment/webhook` | FK merchant dashboard |
| **MED** | Вставить дополнительные иллюстрации в GuidePage (скрины калибровки уже есть) | web/src/pages/GuidePage.jsx |
| **MED** | Task 4 тест: добавить happy path invited_by_id | server/tests/test_web_routes.py |
| LOW | КАЛИБРОВКА: картинки и описания точек А/Б уже есть, можно добавить ещё деталей | main.py |
| LOW | force_update bot-side обработка из app_settings | engine.py / auth.py |

---

## SaaS Master Plan — следующие модули

**~~Phase 2B (Economy / Модуль 4)~~ — ЗАВЕРШЕНА** ✅

**Phase 2C (Community):**
- Публичный leaderboard
- Notifications / broadcasts

**Phase 3 (Bot):**
- Translations (EN/CN/DE)

---

## Архив закрытого

### Закрыто (Хангоф #13 — 2026-04-25)
- ~~Gemini Sync~~ — `sync_to_gemini.py` реализован и протестирован (10 unit-тестов ✅). OAuth 2.0 Desktop App через существующий GCP проект. Запускать после каждого Хангоф: `python sync_to_gemini.py`. 4 Google Docs обновляются (ANTI-PATTERNS, CLAUDE, MEMORY, STATE). `token.json` сохранён, следующие запуски без браузера.

### Закрыто (Хангоф #12 — 2026-04-24)
- ~~Gemini Sync попытка через MCP~~ — base64 PowerShell добавляет пробелы → невалидно. MCP create_file не умеет обновлять существующие Google Docs. Решение выбрано: Python скрипт через Google Docs API. Реализация в следующей сессии.

### Закрыто (Хангоф #11 — 2026-04-24)
- ~~OCR-проверка масла~~ — `OIL_STOP_THRESHOLD`, `parse_oil()`, `_read_oil()` удалены из CryptHunter. OCR путал «М» с «К» → ложный стоп при 6.06М. Игра сама защищает от нулевого масла через `_send_captain`. ANTI-PATTERNS #21.

### Закрыто (Хангоф #10 — 2026-04-22)
- ~~Diamond Rebrand (сайт)~~ — GuidePage: Diamond/NeonCard компоненты, кредиты→алмазы, убраны черепа/мечи, gambling-стиль Ultra, L1/L2/L3 glow (фикс L1 hex цвет), Smart Coastline Scouting
- ~~Diamond Rebrand (программа)~~ — "Купить кредиты" убраны из табов, ◆ справа от баланса (оба таба), +5кр→+5, баланс 46px унифицирован, Google login → глобальный info_banner
- ~~BalancePage~~ — SCOUT/STALKER/RAIDER → LITE/PRO/ULTRA, кредиты→алмазы, Diamond компонент со свечением, КР→◆
- ~~GuidePage~~  — полный контент из GKB_Gemini (10 секций), калибровочные скрины подключены

### Закрыто (Хангоф #9 — 2026-04-21)
- ~~LoginPage~~ — полный редизайн в Deep Night стиле: gradient bg, card с glow, feature pills, loading state, error box
- ~~GuidePage~~ — полный редизайн: sticky TOC sidebar, 7 секций с контентом, карточки пакетов, FAQ, CTA
- ~~docs/guide_knowledge_base.md~~ — база знаний бота (сырьё для гайда и модерации платёжных систем)
- ~~FK env vars~~ — инструкция + sed-скрипт для добавления в systemd на GCP

### Закрыто (Хангоф #8 — 2026-04-21)
- ~~Auth persistence bug~~ — `atob()` не умеет base64url; добавлен `.replace(/-/g,'+').replace(/_/g,'/')` в `isLoggedIn()`
- ~~Умная навигация~~ — логотип Layout → `/dashboard`, App.jsx `/` редиректит залогиненных, LandingPage кнопки адаптивны
- ~~Dashboard stat tiles~~ — увеличены: padding 28px, fontSize 54px, font-weight 900, label 13px bold

### Закрыто (Хангоф #7 — 2026-04-21)
- ~~СКЛЕПЫ tab: CTkScrollableFrame contour~~ — `border_width=1`, `corner_radius=12`, MD3 outline, прозрачный scrollbar track, разделитель 1px
- ~~HWID anti-fraud~~ — бонусы только при первом HWID (hwid_history), дубликат пишет Transaction("hwid_duplicate_blocked")
- ~~Phase 2B Economy~~ — payments.py, Order модель, /payment/create, /payment/webhook (идемпотентный), 3-уровневый каскад, leaderboard, BalancePage реальные кнопки
- ~~Alembic migration orders~~ — `server_default=sa.text("'pending'")`, `sa.text('now()')` — корректный синтаксис
- ~~SQLAlchemy expire bug~~ — `order_id_str` захватывается внутри транзакции до commit
- ~~Admin leaderboard~~ — GET /admin/leaderboard?period=alltime|month|week, Alpine.js UI, nav item

### Закрыто (Хангоф #6 — 2026-04-20)
- ~~Phase 2A Tasks 5–17~~ — все задачи выполнены и задеплоены
  - POST /web/feedback endpoint + Pydantic Field validation
  - GCP: alembic merge heads + upgrade head + restart ✅
  - api.js: globalStats(), sendFeedback(), authGoogle(token, ref_code)
  - Layout.jsx: ad slots + feedback nav
  - App.jsx: /ref/:code + /dashboard/feedback routes
  - RefPage.jsx: th_ref cookie (30 дней) + redirect /login
  - LoginPage.jsx: читает th_ref cookie, передаёт в authGoogle
  - DashboardPage: 3 StatTile (exchanges_today, crypts_today, active_hunters)
  - ReferralsPage: полная ссылка + copy + Transfer to Balance
  - FeedbackPage: textarea 1000 chars + counter + send
  - BalancePage: Daily Bonus + Buy Credits stubs
  - Admin: feedback badge + таблица + JS polling 30s
- ~~Бот ходил по воде~~ — EMA np.clip убран, `% 2π` нормализация оставлена
- ~~Deep Night slider values невидимы~~ — добавлен `value_text` ключ в THEMES
- ~~Deep Night checkbox тёмный~~ — добавлен `checkbox`/`checkbox_hover` ключ в THEMES
- ~~Шрифты ползунков мелкие~~ — увеличены до 13–14px, bold

### Закрыто (Хангоф #5 — 2026-04-20)
- ~~Авторизация через Google~~ — починена (Vercel proxy + GoogleLogin компонент + api.js)
- ~~Phase 2A Tasks 1–4~~ — Theme CSS, Feedback model, /web/stats/global, ref_code в auth

### Закрыто (Хангоф #4)
- ~~CORS `"*"` → исправлен на explicit origins + `allow_credentials=True`~~
- ~~Модуль 2 бэкенд~~ — реализован и задеплоен (web_routes.py, 8 эндпоинтов, 10 тестов)
- ~~Модуль 2 фронтенд~~ — React+Vite, все страницы, Deep Night тема, Vercel деплой

### Закрыто (Хангоф #3)
- ~~HIGH: coast_detect_radius~~ — закрыт, пользователь регулирует слайдерами
- ~~MED: image-diff одинаковые склепы~~ — проверено, не воспроизводится, баг надуман
- ~~scroll лимит 30~~ — исправлен: `while self.is_running` + детект конца по `no_move_count >= 3`
