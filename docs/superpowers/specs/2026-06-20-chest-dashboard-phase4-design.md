# Сундуки — Личный кабинет, Фаза 4 (per Gemini ТЗ, 2-я редакция)

Дата: 2026-06-20

> Заменяет `docs/superpowers/specs/2026-06-20-chest-aliases-dashboard-design.md` —
> та спека предполагала общий глобальный «Chest Catalog» (T5-T9) с очками, эта версия
> делает очки и состав паттерна **per-клан**, по новому ТЗ от Gemini
> (`docs/Входящие_Gemini.md`, 2026-06-20, вторая редакция).

## Контекст

Источник — прямое ТЗ от Gemini, владелец передал без изменений, с одной поправкой,
согласованной отдельно: пункт «Создать публичную таблицу» (автогенерация Google Sheet через
API) **заменён на обычную HTML-страницу на сайте** — сервис-аккаунт физически не может
создавать файлы в своём Google Drive (нулевая квота, см. память `feedback_google_sa_drive_quota`,
уже наступали на эти грабли в Фазе 2). Слаг у коллектора уже существует с момента первого
импорта сундуков — отдельная кнопка «создать» не нужна, публичная ссылка просто всегда есть.

## Архитектурное решение

### Новая модель `ChestConfiguration` (per-collector очки и состав)

```python
class ChestConfiguration(Base):
    __tablename__ = "chest_configurations"
    __table_args__ = (
        UniqueConstraint("collector_id", "catalog_id", name="uq_chest_config_collector_catalog"),
    )
    id            = Column(Integer, primary_key=True)
    collector_id  = Column(Integer, ForeignKey("chest_collectors.id"), nullable=False, index=True)
    catalog_id    = Column(String(200), nullable=False)
    custom_name   = Column(String(200), nullable=True)
    points        = Column(Integer, nullable=False, server_default=text("0"))
    is_in_pattern = Column(Boolean, nullable=False, server_default=text("false"))
```
Один ряд = один официальный сундук (`catalog_id`) для одного клана. Очки и факт включения
в подсчёт — **настройка клана**, не глобальный справочник. Можно создать этот ряд ДО того,
как бот хоть раз увидел этот сундук («Добавить сундук вручную»).

### `ChestTypeAlias` — упрощается до чистого маппинга

Убираем `custom_display_name` (переехало в `ChestConfiguration.custom_name`) и `enabled`
(переехало туда же как `is_in_pattern`, ровно тот же смысл — «считать или нет», просто
теперь это атрибут сундука для клана, а не атрибута конкретной OCR-строки):
```python
class ChestTypeAlias(Base):
    __tablename__ = "chest_type_aliases"
    __table_args__ = (
        UniqueConstraint("collector_id", "raw_type", name="uq_chest_type_aliases_raw_type"),
    )
    id            = Column(Integer, primary_key=True)
    collector_id  = Column(Integer, ForeignKey("chest_collectors.id"), nullable=False, index=True)
    raw_type      = Column(String(200), nullable=False)
    catalog_id    = Column(String(200), nullable=False)
```

### `ChestCollector` — поле для делегирования

Новое поле `management_token` (`String(32)`, nullable, unique) — генерируется по запросу
владельца коллектора, одноразовый предъявляемый код. Когда другой залогиненный пользователь
вводит этот код, его `user_id` записывается в `ChestCollector.user_id` (передача владения),
токен очищается (`NULL`) сразу после использования — одноразовый, не подписка на доступ.

### Миграция данных существующих коллекторов

Коллекторы с уже выставленным `pattern` (сейчас только 229/BERS, `T9`) — Alembic data-migration
переносит их текущие очки: `INSERT INTO chest_configurations (collector_id, catalog_id, points,
is_in_pattern) SELECT cc.id, ctc.canonical_type, ctc.points, true FROM chest_collectors cc JOIN
chest_type_catalog ctc ON ctc.pattern = cc.pattern WHERE cc.pattern IS NOT NULL` — чтобы
владелец не потерял уже настроенные T9-очки при переходе. Старые `ChestTypeCatalog`/
`ChestCollector.pattern` колонки/таблицы **не удаляются** (могут понадобиться, если хочешь
вручную свериться) — просто `summary` их больше не читает.

### Эндпоинты (`server/chest_dashboard.py`, новый файл, авторизация `get_web_user`)

**`GET /api/v1/web/dashboard/chests`** — для текущего пользователя, по каждому его коллектору:
```json
{
  "collectors": [{
    "slug": "...", "kingdom": "...", "clan": "...", "language": "ru",
    "public_url": "https://total-hunter.com/chests/<slug>",
    "rows": [
      {"raw_type": "Эпическая Араiiна", "catalog_id": "Epic Arachne",
       "custom_name": "Толстяк", "points": 40, "is_in_pattern": true},
      {"raw_type": null, "catalog_id": "Common Crypt 5",
       "custom_name": null, "points": 5, "is_in_pattern": true}
    ],
    "catalog_options": [{"catalog_id": "Epic Arachne", "label": "Эпическая Арахна"}, ...]
  }]
}
```
`rows` — FULL OUTER JOIN по `(collector_id, catalog_id)` между `ChestTypeAlias` и
`ChestConfiguration`: строки с алиасом, но без конфигурации (новый OCR, ещё не настроен) —
`points=0, is_in_pattern=false`, `custom_name=null`; строки с конфигурацией, но без алиаса
(добавлены вручную) — `raw_type=null`. Плюс отдельно raw-типы из `chests`, у которых вообще
нет `ChestTypeAlias` (`SELECT DISTINCT chest_type_raw FROM chests WHERE collector_id=? AND
chest_type_raw NOT IN (SELECT raw_type FROM chest_type_aliases WHERE collector_id=?)`) —
показываются с `catalog_id=null` (клиент пока не сопоставил).

**`POST /api/v1/web/dashboard/chests/rows`** — full-replace для коллектора текущего
пользователя (`403` если `collector.user_id != current_user.id`):
```json
{"collector_slug": "...", "rows": [
  {"raw_type": "Эпическая Араiiна", "catalog_id": "Epic Arachne",
   "custom_name": "Толстяк", "points": 40, "is_in_pattern": true},
  {"raw_type": null, "catalog_id": "Common Crypt 5",
   "custom_name": null, "points": 5, "is_in_pattern": true}
]}
```
Для каждой строки: если `raw_type` не `null` → upsert `ChestTypeAlias(raw_type, catalog_id)`;
если `catalog_id` не `null` → upsert `ChestConfiguration(catalog_id, custom_name, points,
is_in_pattern)`. `catalog_id` **обязателен хотя бы в одном месте на строку** (либо алиас,
либо конфигурация, либо оба — но не пустая строка без обоих) и обязан быть из известного
множества (`SELECT DISTINCT canonical_type FROM chest_type_catalog UNION SELECT DISTINCT
canonical_type FROM chest_localizations`) — `400` с понятным текстом, если нет (выбор из
dropdown на фронте, так что это сигнал поломки, не пользовательская ошибка).

**`POST /api/v1/web/dashboard/chests/management-token`** — генерирует `management_token`
для коллектора текущего пользователя, возвращает код.

**`POST /api/v1/web/dashboard/chests/claim`** — принимает `{"code": "..."}`, ищет коллектор
с этим `management_token`, если найден — `collector.user_id = current_user.id`,
`management_token = NULL`, иначе `404`.

**`PATCH /api/v1/web/dashboard/chests/{slug}/language`** — `{"language": "ru"}`, обновляет
`collector.language` (с проверкой владения).

### `GET /summary/{slug}` — переписывается на `ChestConfiguration`

```python
.join(ChestConfiguration,
      and_(ChestConfiguration.collector_id == Chest.collector_id,
           ChestConfiguration.catalog_id == chest_type_expr,
           ChestConfiguration.is_in_pattern.is_(True)))
```
вместо текущего `JOIN ChestTypeCatalog ... WHERE pattern == collector.pattern`.
`display_expr = COALESCE(ChestConfiguration.custom_name, ChestLocalization.display_text,
chest_type_expr)`. `points` берётся из `ChestConfiguration.points`, не из
`ChestTypeCatalog.points`. Безусловный (без `pattern IS NULL` ветки) — если у коллектора
нет ни одной строки `ChestConfiguration` с `is_in_pattern=true`, сводка просто пустая
(`grand_total: 0`), это корректное поведение для нового клана, который ещё не настроился.

### Публичная страница `total-hunter.com/chests/{slug}`

Новая страница `web/src/pages/ChestSummaryPage.jsx`, маршрут `/chests/:slug` (БЕЗ
`PrivateRoute`, без логина) — вызывает уже существующий публичный `GET
/api/v1/chests/summary/{slug}`, рисует таблицу игрок×тип×очки. Ссылка на неё показывается в
личном кабинете (`public_url` в ответе `GET .../chests`), отдельной кнопки «создать» не
нужно — слаг существует с первого импорта.

### Личный кабинет (`web/src/pages/ChestsPage.jsx`, маршрут `/dashboard/chests`)

Верхняя панель: язык клана (select), ссылка на публичную страницу, кнопка «Сгенерировать
код передачи» (показывает код в `alert`/модалке), поле + кнопка «Принять управление» (код).

Таблица, 5 колонок на каждый `row` из `GET .../chests`: сырой OCR (readonly, прочерк если
`null`) | официальный сундук (`<select>` из `catalog_options`) | своё название (текст) |
очки (`<input type=number>`) | в паттерне (checkbox). Кнопка «Добавить сундук вручную» —
добавляет в локальный стейт новую строку `{raw_type: null, catalog_id: null, ...}`, клиент
заполняет, жмёт «Сохранить» — весь массив строк уходит в `POST .../chests/rows`.

## Тестирование

- `server/tests/test_chest_dashboard.py` (новый): `GET` собирает 3 источника строк правильно
  (алиас+конфиг, только алиас, только конфиг); `POST` валидирует `catalog_id`, апсертит,
  отвергает чужой `collector_slug` (`403`); `management-token`/`claim` — генерация,
  одноразовость, `404` на неверный код; `language` — обновление с проверкой владения.
- `server/tests/test_chests.py` — переписать `summary`-тесты под `ChestConfiguration`
  вместо `ChestTypeCatalog`/`pattern`.
- `server/tests/test_chest_aliases.py` — обновить под упрощённый `ChestTypeAlias`
  (`catalog_id` вместо `canonical_type`, без `custom_display_name`/резолва — Фаза 3a удаляется
  полностью, админский Sheets-эндпойнт остаётся только для обратной совместимости синка
  `Player Aliases`, не для `Chest Aliases`).
- Alembic data-migration — тест на реальных текущих данных 229/BERS перед деплоем (ручная
  проверка, не автотест): после миграции `ChestConfiguration` должна содержать 18 строк T9
  с тем же `points`, что были в `ChestTypeCatalog`.

## Явно вне рамок

- Автогенерация Google Sheet через API — отклонено (квота сервис-аккаунта), заменено
  HTML-страницей.
- Самообслуживание `Player Aliases` (имена игроков) — не упомянуто в новом ТЗ Gemini,
  остаётся как было (Sheets, админ-эндпойнт), без изменений.
- Глобальный `Chest Catalog`/`Localizations` (Sheets владельца) — используется ТОЛЬКО как
  источник `catalog_options` (список + перевод для dropdown) и фоллбэк-перевода в `summary`;
  очки оттуда больше не читаются `summary`, но Sheets/скрипты не удаляются.
- Множественные коллекторы на одного пользователя в одном экране — `GET .../chests`
  возвращает список (`collectors: [...]`), но раскладка фронта на несколько коллекторов
  одновременно в одной вкладке — не детализирована, делаем по одной карточке на коллектор
  (естественное расширение существующей структуры ответа, не отдельная задача).
