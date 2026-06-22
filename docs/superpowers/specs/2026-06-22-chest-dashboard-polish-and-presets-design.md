# Сундуки — мелкие правки кабинета/публичной страницы + Пресеты (T9/T8...)

Дата: 2026-06-22

## Контекст

После Фазы 4 (личный кабинет `/dashboard/chests`) и геймификации сезона (Спеки 1-3, 2026-06-21/22)
владелец клана 229/BERS прошёл живой тест интерфейса и сформулировал ряд мелких UX-правок плюс
запрос на новую фичу — пресеты очков (готовые шаблоны "T9", "T8" и т.д.).

## Группа A — мелкие правки (без изменения схемы БД)

### A1. Кабинет — колонка raw_type не должна показывать «—», когда есть название

**Где:** `web/src/pages/ChestsPage.jsx`, таблица сундуков, первая колонка (сейчас `{row.raw_type || '—'}`).

**Было:** если `raw_type` пуст (строка добавлена вручную через «Добавить строку» и привязана к
каталогу без живого OCR-текста), колонка показывает голый «—», что выглядит как пропуск среди
остальных подписанных строк.

**Будет:** колонка показывает первое непустое из: `raw_type` → `custom_name` → `label` каталожной
записи по `catalog_id` (из `collector.catalog_options`) → иначе `—` (только для совсем пустой,
только что добавленной строки без каталога).

Реализуется на фронтенде (чистая функция `displayName(row, catalogOptions)`), без изменений
backend — `_collector_rows` уже отдаёт всё нужное (`raw_type`, `custom_name`, `catalog_id`),
а `catalog_options` уже приходит в ответе `GET /web/dashboard/chests`.

### A2. Публичная страница — закреплённый заголовок + верхний скроллбар

**Где:** `web/src/pages/ChestSummaryPage.jsx` + `web/src/styles/*.css` (таблица `.public-table`,
обёртка `.public-table-wrap`).

- `thead` таблицы получает `position: sticky; top: 0` внутри `.public-table-wrap` (вертикальный
  скролл уже есть из Спеки 3 — закреплены первые 2 колонки по горизонтали, по вертикали `thead`
  сейчас не закреплён).
- Над таблицей добавляется второй горизонтальный скроллбар-зеркало (тонкий div с тем же
  `scrollWidth`, синхронизированный с основным через `onScroll` обоих элементов в обе стороны) —
  тот же приём, что и для нижнего скроллбара, который уже есть благодаря `overflow-x: auto` на
  `.public-table-wrap`.

Чисто CSS/JS на фронтенде, backend не трогаем.

### A3. Публичная страница — явные даты периода рядом с таймером

**Где:** `web/src/pages/ChestSummaryPage.jsx`, блок `.public-season-info` (сейчас там бейдж цели,
бейдж часового пояса и `<CountdownTimer>`).

Добавляется ещё один бейдж с явными датами начала/конца периода, отрендеренными в часовом поясе
клана (`data.period_start`/`data.period_end` + `data.timezone_offset_minutes`, те же поля, что уже
используются в `formatRemaining`). Формат: `01.07 00:00 – 14.07 23:59 (UTC+03:00)`. Если
`period_start` не задан — бейдж не показывается (как и весь season-блок при отсутствии сезона).

Backend уже отдаёт `period_start`/`period_end`/`timezone_offset_minutes` в `GET /chests/summary/{slug}`
(Спека 2) — изменений backend не требуется.

### A4. Кабинет — колонка «Итого собрано» (за всё время, без учёта пресета/квоты)

**Где:** backend `server/chest_dashboard.py` (`_collector_rows`), frontend `ChestsPage.jsx`
(новая колонка `<th>` в конце таблицы сундуков).

**Семантика:** для каждой строки таблицы — сколько сундуков этого типа суммарно собрано кланом за
всё время, **независимо** от `is_in_pattern`/`counts_toward_quota` (то есть число не меняется при
переключении тоглов — это справочная метрика "сколько всего принесли").

**Подсчёт:**
- Для строки с `catalog_id` — сумма по ВСЕМ `raw_type`, алиасы которых (`ChestTypeAlias`) ведут на
  этот `catalog_id` у данного коллектора (может быть несколько raw-вариантов → один catalog_id, как
  уже бывает, см. фикс дубликатов 2026-06-22).
- Для строки без `catalog_id` (чистый необработанный `raw_type`) — просто `COUNT(*)` сундуков с этим
  `chest_type_raw` у коллектора.

**Реализация:** в `_collector_rows` — один доп. запрос
`SELECT chest_type_raw, COUNT(*) FROM chests WHERE collector_id=... GROUP BY chest_type_raw`,
строится словарь `raw_type -> count`; для строк с `catalog_id` суммируются counts всех
`alias.raw_type`, у которых `alias.catalog_id == row.catalog_id` (используя уже загруженный список
`aliases`). Новое поле в ответе строки: `total_ever: int`.

Тесты (TDD, `server/tests/test_chests.py`): новый тест проверяет, что `total_ever` суммируется по
нескольким raw-алиасам на один catalog_id и не зависит от `is_in_pattern`/`counts_toward_quota`.

## Группа B — Пресеты (T9, T8, ...)

### Модель

Пресеты — **глобальные готовые шаблоны**, не привязаны к пользователю/клану, не редактируются через
UI. Задаются и обновляются мной (Claude) по запросу владельца как статический список в коде:

```python
# server/chest_dashboard.py (или отдельный модуль chest_presets.py)
CHEST_PRESETS = {
    "T9": [
        {"catalog_id": "Epic Crypt 35", "points": 135, "is_in_pattern": True},
        {"catalog_id": "Epic Crypt 30", "points": 80, "is_in_pattern": True},
        {"catalog_id": "Rare Crypt 30", "points": 65, "is_in_pattern": True},
        {"catalog_id": "Epic Shadow City", "points": 55, "is_in_pattern": True},
        {"catalog_id": "Epic Crypt 25", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Dark Omens Chest", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Epic Briareus", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Epic Arachne", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Elven Citadel 30", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Yogwai", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Epic Fire Hydra", "points": 30, "is_in_pattern": True},
        {"catalog_id": "Epic Basilisk", "points": 30, "is_in_pattern": True},
        {"catalog_id": "Epic Undead", "points": 25, "is_in_pattern": True},
        {"catalog_id": "Epic Chimera", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Rare Crypt 25", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Epic Hellforge", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Common Crypt 25", "points": 5, "is_in_pattern": True},
        {"catalog_id": "Epic Jormungander", "points": 5, "is_in_pattern": True},
        {"catalog_id": "Epic Fenrir", "points": 5, "is_in_pattern": True},
    ],
}
```

Значения T9 взяты живыми (`psql` на проде) из текущих `ChestConfiguration` клана 229/BERS — это
их реальная рабочая настройка, использована как образцовый шаблон. Все каталожные типы, не
перечисленные в пресете, трактуются как `points=0, is_in_pattern=False` (то есть подразумевается,
что пресет явно перечисляет только то, что входит в зачёт — остальное приложение обнулит при
загрузке, см. ниже).

**T8 и другие уровни — вне рамок этого спринта.** Добавляются позже тем же механизмом (новый ключ
в `CHEST_PRESETS`), без изменений схемы/API — чисто данные.

### API

Новый эндпоинт:

```
GET /web/dashboard/chests/presets
→ {"T9": [{"catalog_id", "points", "is_in_pattern"}, ...]}
```

Авторизация — та же сессия (`get_web_user`), как и остальные `/web/dashboard/chests/*` эндпоинты
(presets не зависят от клана, но эндпоинт держим в той же auth-зоне ради консистентности роутера).

### UI

В кабинете, над таблицей сундуков — выпадающий список доступных пресетов + кнопка «Загрузить
пресет». При нажатии:

1. Фронтенд берёт `CHEST_PRESETS[name]` (загруженный один раз при открытии страницы).
2. Для каждого элемента пресета: если в текущем (несохранённом) состоянии `rowsByCollector[slug]`
   уже есть строка с этим `catalog_id` — обновляются её `points`/`is_in_pattern` на месте
   (`raw_type`/`custom_name` не трогаются). Если строки с этим `catalog_id` нет — добавляется новая
   строка `{raw_type: null, catalog_id, custom_name: null, points, is_in_pattern, counts_toward_quota: false}`.
3. Catalog-типы, которых нет в самом пресете, не трогаются (загрузка пресета не обнуляет то, что
   не упомянуто — только проставляет/обновляет перечисленное).
4. Изменения только в локальном состоянии React — ничего не уходит на сервер, пока клан не нажмёт
   обычную кнопку «Сохранить» (`save(slug)`, уже существует).

Это значит: загрузка пресета — чисто клиентская операция предзаполнения формы, никакого нового
эндпоинта сохранения не требуется, конфликтов идемпотентности/гонок нет.

### Переименование

Лейбл колонки/тоггла `is_in_pattern` — «В паттерне» → «В пресете» (только текстовая строка в
`dashboard_content.js`/`dashboard_content.en.js`, RU/EN). Само поле `is_in_pattern` в БД/API не
переименовывается (слишком большой бесполезный рефакторинг ради подписи).

## Вне рамок

- Сохранение клановых пресетов (своих именованных шаблонов) — явно отклонено владельцем, пресеты
  только глобальные/готовые.
- T8 и другие уровни — данные придут позже, добавляются тривиально через тот же `CHEST_PRESETS`.
- Любые изменения схемы `ChestConfiguration`/`ChestTypeAlias` — не требуются, вся фича B —
  чтение статического словаря + клиентский merge в существующую форму.

## Тестирование

- Backend (TDD): `test_chests.py` — новый тест на `total_ever` (A4, суммирование по нескольким
  алиасам на один catalog_id, независимость от тоглов) + тест на `GET .../presets` (содержит "T9",
  непустой список, валидная структура).
- Frontend: ручная проверка в браузере (нет фронтенд-тестов в проекте) — загрузка пресета T9,
  сохранение, отображение колонки «Итого собрано», sticky-заголовок и верхний скроллбар на
  публичной странице, отображение дат периода.
