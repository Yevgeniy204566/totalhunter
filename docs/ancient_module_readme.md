# «Древний» / "Ancient" — как устроен модуль целиком

> Технический README для будущих сессий и разработчиков. Пользовательская версия (без деталей реализации) — вкладка «Как это работает» на странице `/dashboard/ancients` сайта. Русская версия ниже, английская — во второй половине файла.

---

# RU — Русская версия

## 1. Что это такое

«Древний» — модуль расчёта нормы урона по ежедневному игровому событию «Древний». Клан вносит список игроков (вручную, через бота или через Сундуки), лидер запускает калькулятор — система делит общую норму урона между игроками (по званию или по составу войск) и показывает, кто не дотягивает.

Три поверхности одного модуля:
- **Бот** (`tournament_reader.py`) — читает турнирную таблицу с экрана игры и загружает на сервер.
- **Личный кабинет** (`/dashboard/ancients`, `AncientsPage.jsx`) — лидер/редактор управляет ростером и считает норму.
- **Публичная страница** (`/ancients/:slug`, `PublicAncientsPage.jsx`) — игроки без входа в аккаунт сами вписывают звание/состав войск.

Все три завязаны на общие таблицы БД, привязанные к одному `ChestCollector` (та же сущность «клан-тенант», что и у Сундуков).

## 2. Бот: `tournament_reader.py`

Читает в игре диалог «Статистика» турнира «Древний» — прокручиваемый список игроков.

**Как распознаёт:**
- `detect_dialog_bbox()` находит диалог по HSV-маске (бежевый фон окна).
- `detect_row_pitch()` находит границы строк по градиенту яркости, вычисляет шаг строки.
- `get_row_crops()` вырезает 4 видимые строки за раз, для каждой — ROI имени и ROI очков. У собственной строки бота (внизу диалога) дополнительно есть ROI места/звания.
- **Имя** — сначала пробуется фиксированный порог (обрезает иконку VIP-бейджа), при неудаче — перебор Otsu-порога по 4 комбинациям psm/инверсии, выбирается самый длинный результат. Язык OCR: RU+EN+Latin по умолчанию («Light»), либо + арабский/японский/китайский/корейский («Full» — медленнее, для кланов с нестандартными никами). Словарная коррекция (DAWG) отключена — она портит стилизованные имена.
- **Очки** — просто цифры, всё остальное отбрасывается.
- **Место/звание** (только своя строка) — отдельный OCR цифр.

**Цикл сбора:** измеряет сдвиг прокрутки через сравнение шаблонов (чтобы не читать повторно уже виденные строки), OCRит только новые строки, присваивает порядковое место, прокручивает вниз. Останавливается на 2 подряд нулевых сдвигах (конец списка) или по кнопке «Стоп». Каждые 180 сек — клик по заголовку диалога (анти-AFK, чтобы игра не перекрыла диалог рекламой).

**Загрузка:** POST `{hwid, kingdom, clan, timestamp, items:[{name,place,points}]}` на `/api/v1/tournaments/import`. При сетевой ошибке — сохраняет локально JSON-файлом, не теряя данные.

**UI в боте:** вкладка «ДРЕВНИЙ» в `main.py` — поля Королевство/Клан, переключатель Light/Full языка OCR, одна кнопка Старт/Стоп. Импорта клан-чата на этой вкладке нет (это отдельная, экспериментальная и на данный момент неудачная фича, см. `project_clan_chat_94`/сессия #112 в памяти).

## 3. Модель данных (`server/models.py`)

- **`ChestCollector`** — общий тенант с Сундуками. Поля для Древнего: `ancient_hidden`/`ancient_hidden_at` (скрытие + таймер автоочистки), `ancient_shortfall_light_pct`/`_medium_pct`/`_critical_pct` (пороги подсветки недобора, дефолт 10/30/60), `slug` (общий для `/chests/{slug}` и `/ancients/{slug}`).
- **`PlayerAlias`** — словарь коррекции имён Сундуков (`raw_name → canonical_name`), источник «истинных» имён для fuzzy-сопоставления и «Заполнить из Сундуков».
- **`PlayerProfile`** — общая таблица для Сундуков и Древнего: `(collector_id, canonical_name) → rank, troop_level`. Пишется и с публичной страницы Сундуков/Древнего (`POST /api/v1/chests/public/player-profile`), и из кабинета Сундуков.
- **`AncientRoster`** — одна строка = один игрок в текущем ростере. Полностью перезаписывается импортом турнира (кроме `troop_level`). Поля: `player_name` (эффективное имя — либо сырой OCR, либо каноническое после слияния), `raw_ocr_name` (сохраняется после физического слияния), `place`, `points`, `troop_level`, `source` (`ocr`/`manual`/`chests`), `manual_expires_at` (TTL для ручных записей), `rank`.
- **`AncientCalculation`** — история расчётов, максимум 5 на коллектор. `strategy`, `summon_levels`, `amplification_coef`, `officer_count`/`veteran_count`, `total_quota_millions`, `result_json`.
- **`AncientNameMapping`** — подтверждённое лидером сопоставление `raw_ocr_name → canonical_name` (`confirmed: bool`).
- **`AncientInviteCode`** — одноразовые коды приглашения редактора (24ч TTL).
- **`AncientEditor`** — активные гранты доступа редактора (30 дней от выдачи/повторной выдачи).

## 4. Сервер — кабинет лидера (`server/ancients_dashboard.py`)

Ключевые эндпоинты (`/web/dashboard/ancients`, авторизация — сессия сайта):

| Метод + путь | Что делает |
|---|---|
| `GET /` | Полный дашборд: свои + доступные как редактору коллекторы, ростер, история, `canonical_sources`, скрытые |
| `PATCH /{slug}/ancient-visibility` | Скрыть/показать (только владелец) |
| `PATCH /{slug}/quota-thresholds` | Пороги подсветки недобора (только владелец) |
| `PATCH /{slug}/troop-level`, `/rank` | Правка состава войск/звания одной строки |
| `PATCH /{slug}/name-mappings` | Подтвердить сопоставление имени → физическое слияние строк |
| `DELETE /{slug}/name-mappings/{raw}` | Отменить неподтверждённое сопоставление (для уже слитых — недоступно, 🔒) |
| `DELETE /{slug}/roster/ocr-import` | «Очистить» — стереть последний импорт турнира |
| `DELETE /{slug}/roster/{player_name}` | Удалить строку целиком |
| `POST /{slug}/calculate` | Посчитать норму (Стратегия А/Б) |
| `POST /{slug}/roster/manual` | Добавить участника вручную |
| `POST /{slug}/roster/populate-from-chests` | Зеркалировать ростер из Сундуков |
| `POST /invite`, `POST /{slug}/invite` | Пригласить/принять доступ редактора |

**Как строится ростер (`_roster_rows`)** — три уровня разрешения имени:
1. Уже физически слито (`raw_ocr_name != player_name`) — имя окончательное, показывается 🔒.
2. Есть подтверждённое, но ещё не слитое сопоставление — покажет предложенное каноническое имя, слияние произойдёт при следующем сохранении.
3. Несопоставленное сырое OCR-имя — fuzzy-подбор (`difflib`, порог регулируется ползунком 50-100%) по каноническим именам Сундуков.

**Физическое слияние** — при подтверждении сопоставления две строки ростера (одна с войсками/званием, другая с местом/очками) сливаются в одну, необратимо (кнопка «Разблокировать» скрывается, показывается 🔒) — иначе стало бы неясно, каким очкам какая строка принадлежит.

**«Заполнить из Сундуков»** — это **зеркалирование, не добавление**: список игроков становится точной копией списка Сундуков, все строки без соответствия (включая ручные записи для не-носящих сундуки игроков) удаляются. Кнопка требует двойного подтверждения — операция деструктивна.

**Ручное добавление** — проверка на дубли (точное имя) и на похожие канонические имена Сундуков (fuzzy, порог 0.75 — предлагает «это тот же игрок?»). Срок жизни ручной записи — до конца ближайшего цикла события «Торговые Пути» (`next_trade_routes_end()`), если её не подтвердит реальный импорт или Сундуки.

**Приглашение редактора** — одноразовый код (24ч), после использования — грант на 30 дней. Редактор может править войска/звания/имена/ручные записи, но НЕ может считать норму, менять пороги, скрывать клан или приглашать.

**Расчёт нормы (`ancient_quota.py`):**
- Общая норма = Σ HP уровня Древнего (таблица `ANCIENT_LEVEL_HP`, уровни 81-250) × коэффициент усиления.
- **Стратегия А (по званию):** норма делится между офицерами (`Глава/Старший/Офицер`) и ветеранами в пропорции 1.0:0.5 — офицер получает вдвое больше ветерана.
- **Стратегия Б (по составу войск):** вес игрока = сумма `1.8^(тир-5)` по Земле/Осаде/Коннице, делённая на вес прессета клана (T5-T9, 3 максимальных тира). Норма пропорциональна весу. Без указанного (валидного) состава войск игрок исключается из расчёта, не роняя весь запрос.

## 5. Сервер — публичная страница (`server/ancients_public.py`)

Один эндпоинт, без авторизации: `GET /api/v1/ancients/public/{slug}`.

Возвращает: `kingdom`, `clan`, `quota_thresholds`, `roster: [{player_name, rank, troop_level, points, quota, shortfall_pct}]`.

**Никогда не отдаёт наружу:** `raw_ocr_name`, `mapped_name`, `suggested_name`, `mapping_confirmed` — это внутренние инструменты лидера, не публичная информация. Внутри эндпоинта используется таблица подтверждённых сопоставлений для точного расчёта нормы по Стратегии Б (тот же результат, что видит лидер в кабинете), но сами эти данные не покидают сервер.

**Запись** — не новый эндпоинт: публичная страница переиспользует уже существующий `POST /api/v1/chests/public/player-profile` (та же таблица `PlayerProfile`, тот же коллектор), с антифлуд кулдауном 15 минут на одну запись.

## 6. Связка с Сундуками — что можно с ней и без неё

**Клан БЕЗ Сундуков** — минимальный рабочий путь:
1. Лидер вручную добавляет игроков (`POST /roster/manual`) — без бота и без Сундуков.
2. Считает норму (Стратегия А достаточно только званий; Стратегия Б — состава войск, который могут вписать сами игроки).
3. Игроки заходят на `/ancients/{slug}` и сами вписывают звание/состав через «Ввести состав».
4. Всё работает — но ручные записи «сгорают» к концу цикла «Торговые Пути», если их не подтвердит реальный импорт турнира — лидеру придётся периодически повторять добавление, если клан так и не начнёт вести Сундуки.

**Клан С Сундуками** — что даёт дополнительно:
1. **Канонизация имён** — fuzzy-подбор и проверка дублей при ручном добавлении используют уже накопленный словарь имён Сундуков (`PlayerAlias`), а не начинают с нуля.
2. **«Заполнить из Сундуков»** — мгновенно (одной кнопкой) синхронизирует список участников вместо ручного набора каждого.
3. **Общий `PlayerProfile`** — любое звание/состав войск, который игрок уже указал на публичной странице Сундуков (или лидер вписал в кабинете Сундуков), автоматически видно и учитывается в Древнем — без повторного ввода.

## 7. Автоочистка (`server/ancient_retention.py`)

Два независимых фоновых тика, раз в сутки:
- **Очистка скрытых коллекторов** (60 дней): если коллектор скрыт (`ancient_hidden_at` не пусто) дольше 60 дней без активности — удаляются ТОЛЬКО таблицы Древнего (`AncientRoster`/`AncientNameMapping`/`AncientCalculation`/`AncientEditor`/`AncientInviteCode`). Сундуки, `PlayerAlias`, `PlayerProfile` и сам `ChestCollector` не трогаются. Таймер сбрасывается любой активностью Древнего (импорт турнира, расчёт нормы), пока коллектор скрыт — «живой» скрытый клан никогда не очищается.
- **Очистка просроченных ручных записей** — независимо от статуса скрытия: строки `source='manual'` с истёкшим `manual_expires_at` удаляются каждый тик.

## 8. Фронтенд-маршруты

- `/dashboard/ancients` (авторизация обязательна) → `AncientsPage.jsx` — калькулятор, ростер, история, вкладка «Как это работает».
- `/ancients/:slug` (без авторизации) → `PublicAncientsPage.jsx` — только чтение + режим редактирования собственного звания/состава войск.

---

# EN — English version

## 1. What this is

"Ancient" is a damage-quota calculator for the game's daily "Ancient" event. A clan populates a player roster (manually, via the bot, or by mirroring Chests), the leader runs the calculator — the system splits the total damage quota across players (by rank or by troop composition) and highlights who is falling short.

Three surfaces of one module:
- **Bot client** (`tournament_reader.py`) — reads the in-game tournament leaderboard via OCR and uploads it to the server.
- **Dashboard** (`/dashboard/ancients`, `AncientsPage.jsx`) — the leader/an editor manages the roster and runs the quota calculator.
- **Public page** (`/ancients/:slug`, `PublicAncientsPage.jsx`) — players self-report rank/troop composition without logging in.

All three share the same database tables, keyed to one `ChestCollector` (the same clan-tenant entity Chests uses).

## 2. Bot: `tournament_reader.py`

Reads the in-game "Statistics" dialog for the "Ancient" tournament — a scrollable player leaderboard.

**How it recognizes rows:**
- `detect_dialog_bbox()` finds the dialog via an HSV color mask (tan dialog background).
- `detect_row_pitch()` finds row boundaries from brightness-gradient peaks, deriving row height.
- `get_row_crops()` crops 4 visible rows at a time, each split into a name ROI and a points ROI. The bot's own row (pinned at the bottom) additionally has a place/rank ROI.
- **Name OCR** — tries a fixed threshold first (strips VIP badge glyph noise); falls back to an Otsu-threshold sweep across 4 psm/invert combinations, picking the longest result. Language: RU+EN+Latin by default ("Light"), or + Arabic/Japanese/Chinese/Korean ("Full" — slower, for clans with non-Latin/Cyrillic nicknames). Dictionary correction (DAWG) is disabled — it corrupts stylized names.
- **Points OCR** — digits only, everything else stripped.
- **Place/rank** (own row only) — separate digit OCR.

**Collection loop:** measures scroll shift via template matching (to avoid re-reading already-seen rows), OCRs only newly-revealed rows, assigns sequential rank, scrolls down. Stops after two consecutive zero-shift reads (end of list) or on Stop. An anti-AFK click on the dialog header runs every 180s to prevent the game's ad popup from covering the dialog.

**Upload:** POSTs `{hwid, kingdom, clan, timestamp, items:[{name,place,points}]}` to `/api/v1/tournaments/import`. On network failure, saves the payload as a local JSON file instead of losing the data.

**Bot UI:** the "ANCIENT" tab in `main.py` — Kingdom/Clan fields, a Light/Full OCR language toggle, a single Start/Stop button. There's no clan-chat roster import here (that's a separate, experimental, and currently unsuccessful feature — see the `project_clan_chat_94` memory / session #112).

## 3. Data model (`server/models.py`)

- **`ChestCollector`** — the shared tenant with Chests. Ancient-relevant fields: `ancient_hidden`/`ancient_hidden_at` (hide toggle + retention timer), `ancient_shortfall_light_pct`/`_medium_pct`/`_critical_pct` (shortfall-highlight thresholds, default 10/30/60), `slug` (shared between `/chests/{slug}` and `/ancients/{slug}`).
- **`PlayerAlias`** — the Chests name-correction dictionary (`raw_name → canonical_name`), the source of truth for fuzzy-matching and "Populate from Chests."
- **`PlayerProfile`** — shared between Chests and Ancient: `(collector_id, canonical_name) → rank, troop_level`. Written both from the Chests/Ancient public page (`POST /api/v1/chests/public/player-profile`) and from the Chests dashboard.
- **`AncientRoster`** — one row per roster player. Fully overwritten by each tournament import (except `troop_level`). Fields: `player_name` (effective name — raw OCR text, or canonical after a merge), `raw_ocr_name` (kept once physically merged), `place`, `points`, `troop_level`, `source` (`ocr`/`manual`/`chests`), `manual_expires_at` (TTL for manual rows), `rank`.
- **`AncientCalculation`** — calculation history, max 5 per collector. `strategy`, `summon_levels`, `amplification_coef`, `officer_count`/`veteran_count`, `total_quota_millions`, `result_json`.
- **`AncientNameMapping`** — leader-confirmed `raw_ocr_name → canonical_name` mapping (`confirmed: bool`).
- **`AncientInviteCode`** — one-time editor-invite codes (24h TTL).
- **`AncientEditor`** — active editor grants (30 days from grant/re-grant).

## 4. Server — leader dashboard (`server/ancients_dashboard.py`)

Key endpoints (`/web/dashboard/ancients`, site-session auth):

| Method + path | What it does |
|---|---|
| `GET /` | Full dashboard payload: own + editor-accessible collectors, roster, history, `canonical_sources`, hidden collectors |
| `PATCH /{slug}/ancient-visibility` | Hide/show (owner only) |
| `PATCH /{slug}/quota-thresholds` | Shortfall-highlight thresholds (owner only) |
| `PATCH /{slug}/troop-level`, `/rank` | Edit one row's troop composition/rank |
| `PATCH /{slug}/name-mappings` | Confirm a name mapping → triggers a physical row merge |
| `DELETE /{slug}/name-mappings/{raw}` | Remove an unconfirmed mapping (unavailable for already-merged rows — 🔒) |
| `DELETE /{slug}/roster/ocr-import` | "Clear" — wipe the last tournament import |
| `DELETE /{slug}/roster/{player_name}` | Remove one row entirely |
| `POST /{slug}/calculate` | Run the quota calculator (Strategy A/B) |
| `POST /{slug}/roster/manual` | Add a participant manually |
| `POST /{slug}/roster/populate-from-chests` | Mirror the roster from Chests |
| `POST /invite`, `POST /{slug}/invite` | Invite/accept editor access |

**How the roster is built (`_roster_rows`)** — three tiers of name resolution:
1. Already physically merged (`raw_ocr_name != player_name`) — name is final, shown with 🔒.
2. A confirmed-but-unmerged mapping exists — shows the suggested canonical name; the merge happens on next save.
3. Unmapped raw OCR name — fuzzy-matched (`difflib`, threshold adjustable 50-100%) against Chests' canonical names.

**Physical merge** — confirming a mapping merges two roster rows (one carrying troops/rank, the other place/points) into one, irreversibly (the "unlock" button disappears, replaced by 🔒) — otherwise it would become ambiguous which row's points belonged to whom.

**"Populate from Chests"** is a **mirror, not an additive merge**: the player list becomes an exact copy of the Chests list; every row without a Chests match (including manual entries for players not tracked in Chests) is deleted. The button requires two-step confirmation since the action is destructive.

**Manual add** — checks for exact-name duplicates and for similar Chests canonical names (fuzzy, 0.75 cutoff — prompts "is this the same player?"). A manual row's lifetime is until the end of the next "Trade Routes" event cycle (`next_trade_routes_end()`), unless confirmed sooner by a real tournament import or Chests sync.

**Editor invites** — a one-time 24h code redeems into a 30-day grant. An editor can edit troops/ranks/names/manual entries, but CANNOT run the calculator, change thresholds, hide the clan, or invite others.

**Quota calculation (`ancient_quota.py`):**
- Total quota = Σ HP of the Ancient levels farmed (`ANCIENT_LEVEL_HP` table, levels 81-250) × amplification coefficient.
- **Strategy A (by rank):** the quota splits between officers (`Глава/Старший/Офицер`) and veterans at a 1.0:0.5 ratio — an officer gets twice a veteran's quota.
- **Strategy B (by troop composition):** a player's weight = sum of `1.8^(tier-5)` across Ground/Siege/Mounted, divided by the clan's target preset weight (T5-T9, 3 max-tier troop types). Quota is proportional to weight. A player with no valid troop level is excluded from the split, without failing the whole request.

## 5. Server — public page (`server/ancients_public.py`)

One no-auth endpoint: `GET /api/v1/ancients/public/{slug}`.

Returns: `kingdom`, `clan`, `quota_thresholds`, `roster: [{player_name, rank, troop_level, points, quota, shortfall_pct}]`.

**Never exposes:** `raw_ocr_name`, `mapped_name`, `suggested_name`, `mapping_confirmed` — leader-only dashboard concerns, not public information. Internally, the endpoint still uses the confirmed-mapping table to compute the correct Strategy B quota (matching what the leader sees on the dashboard), but that lookup data never leaves the server.

**Writes** aren't a new endpoint: the public page reuses the existing `POST /api/v1/chests/public/player-profile` (same `PlayerProfile` table, same collector), with a 15-minute anti-flood cooldown per row.

## 6. Chests linkage — what's possible with or without it

**Clan WITHOUT Chests** — minimum viable path:
1. The leader manually adds players (`POST /roster/manual`) — no bot import, no Chests needed.
2. Runs the calculator (Strategy A only needs rank counts; Strategy B needs troop levels, which players can self-report).
3. Players visit `/ancients/{slug}` and self-report rank/troops via "Enter composition."
4. Works end-to-end — but manual entries expire at the next "Trade Routes" cycle end unless confirmed by a real tournament import; the leader must periodically re-add players if the clan never starts tracking Chests.

**Clan WITH Chests** — what it adds:
1. **Name canonicalization** — fuzzy-matching and duplicate detection for manual adds draw on the already-curated Chests name dictionary (`PlayerAlias`) instead of starting from zero.
2. **"Populate from Chests"** — instantly syncs the full member list in one click instead of adding every player by hand.
3. **Shared `PlayerProfile`** — any rank/troops a player already self-reported on the Chests public page (or the leader entered in the Chests dashboard) is automatically visible and used in Ancient — no re-entry needed.

## 7. Retention/cleanup (`server/ancient_retention.py`)

Two independent daily background ticks:
- **Hidden-collector purge** (60 days): if a collector has been hidden (`ancient_hidden_at` set) for 60+ days with no activity, ONLY the Ancient-specific tables (`AncientRoster`/`AncientNameMapping`/`AncientCalculation`/`AncientEditor`/`AncientInviteCode`) are deleted. Chests data, `PlayerAlias`, `PlayerProfile`, and the `ChestCollector` row itself are untouched. The timer resets on any Ancient activity (tournament import, quota calculation) while hidden — a still-actively-used hidden clan is never purged.
- **Manual-entry expiry** — independent of hide status: `source='manual'` rows past their `manual_expires_at` are deleted every tick.

## 8. Frontend routes

- `/dashboard/ancients` (auth required) → `AncientsPage.jsx` — calculator, roster, history, "How it works" tab.
- `/ancients/:slug` (no auth) → `PublicAncientsPage.jsx` — read-only view plus self-service edit mode for one's own rank/troops.
