# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-04-20 (Хангоф #6)

---

## Статус модулей

| Модуль | Файл | Статус | Дата |
|---|---|---|---|
| GUI | main.py | ✅ Готов, 2 языка, 4 вкладки, 4 темы, шрифты +15%, Deep Night фикс | 2026-04-20 |
| Движок бирж | engine.py + navigator.py | ✅ Готов, EMA нормализация исправлена | 2026-04-20 |
| CoastalSnakeNavigator | navigator.py | ✅ Готов, 42 теста, EMA clamp убран | 2026-04-20 |
| MiniMap Reader | minimap_reader.py | ✅ Готов, 15 тестов | 2026-04-13 |
| CryptHunter (слепой склеп) | crypt_hunter.py | ✅ Готов, 31 тест, скролл до конца списка | 2026-04-18 |
| CoordManager | coord_manager.py | ✅ Готов, 14 тестов, верифицирован | 2026-04-09 |
| Cloud API (бэкенд) | server/ | ✅ Задеплоен на GCP, PostgreSQL, systemd | 2026-04-20 |
| Admin Panel | server/admin/index.html | ✅ Feedback badge + таблица записей | 2026-04-20 |
| Web Platform (личный кабинет) | server/web_routes.py + web/ | ✅ Phase 2A завершена, задеплоена | 2026-04-20 |
| Economy (Free-Kassa + рефералы) | — | ⏳ Следующий (Phase 2B) | — |

---

## Текущая работа (2026-04-20)

- **Бот 100% функционально завершён** — все модули работают
- **GCP деплой актуален** — FastAPI + PostgreSQL + systemd на `34.68.86.57:8000` ✅
- **Phase 2A — ЗАВЕРШЕНА** ✅ (все 17 задач, commits до `605259f`, задеплоено на GCP + Vercel)
- **Phase 2B (Economy)** — следующий этап

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
- Web: 10+ роутов /web/*, JWT, Google OAuth, HWID linking, feedback
- Bot: 18 роутов (bot API + admin API)
- Admin: `/admin/feedback/unread`, `/admin/feedback/list` с badge в UI
- HTTP 402 при нехватке кредитов
- Heartbeat: daemon thread, 12×10s sleep для мгновенной остановки
- 7 таблиц БД: User, Transaction, Hunt, Log, Broadcast, AppSetting, Feedback

### Web Platform ✅ (Phase 2A завершена)
- Vercel proxy `/api/*` → GCP:8000 (решает Mixed Content)
- Google Auth → ref_code cookie → invited_by_id в БД
- Страницы: Dashboard (global stats), Profile, Balance (stubs), Hunts, Referrals (link+transfer), Feedback, Devices, Transactions, Guide, Legal
- Ad slots: top `.ad-slot` + footer `.ad-slot-footer` в Layout.jsx
- `/ref/:code` → cookie `th_ref` (30 дней) → redirect /login

---

## Известные баги / TODO

| Приоритет | Баг/TODO | Файл |
|---|---|---|
| **MED** | Task 4 тест: добавить happy path invited_by_id | server/tests/test_web_routes.py |
| LOW | КАЛИБРОВКА: добавить описание с картинками (Точка А/Б) | calibration_ui.py / main.py |
| LOW | force_update bot-side обработка из app_settings | engine.py / auth.py |

---

## SaaS Master Plan — следующие модули

**Phase 2B (Economy / Модуль 4):**
- Free-Kassa вебхуки → `/purchase` endpoint
- L1/L2/L3 % от покупок рефералов (10%/5%/1%)
- Leaderboard TOP-50 в admin dashboard

**Phase 2C (Community):**
- Публичный leaderboard
- Notifications / broadcasts

**Phase 3 (Bot):**
- Translations (EN/CN/DE)

---

## Архив закрытого

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
