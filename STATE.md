# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-04-18 (Хангоф #3)

---

## Статус модулей

| Модуль | Файл | Статус | Дата |
|---|---|---|---|
| GUI | main.py | ✅ Готов, 2 языка, 4 вкладки, 4 темы, MD3 редизайн | 2026-04-18 |
| Движок бирж | engine.py + navigator.py | ✅ Готов | 2026-04-13 |
| CoastalSnakeNavigator | navigator.py | ✅ Готов, 42 теста | 2026-04-14 |
| MiniMap Reader | minimap_reader.py | ✅ Готов, 15 тестов | 2026-04-13 |
| CryptHunter (слепой склеп) | crypt_hunter.py | ✅ Готов, 31 тест, скролл до конца списка | 2026-04-18 |
| CoordManager | coord_manager.py | ✅ Готов, 14 тестов, верифицирован | 2026-04-09 |
| Cloud API (бэкенд) | server/ | ✅ Реализован, деплой в процессе | 2026-04-16 |
| Admin Panel | server/admin/index.html | ✅ Реализован (MD3 dark) | 2026-04-16 |
| Web Platform (личный кабинет) | — | ⏳ Следующий | — |
| Economy (Free-Kassa + рефералы) | — | ⏳ Следующий | — |

---

## Текущая работа (2026-04-18)

- **Бот 100% функционально завершён** — нареканий нет, все модули работают
- Деплой GCP в процессе (server/ готов, нужен финальный деплой)
- **GUI редизайн завершён** — MD3 тёмная тема, 4 утверждённые палитры
- **Цветовые палитры зафиксированы** → `docs/color_palettes.md` (эталон для бота и сайта 1:1)
- **Следующий этап:** SaaS — Модуль 2 (Web Platform, личный кабинет)

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
- Мягкая диагональ: `blind_factor = 1.0 - angle_ratio * diagonal_blind_coeff`
- force_shift_after = счётчик-стена (0=выкл)
- EMA сглаживание угла: coast_ema_alpha=0.3

### Цветовые темы GUI ✅
- 4 утверждённые палитры: **Dark Mode**, **Deep Night**, **Ocean** (эталон), **Light** (Wet Asphalt & Sand)
- `THEMES` dict в `main.py`, тема сохраняется в `gui_config.json`
- Эталонный файл: `docs/color_palettes.md` — используется и для сайта (CSS-переменные готовы)
- Selector рядом с языком, применяется после рестарта

### Координатная система ✅
- REF_A=(90,925), REF_B=(1149,88) — верифицировано пользователем
- dialog_offset_y — микроподстройка кликов для браузера (сохраняется в gui_config.json)
- Все 3 профиля работают: client, chrome, firefox

### Серверный API ✅
- 18 роутов (bot API + admin API)
- HTTP 402 при нехватке кредитов
- Heartbeat: daemon thread, 12×10s sleep для мгновенной остановки
- 6 таблиц БД: User, Transaction, Hunt, Log, Broadcast, AppSetting

---

## Известные баги / TODO

| Приоритет | Баг/TODO | Файл |
|---|---|---|
| LOW | КАЛИБРОВКА: добавить описание с картинками (Точка А/Б) | calibration_ui.py / main.py |
| LOW | CORS "*" → реальный домен после настройки | server/main.py |
| LOW | force_update bot-side обработка из app_settings | engine.py / auth.py |

### Закрыто (Хангоф #3)
- ~~HIGH: coast_detect_radius~~ — закрыт, пользователь регулирует слайдерами
- ~~MED: image-diff одинаковые склепы~~ — проверено, не воспроизводится, баг надуман
- ~~scroll лимит 30~~ — исправлен: `while self.is_running` + детект конца по `no_move_count >= 3`

---

## SaaS Master Plan — следующие модули

**Модуль 2 (личный кабинет):**
- Google OAuth → web UI
- Баланс кредитов, история охот
- HWID reset 1×/неделю

**Модуль 4 (Economy):**
- Free-Kassa вебхуки → `/purchase` endpoint
- L1/L2/L3 % от покупок рефералов
- Leaderboard TOP-50 в admin dashboard
