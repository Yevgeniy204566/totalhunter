# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-06-20 (Хангоф #100) — **Релиз v1.8.1 выпущен.** Сундуки полностью готовы: сбор+отправка+биллинг (backend на GCP с 2026-06-19), ползунок скорости клика (v1.8.0), и тюнинг полей OCR-распознавания (v1.8.1) — после релиза v1.8.0 владелец обнаружил, что `chest_type` читался с заголовка карточки вместо строки «Источник:»; вместо расследования первопричины (расхождение `python main.py` vs EXE, вероятно DPI/рендер — не установлена) добавлен ручной D-Pad тюнинг с живым прямоугольником-оверлеем поверх игры (2 новых пункта `chest_sender`/`chest_type` в существующем «Тюнинг кликов», через `coord_manager.ui_offsets`). По пути финальный whole-branch review нашёл и тут же исправил баг: `change_lang` мог упасть с `IndexError` при смене языка с выбранным сундучным таргетом (дублирующийся хардкод списка целей в двух местах `main.py` — унифицирован в `TUNE_TARGET_NAMES`). Владелец живо проверил на игре — рамка точно встаёт на «Источник:». Подробности → раздел «Сундуки» в таблице модулей ниже.

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
| **Система РОЙ** | roy/ + server/roy.py + engine.py | ✅ **v1.7.2:** Экономика времени — drain при простое (тумблер ON + бот не ищет → −30 сек/мин через `POST /roy/idle`, `_tick_roy_drain` в main.py). Плюс из v1.7.1: пул без лимита (height=400, скролл), автоочистка 20мин, тумблер OFF=пул скрыт, пул при старте/после ESC, consume=False. | 2026-06-08 |
| **TG-канал тизер** | server/tg_channel.py | ✅ Работает. `send_telegram_alert()` — `sendMessage` с текстом `🟢 ➕1️⃣` в канал `-1003983747219` (@Total_Hunter). Без файлов, без file_id. Протестировано curl → `ok:true`. GCP задеплоен. Триггер: новая биржа в РОЙ во время Торговых Путей. | 2026-06-04 |
| **Версия в заголовке** | main.py | ✅ `f"Total Hunter v{VERSION}"` — автоматически обновляется | 2026-05-07 |
| **Версия в админке** | server/admin/index.html | ✅ Колонка "Версия бота" в таблице пользователей | 2026-05-07 |
| **Tournament Reader** | tournament_reader.py | ✅ **Фаза 2 готова + ЖИВОЙ ТЕСТ ПРОЙДЕН** (34/34 теста). Standalone CLI: pixel-shift навигация (`measure_scroll_shift`, matchTemplate), Otsu+4-кандидата OCR имён (psm 7/6 × normal/inv, `clean_name` 4 стадии), anti-AFK клик каждые 180с, закреплённая «своя» строка. Живой прогон 95/95 строк: 0% пустых имён (было 37%), 0 крашей (anti-AFK сработал), `own_data` верный (место 54 "ЗОЛОТОЙ" 320100). 4 косметических случая (захват VIP-бейджа в хвост имени, напр. "SG By") — пользователь подтвердил: исправлять вручную на сайте, не блокирует. ⚠️ Не интегрирован в GUI бота, не собран в релиз — отдельный CLI-скрипт. **Backend-эндпоинт `/api/v1/tournaments/import` НЕ СУЩЕСТВУЕТ** (export_to_api всегда падает в локальный JSON-fallback). | 2026-06-16 |
| **Сундуки (клиент)** | chest_reader.py + main.py (вкладка СУНДУКИ) | ✅ **Реализовано и живо-протестировано (2026-06-18).** Без скролла — клик «Открыть» по верхней строке, список сам сдвигается. Имя отправителя и тип сундука читаются по ФИКСИРОВАННЫМ координатам (`SENDER_REF_RECT=(816,375,361,24)`, `SOURCE_REF_RECT=(865,398,371,24)`, через `coord_manager.to_region_dialog`). **chest_type = строка «Источник:»**. Локальный буфер `chest_buffer.db` (SQLite, gitignored). Живой тест: 1276+ сундуков, 0 крашей. `coord_picker.py` — служебная утилита калибровки. **2026-06-18 обновлено**: `export_to_api` теперь возвращает `{"success": bool, "low_credits"?: bool}` вместо bool; кнопка «Отправить» больше НЕ зовёт `spend_credit` — биллинг переехал на сервер. **2026-06-19 — ползунок скорости клика готов** (`44de0fa`→`9e06218`→`3604bb8`→`79615fa`, TDD subagent-driven, 2 задачи, оба ревью + финальный whole-branch review чисто): `chest_reader.py` принимает явный `pause_range` (дефолт не тронут, 24/24 теста); `main.py` — `CTkSlider` 0.1–1.0 над кнопкой СТАРТ, формула `lower=max(0.1, v-0.1), upper=lower+0.2`, сохранение в `gui_config.json["chest_click_pause"]` без отдельной кнопки, перевод `chest_speed_lb` на 19 языков. **Живая проверка (Step 8) пройдена владельцем** — `chest_click_pause: 0.2` сохранилось в `gui_config.json` после реального прогона, «всё получилось». **2026-06-20 — релиз v1.8.0 собран и выпущен.** После релиза владелец обнаружил баг: `chest_type` читался с заголовка карточки вместо строки «Источник:» (промах по высоте, причина не установлена — расхождение `python main.py` vs EXE, вероятно DPI/рендер). Решение: тюнинг вместо расследования первопричины — 2 новых пункта в существующем D-Pad «Тюнинг кликов» (`chest_sender`/`chest_type`, через `coord_manager.ui_offsets`), живой прямоугольник-оверлей поверх игры при выборе одного из них (`docs/superpowers/specs/2026-06-20-chest-fields-tuning-design.md`). Subagent-driven, 3 задачи + 1 фикс после финального ревью (краш `change_lang` при смене языка с выбранным сундучным таргетом — дублирующийся хардкод списка целей, унифицирован в `TUNE_TARGET_NAMES`). Владелец живо проверил — рамка точно встаёт на «Источник:». **Релиз v1.8.1 выпущен и задеплоен на сервер.** | 2026-06-20 |
| **Сундуки (backend-фундамент)** | server/chests.py + server/models.py (ChestCollector/Chest/PlayerAlias/ChestTypeAlias) | ✅ **Реализовано 2026-06-18, TDD subagent-driven (5 задач). ЗАДЕПЛОЕНО НА GCP 2026-06-19** (коммит `a9d01f3`, `alembic upgrade head` → `h7c8e9s0t1c2`, сервис active). По пути исправлен баг merge-миграции `p1q2r3s4t5u6` (фиктивный two-parent merge) + вручную почищены 2 лишние строки `alembic_version` на проде. `POST /api/v1/chests/import`: тенант = `users.id` (через hwid) × kingdom × clan → `ChestCollector` (get-or-create, slug для будущего дашборда). Alias-словари (`PlayerAlias`/`ChestTypeAlias`, скоуп per-collector) исправляют OCR-ошибки в имени И типе сундука. Идемпотентность — in-memory pre-check + unique constraint `(collector_id, sender_raw, chest_type_raw, collected_at)`, портативно для SQLite-тестов и Postgres-прода (без `ON CONFLICT`). **Биллинг на сервере**: флэт 10 кредитов за батч, списывается атомарно с записью ТОЛЬКО если в батче есть хоть одна новая запись (повторная отправка дубликата бесплатна — это и есть смысл идемпотентности), 402 при нехватке. Race-fix: `IntegrityError` на commit → rollback (отменяет и списание) → пересчёт коллектора+ключей → одна повторная попытка. Источник правды: `docs/superpowers/specs/2026-06-18-chests-backend-foundation-design.md` + `docs/superpowers/plans/2026-06-18-chests-backend-foundation.md`. Тесты: `server/tests/test_chests.py` (14), `test_chest_reader.py` (17 вкл. `export_to_api`). Все 5 задач + 2 whole-branch review прошли Approved. **Что дальше**: собрать новый клиентский релиз (main.py/chest_reader.py изменились с последнего ZIP). Явно вне рамок: веб-редактор алиасов, публичный дашборд по `collector_slug`, Ownership Transfer (PIN-код передачи прав сборщика). **2026-06-20 — публичная сводка готова и задеплоена.** `GET /api/v1/chests/summary/{slug}` (без авторизации, slug — сам контроль доступа) агрегирует `chests` по `GROUP BY sender_canonical, chest_type_canonical` прямо в SQL, отдаёт `{kingdom, clan, chest_types, players[{name,counts,total}], totals}`, сортировка по total убыв. + имя как tie-break. TDD subagent-driven (3 задачи), оба ревью + финальный whole-branch review чисто (2 minor-фикса применены: детерминированная сортировка, убран устаревший комментарий теста). Задеплоено на GCP, живой `curl` 404 на неизвестный slug подтверждён. Интерим-инструмент `export_chests_to_sheet.py` (корень, НЕ на GCP) — пуллит сводку и полностью перезаписывает Google Sheet (`clear()`+`update()`) через `service_account.json` (тот же файл, что у `sync_to_gemini.py`, добавлен scope `spreadsheets`). **Живой прогон пройден**: создан реальный Sheet под аккаунтом владельца, расшарен Editor на `gemini-sync@...iam.gserviceaccount.com` (сервис-аккаунты не могут создавать файлы в своём Drive — нулевая квота, поэтому направление шаринга как у Docs), залит коллектор `m00bqgjcl1xqUHRDvEa8bQ` (229/BERS) — 103 игрока, 3852 сундука. Грабля: RU-локаль Sheets называет первую вкладку «Лист1», не «Sheet1» — захардкожено в `SHEET_RANGE`. Источник правды: `docs/superpowers/specs/2026-06-20-chests-summary-export-design.md` + `docs/superpowers/plans/2026-06-20-chests-summary-export.md`. **Следующий шаг** — красивая публичная веб-страница на сайте по `/chests/{slug}`, использует тот же GET-эндпойнт. **2026-06-20 — управление алиасами через Google Sheets готово и задеплоено.** Реакция на Gemini-предложение «Админской таблицы» (`docs/Входящие_Gemini.md`) — разбито на 2 спринта (сначала алиасы, потом очки/паттерны T5-T9, см. `project_chest_history_2week_cycles.md` в памяти). Архитектурная развилка: алиасы теперь применяются **на чтении** (LEFT JOIN + COALESCE в `summary`), а не на записи — новый алиас мгновенно правит всю историю без переимпорта; старые `*_canonical` в `chests` остались нетронутыми, просто больше не читаются. Новый `POST /api/v1/chests/aliases/import` (`server/chest_aliases.py`) — Bearer `$ADMIN_TOKEN` (паттерн как в `clan.py`, но с фиксом: `HTTPBearer(auto_error=False)` + явная проверка `creds is None`, иначе отсутствующий заголовок давал 401 вместо требуемых 403 — баг отсутствует здесь, но **обнаружен как есть в `clan.py`, не тронут, отдельный follow-up**), полная замена алиасов коллектора в одной транзакции (DELETE+INSERT), идентификация по `collector_slug`. Два новых листа «Player Aliases»/«Chest Aliases» в том же Sheet, что и сводка. `sync_admin_sheet_to_db.py` (корень, не на GCP) читает листы и шлёт в эндпойнт. TDD subagent-driven (3 задачи + 1 доп. тест на схлопывание many-to-one алиасов по запросу ревьюера), все ревью + финальный whole-branch review чисто (1 minor-фикс применён: `.strip()` ячеек перед отправкой). **Живой прогон пройден полностью**: листы созданы в реальном Sheet, скрипт прогнан против прода с реальным `ADMIN_TOKEN`, `player_aliases`/`chest_type_aliases` подтверждены прямым `psql` на GCP. Источник правды: `docs/superpowers/specs/2026-06-20-chest-aliases-admin-sheet-design.md` + `docs/superpowers/plans/2026-06-20-chest-aliases-admin-sheet.md`. Вне рамок (следующий спринт): глобальный `chest_type_catalog` с очками, паттерны T5-T9. **2026-06-20 — глобальный каталог очков, паттерны и i18n готовы и задеплоены (Фаза 2).** Архитектура (English is the Core, по предложению Gemini): `ChestTypeAlias.canonical_type` теперь английское универсальное имя из эталонного списка 138 сундуков (не текст на языке клана — бот работает на 20+ языках, будущие сборщики будут на китайском и др.). `ChestCollector.pattern`/`language` — новые поля, константы НА ВЕСЬ КЛАН (не на игрока), админ ставит вручную через `POST /aliases/import` (2 опциональных поля, без нового эндпойнта). Две новые ГЛОБАЛЬНЫЕ таблицы (общие для всех кланов): `chest_type_catalog` (canonical_type×pattern→очки), `chest_localizations` (canonical_type×language→текст), с админ-эндпойнтами `POST /catalog/import`/`POST /localizations/import` (Bearer ADMIN_TOKEN, full-replace, защита от дублей ключей → 400 не 500). `GET /summary/{slug}`: если у коллектора задан pattern — **INNER JOIN** с каталогом этого паттерна, сундуки не из каталога **полностью исключаются** (не в очки, не в счётчик, не в лидерборд; игрок только с внеформатными сундуками не попадает в ответ вообще); если pattern не задан — старое поведение без изменений (обратная совместимость подтверждена тестом). Sheet остаётся простым — 3 новых 2-колоночных вкладки (Chest Catalog, Localizations, Collector Settings), без широких таблиц на 5 паттернов/20 языков впрок. `export_chests_to_sheet.py`: колонки Очки/Всего сундуков перед разбивкой по типам. TDD subagent-driven (6 задач, самая сложная — Task 4, SQL с двойным JOIN — прошла ревью с opus без единого замечания по существу), финальный whole-branch review чисто (применены 2 minor-фикса: уточняющий комментарий, понятная ошибка парсинга очков). **Живой прогон пройден полностью на реальных данных**: коллектор 229/BERS, добавлен 1 реальный алиас («Эпический склеп 35 уровня»→«Epic Crypt 35»), сразу отразилось в `summary` — 109 сундуков у Niduel × 135 очков = 14715, локализация на русский, сортировка по очкам убыв. Источник правды: `docs/superpowers/specs/2026-06-20-chest-catalog-points-localization-design.md` + `docs/superpowers/plans/2026-06-20-chest-catalog-points-localization.md`. **Известное ограничение**: реальные очки видны только для сундуков, у которых уже есть алиас raw→English (сейчас 1 из 18); остальные ~17 каталожных типов нужно прописать в «Chest Aliases» — задача владельца. Вне рамок (Фаза 3): тайм-ивенты (Древний и др.) + норма урона по весам, см. `project_chest_events_phase2.md`. **2026-06-20 — брейнсторм публичной страницы `/chests/{slug}` начат, не завершён.** Решено: страница полностью публичная, без логина на сайте (slug = право доступа, как у backend-эндпойнта уже сейчас). Дизайн (вёрстка, состав данных на странице) не зафиксирован — продолжить вопросы в следующей сессии перед `writing-plans`. | 2026-06-20 |
| **Clan Roster Reader** | clan_roster_reader.py | 🔄 **Фаза 0 — в работе.** PITCH=86, HEADER=35 верны. **Архитектура имени финальная:** широкий кроп y=0..57 для ВСЕХ карточек + OCR psm=6 + `_clean_name` берёт первую не-статусную строку. **Проблема Фазы 0:** интерфейс "живой" — размер сепаратора между карточками варьируется от 3px (card_1) до 40px (card_2) в зависимости от количества иконок у предыдущего игрока. Фиксированный Y=25..45 не работает. Решение: широкий кроп + regex-стрип статусов. **ТЕСТ НЕ ЗАПУЩЕН** — нужен живой прогон с открытой панелью. Backend `/api/v1/clan/roster` НЕ СУЩЕСТВУЕТ. | 2026-06-17 |
| **Combo** | combiner.py | ⛔ ЗАМОРОЖЕН | 2026-05-02 |
| **Авто-калибровка** | auto_calibration.py | ✅ 2 этапа, 13 тестов | 2026-05-03 |
| **Движок бирж** | engine.py + navigator.py + roy/ | ✅ **v1.6.5:** ESC = абсолютная остановка (`after_cancel(_auto_restart_id)` + `_esc_stopped`). Фикс клика (moveTo+click). tesseract_bin портативный в сборке. | 2026-06-02 |
| **ROY real-time** | main.py `_start_roy_sse_listener` + server/roy.py | ✅ SSE подписка в боте. При находке биржи любым участником → мгновенное обновление пула. **v1.6.2:** собственные находки не дают двойной звук (`_roy_self_reported`). GCP задеплоен. | 2026-06-01 |
| **Telegram OCR отчёт** | engine.py + debug_reporter.py + server/debug_router.py | ✅ После каждой биржи: `✅ OCR: K:X X:Y Y:Z — P%` или `❌ OCR: не распознаны`. Эндпоинт `/api/debug/send-text` на GCP. | 2026-06-01 |
| **CryptHunter** | crypt_hunter.py | ✅ **v1.7.3:** Фикс silent floor — `max(300.0,…)` заменён на `max(60.0,…)`. Значения марша < 5 мин (2, 3, 4 мин) теперь реально применяются. Раньше любое значение ниже 5 мин молча зажималось до 300 сек. | 2026-06-09 |
| **Тюнинг кликов (D-Pad)** | coord_manager.py + main.py | ✅ **v1.6.9:** Баг AP-SWING-OVERRIDE устранён — crypt_swing больше не перезаписывает ui_offsets при загрузке. Сохранение через «Сохранить профиль», ui_offsets авторитетны. | 2026-06-03 |
| **Калибровка** | calibration_ui.py + main.py | ✅ **v1.5.12:** клик в лупе работает. `win.after` перенесён в начало `_refresh`, `_update_dot` в try/except, `win.focus_force()`, `iconify()` вместо `withdraw()`. | 2026-05-31 |
| **GUI — 19 языков** | main.py | ✅ PIL-флаги (LangPopupButton), EN→UA→RU→..., Carter/EndOfList статусы→EN | 2026-05-12 |
| **OG-превью** | web/public/img/og-v3.jpg | ✅ Night Blue фон, лого+свечение, градиент текст. Telegram кеш: менять имя файла → og-v4.jpg и т.д. | 2026-05-12 |
| **Auto-update** | updater.py | ✅ v1.4.1. ZIP плоский (exe в корне). xcopy `extract_dir\*`. Петля устранена. | 2026-05-20 |
| **Debug Reporter** | debug_reporter.py + server/debug_router.py | ✅ Fire-and-forget FIND+DIALOG скрины → GCP → Telegram @total_hunter_debug_bot. YOLO conf на bbox. Без сохранения на диск. python-multipart установлен на GCP. | 2026-05-19 |
| **Гайд сайта — ROY секция** | web/src/guide_content.js + .en.js + GuidePage.jsx | ✅ Раздел «Система РОЙ 🐝» (RU+EN): механика баланса, event gate, AFK защита, инструкция 4 шага. | 2026-05-19 |
| **Динамическое окно** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо. Работает на любом разрешении. | 2026-05-12 |
| **SEO** | web/ | ✅ **Полный SEO-спринт (2026-05-25):** URL-локализация (EN=default, RU=/ru prefix), 12 prerender-маршрутов (6EN+6RU) с html[lang]/title/desc/og, hreflang x-default+en+ru (статика prerender + динамика useMeta), FAQ JSON-LD EN+RU, sitemap.xml 12 URL xhtml:link, Vercel Analytics ✅. **2026-06-04 Мобильный SEO + Desktop аудит:** preload LCP logo, manifest.json (PWA), theme-color, softwareVersion→1.6.9, fetchpriority+aspect-ratio на logo, screenshots column на мобиле, prefers-reduced-motion, credits-badge скрыт на мобиле, дубль FAQ JSON-LD устранён, sitemap lastmod→2026-06-04. **2026-06-09 Entity SEO:** meta description RU = "Триумф: Рождение Империй" + "Scorewarrior"; EN = "MMO RTS by Scorewarrior". FAQ вопрос про Android/iOS с органичными ключами. Дисклеймер footer (юридическая защита + ключи). Переиндексация запрошена в Search Console. | 2026-06-09 |
| **Видео на лендинге** | web/public/video/exchange-demo.mp4 | ✅ **2026-06-04:** HTML5 demo-видео (1.7МБ). autoPlay/loop/muted/playsInline. Кнопка 🔇/🔊 через useRef (обход React muted-бага). scale(1.13) убирает letterboxing. Секция «Как это работает» между скриншотами и статистикой. | 2026-06-04 |
| **Статистика лендинга** | server/web_routes.py | ✅ Накопительная: base 300 бирж + 5000 склепов + реальные данные. Только растёт. | 2026-05-12 |
| **Installer** | installer.iss | ✅ v1.1.2: Win10+ gate, 64-bit check, авто-язык RU/EN | 2026-05-09 |
| **Silent Observer** | main.py + server/web_routes.py | ✅ crash reporter: crash_report.txt + POST /web/crash_report + вкладка Краши в админке | 2026-05-09 |
| **Snap-right fix** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо сразу | 2026-05-12 |
| **Mobile OAuth** | web_routes.py + LoginPage.jsx | ✅ /auth/google/start + /callback, детект мобилки, JWT в URL | 2026-05-10 |
| **Guide — точность детекции** | guide_content.js/en.js + GuidePage.jsx | ✅ Биржи 80%, Склепы 30%, предупреждение про скорость нейросети | 2026-05-10 |
| **Скачать в хедере** | Layout.jsx | ✅ кнопка ↓ Скачать бота рядом с балансом, видна на всех страницах | 2026-05-10 |
| **Admin Panel** | server/admin/index.html | ✅ adjust_credits по user_id + вкладка Краши (crash reports). **HTTP Basic Auth на GET /admin** (браузер-диалог) + Bearer на все /admin/* API. | 2026-05-27 |
| **Реферальная система** | server/web_routes.py | ✅ **Полный TDD-аудит (2026-05-26):** BUG-1 (+50 invited безусловно даже если inviter забанен), BUG-2 (db.begin→begin_nested в /activate), BUG-3 (cycle detection ≤3 хопов), BUG-4 (naive/aware datetime в hwid/reset). 57 тестов зелёных. notify_balance_changed в /activate. | 2026-05-26 |
| **Лендинг** | web/LandingPage.jsx | ✅ **2026-06-09:** секция "О проекте" (соло-разработчик), секция "Мы платим за честность" (+300 алмазов за отзыв → Telegram), FAQ секция (7 вопросов, рендерится), дисклеймер footer. 3D скриншоты, demo-видео, Live Stats, мобильный хедер. | 2026-06-09 |
| **Мобильный сайт** | web/src/styles/mobile.css | ✅ Единая ширина всех страниц. Гайд: TOC dropdown + Windows-баннер. Рефералы: кнопка под инпутом. | 2026-05-12 |
| **MLM Реферальное дерево** | web/src/pages/ReferralTreePage.jsx + web/src/components/ReferralTree.jsx | ✅ Отдельная страница /dashboard/tree. Pan+zoom (drag мышью + колесо). Org-chart ПК, аккордеон мобилка. L1→L2→L3. Backend: GET /web/referral/tree, 3 async-запроса, index на invited_by_id. | 2026-05-13 |
| **Guide Settings** | web/GuidePage.jsx + guide_content*.js | ✅ Раздел "Настройки бота": 16 слайдеров RU/EN с диапазонами | 2026-05-09 |
| **Безопасность** | server/main.py | ✅ atomic /use_credit, backup_db.sh | 2026-05-04 |

---

## Текущие ключи и токены (хранить только здесь)

### Admin API
- `ADMIN_SECRET_KEY`: `[в systemd override.conf на GCP]` ⚠️ НЕ хранить здесь
- ✅ `ADMIN_TOKEN` настроен и рабочий (проверено 2026-06-08 при релизе v1.7.2) — актуальное значение в `.claude/settings.local.json` → `ADMIN_TOKEN`. Старое значение из памяти `project_build_release.md` устарело (≈20 дней) и больше не подходит — сверять с settings.local.json.
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

### ✅ 0. 🐝 РОЙ — экономика времени (drain) — ВЫПУЩЕНО и ЗАДЕПЛОЕНО v1.7.2 (2026-06-08)

Простой = тумблер ROY ON + `is_running=False` → −30 сек/мин (`POST /roy/idle`, `IDLE_DRAIN_SEC=30`, rate-limit 58с, floor на нуле). Тумблер OFF — без изменений. Тик `_tick_roy_drain` в main.py (по аналогии с `_tick_trade_routes`, раз в минуту), сервер: `server/roy.py`. 5 TDD-тестов зелёных.

**Релиз закрыт полностью:** сборка (10/10 Nuitka) → ZIP → GitHub Release [v1.7.2](https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.7.2) → `/admin/version/update` → 1.7.2 ✅ → GCP `git pull` (`d62cd60→4cb0afd`) + `systemctl restart` → active ✅ → `/roy/idle` отвечает в проде ✅.

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
