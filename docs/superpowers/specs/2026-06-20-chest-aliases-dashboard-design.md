# Сундуки — Личный кабинет: явный выбор сундука вместо угадывания (Фаза 4)

Дата: 2026-06-20

## Контекст

Фаза 3a (резолв родного языка → английский ID через обратный поиск по `ChestLocalization`)
оказалась тупиком на живых данных: владелец вводит произвольный сленг («Толстяк» вместо
«Epic Undead»), система не может его угадать, и либо блокирует весь импорт (первая версия),
либо тихо теряет очки (вторая версия, после того как владелец потребовал не блокировать).
Источник: `docs/Входящие_Gemini.md` (2026-06-20) — Gemini предложил отказаться от угадывания
текста и заменить его явным выбором из списка на UI. Полностью согласен, реализуем как описано.

**Ключевая мысль:** компьютер не обязан понимать сленг — пусть клиент явно укажет, какой
официальный сундук он имеет в виду, через выпадающий список (на его языке), а подпись для
своего клана пишет отдельно, по желанию.

## Архитектурное решение

### Схема данных — `ChestTypeAlias`

- `canonical_type` → переименовать в **`catalog_id`** (по смыслу не меняется: всё ещё
  английский ID, всё ещё ключ для `ChestTypeCatalog`/`ChestLocalization`; переименование —
  чтобы явно отличать от `custom_display_name`, который раньше путали с тем же полем).
- Новая колонка **`custom_display_name`** (`String(200)`, `nullable=True`) — свободный текст
  клана, опционально. Если `NULL` — показываем перевод из `ChestLocalization`.
- Alembic-миграция: `ALTER TABLE chest_type_aliases RENAME COLUMN canonical_type TO
  catalog_id; ALTER TABLE chest_type_aliases ADD COLUMN custom_display_name VARCHAR(200)
  NULL;` — без трансформации данных. Существующие строки (включая внесённый сегодня мусор
  типа «Толстяк», «Рой Арахны») переедут как есть в `catalog_id` — они и сейчас не совпадают
  с каталогом, поведение не меняется к худшему; владелец переразметит их через новый UI.

### Эндпоинты — Личный кабинет (`server/web_routes.py` или новый `server/chest_dashboard.py`)

Авторизация — **обычная сессия пользователя** (`Depends(get_web_user)`, JWT Bearer, как у
`/web/balance`, `/web/devices` и т.д.) — никакого `ADMIN_TOKEN`, никаких Google Sheets.

**`GET /api/v1/web/dashboard/chests`** — возвращает для коллектора(ов) текущего пользователя:
```json
{
  "collectors": [{
    "slug": "...", "kingdom": "...", "clan": "...", "pattern": "T9", "language": "ru",
    "raw_types": [
      {"raw_type": "Эпическая Араiiна", "catalog_id": null, "custom_display_name": null, "enabled": true},
      {"raw_type": "Exon", "catalog_id": "Yogwai", "custom_display_name": null, "enabled": true}
    ],
    "catalog_options": [
      {"catalog_id": "Epic Arachne", "label": "Эпическая Арахна"},
      {"catalog_id": "Yogwai", "label": "Ёкай"}
    ]
  }]
}
```
- `raw_types` — `SELECT DISTINCT chest_type_raw FROM chests WHERE collector_id=?` LEFT JOIN
  текущим `ChestTypeAlias` (если уже сопоставлено — отдаёт текущий `catalog_id`/имя).
- `catalog_options` — список для выпадающего списка: `SELECT DISTINCT canonical_type FROM
  chest_type_catalog UNION SELECT DISTINCT canonical_type FROM chest_localizations`, `label`
  — перевод из `ChestLocalization` для `collector.language` (`COALESCE(display_text,
  catalog_id)` если перевода нет). Сортировка по `label`. **Не фильтруется по паттерну** —
  паттерн влияет только на очки, не на состав списка сундуков.

**`POST /api/v1/web/dashboard/chests/aliases`** — full-replace для коллектора(ов) ТЕКУЩЕГО
пользователя (проверка `collector.user_id == current_user.id`, иначе `403`):
```json
{"collector_slug": "...", "aliases": [
  {"raw_type": "Эпическая Араiiна", "catalog_id": "Epic Arachne", "custom_display_name": "Толстяк", "enabled": true}
]}
```
- `catalog_id` **обязателен и проверяется** на принадлежность множеству известных ID
  (`chest_type_catalog` ∪ `chest_localizations`) — раз пользователь выбирает из выпадающего
  списка, а не печатает текст, невалидный `catalog_id` означает поломку фронта/чужой запрос,
  не пользовательскую ошибку → `400` с понятным текстом, без попытки угадать.
- `custom_display_name` — опционален, не валидируется (любой текст клана).
- Никакого резолва текста — вся логика `_resolve_chest_aliases`/`_resolve_one`
  (`server/chest_aliases.py`, Фаза 3a) **удаляется**: явный выбор делает её ненужной.
- Существующий админский `POST /api/v1/chests/aliases/import` (ADMIN_TOKEN, Google Sheets)
  не трогаем — он остаётся механизмом для глобального каталога/локализаций владельца
  (`Chest Catalog`/`Localizations` листы), но больше не предполагается для per-клановых
  алиасов клиентов. Player Aliases пока остаются через тот же старый Sheet-путь — вне рамок
  этой спеки (не упомянуты в ТЗ Gemini, его пример касался только типов сундуков).

### Изменение `GET /summary/{slug}` (`server/chests.py`)

- `chest_type_expr` теперь читает `ChestTypeAlias.catalog_id` (переименованная колонка) —
  без изменения семантики JOIN с `ChestTypeCatalog`/`ChestLocalization` (всё ещё `catalog_id`
  ↔ `canonical_type` тех таблиц, имена столбцов в них не меняются).
- `display_expr` меняется с `COALESCE(ChestLocalization.display_text, chest_type_expr)` на
  `COALESCE(ChestTypeAlias.custom_display_name, ChestLocalization.display_text,
  chest_type_expr)` — приоритет: своё имя клана → перевод → сырой текст (если вообще не
  размечено).
- **Известное ограничение (принимается, не блокирует):** если два разных `raw_type`
  размечены на один `catalog_id`, но с разными `custom_display_name` — в сводке они дадут
  ДВЕ отдельные строки (группировка всё ещё по `display_expr`), а не одну объединённую.
  Сумма очков корректна в любом случае (считается по `catalog_id`, не по отображаемому
  имени) — ломается только красота группировки в редком edge-case. Не в рамках этой фазы.

### Frontend (`web/src/pages/`)

- Новая страница `ChestsPage.jsx`, маршрут `/dashboard/chests` (рядом с `balance`/`devices`
  в `App.jsx`, `PrivateRoute`).
- Таблица 3 колонки на каждый `raw_type`: сырой текст (readonly) | `<select>` с
  `catalog_options` (label на языке клиента, value = `catalog_id`) | текстовое поле
  `custom_display_name`. Кнопка «Сохранить» — `POST .../aliases` с полным списком строк.
- Если у коллектора `language` не задан — выпадающий список показывает английские `label`
  (fallback `catalog_id` как label, раз перевода ещё нет) — это уже учтено форматом ответа
  `GET .../chests` (label = `COALESCE(display_text, catalog_id)`).

## Тестирование

- `server/tests/test_chest_dashboard.py` (новый): `GET` отдаёт только коллекторы текущего
  user_id, `catalog_options` отсортированы и переведены; `POST` отвергает `catalog_id` не из
  известного множества (`400`), отвергает чужой `collector_slug` (`403`), full-replace
  работает аналогично админскому импорту, `custom_display_name` сохраняется и участвует в
  `display_expr` при следующем вызове `summary`.
- `server/tests/test_chests.py` — обновить существующие тесты `summary` под переименование
  `canonical_type` → `catalog_id` и добавить случай с `custom_display_name`.
- `server/tests/test_chest_aliases.py` — удалить тесты резолва текста (Фаза 3a, больше не
  существуют: `_resolve_one`, `_resolve_chest_aliases`, литерал-фоллбэк); оставить тесты на
  full-replace/auth/pattern-language (переименовать поля в payload/assertions под
  `catalog_id`).

## Явно вне рамок

- Самообслуживание `Player Aliases` (имена игроков) — Gemini не упомянул, оставляем
  Sheets-путь как есть, отдельная будущая фаза если понадобится.
- Самообслуживание глобального каталога/переводов (`Chest Catalog`/`Localizations`) —
  остаётся Sheets + `sync_catalog_to_db.py`, подтверждено явно в разговоре с владельцем.
- UI для выбора `pattern`/`language` коллектора в личном кабинете — не оговорено в ТЗ
  Gemini; пока остаётся как сейчас (владелец ставит вручную через старый админ-эндпоинт
  `pattern`/`language` в `AliasImportPayload`, который не трогаем).
- Публичная страница `/chests/{slug}` на сайте — отдельная, ранее начатая, не завершённая
  спека (см. память `project_chest_catalog_next_steps`), не входит в эту фазу.
