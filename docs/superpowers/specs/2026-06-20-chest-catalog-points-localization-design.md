# Сундуки — глобальный каталог очков, паттерны и мультиязычная локализация (Фаза 2)

Дата: 2026-06-20

## Контекст

Алиасы (`docs/superpowers/specs/2026-06-20-chest-aliases-admin-sheet-design.md`) задеплоены
и живо проверены. Следующий шаг, отложенный туда же — "Очки/Паттерны (T5-T9) и
`chest_type_catalog`" — теперь раскрыт владельцем через реальную рабочую Google Sheet
(`1CvfVs4cWUr4EXs7e8uKi2wbT-sQ_gYSIWDw3oJ0Xo64`, вкладка «Сундуки»): пример лидерборда
(Игрок/Очки/Сундуки), таблица «сундук → очки» для паттерна Т9 (18 строк), текстовые
описания паттернов Т5-Т9, и справочный список 138 английских названий всех известных типов
сундуков в игре.

Параллельно выяснилось ключевое архитектурное ограничение: бот работает на 20+ языках
клиента игры, будущие сборщики (кланы) будут на китайском и других языках — поэтому
канонизация сундуков не может оставаться "на языке этого конкретного клана", иначе очки/
каталог придётся дублировать под каждый язык.

Вкладка «Древний» в этой же Sheet — про другое (тайм-ивент + отдельная подсистема
распределения нормы урона по весам) и явно отложена владельцем на будущую Фазу 3, см.
[[project_chest_events_phase2]] в памяти. Не часть этой спеки.

## Решённые архитектурные вопросы

- **English is the Core.** `ChestTypeAlias.canonical_type` (поле уже существует, схема не
  меняется) теперь обязан быть английским именем из эталонного списка 138 сундуков, а не
  текстом на языке конкретного клана. Это единый язык-независимый идентификатор сундука
  во всей системе. Существующие тестовые алиасы коллектора `m00bqgjcl1xqUHRDvEa8bQ`
  (`"Machet"→"MACHETE"`, `"Эпический отр"→"Эпический отряд"`) были тестовыми данными для
  проверки прошлой фичи — владелец перезаполнит лист «Chest Aliases» правильными
  английскими canonical-именами, это не код-миграция.
- **Паттерн — константа на весь клан, не вычисляется по игроку.** `ChestCollector` получает
  новое поле `pattern` (nullable string, напр. `"T9"`), которое **админ выставляет вручную**
  для каждого клана. Один клан = один паттерн. Сейчас реален только Т9 (18 сундуков),
  остальные 4 (Т5-Т8) — пустые текстовые описания без данных, заполнятся по мере появления
  кланов на этих паттернах (вне рамок этой спеки).
- **Язык отображения — тоже константа на клан**, не выводится автоматически из языка GUI
  бота. `ChestCollector` получает новое поле `language` (nullable string, напр. `"ru"`),
  которое **админ выставляет вручную**, как и `pattern`.
- **Каталог и локализация — глобальные таблицы**, общие для всех кланов и языков, не
  per-collector. Одна запись очков на (сундук, паттерн), одна запись перевода на (сундук,
  язык) — не дублируется для каждого нового клана.
- **Полная фильтрация по каталогу в `summary`.** Если у коллектора задан `pattern`, то
  ТОЛЬКО сундуки, присутствующие в `chest_type_catalog` для этого паттерна, попадают в
  ответ — ни в очки, ни в счётчик «всего сундуков», ни в список вообще. Внеформатные
  сундуки (которые игрок принёс, но они не входят в каталог паттерна) **полностью
  исключаются** — это касается и игроков, которые принесли только внеформатные сундуки: они
  не появляются в лидерборде совсем. Если `pattern` у коллектора не задан (`NULL`) —
  поведение как сейчас (без фильтра, без очков) — обратная совместимость для коллекторов,
  которым паттерн ещё не назначили.
- **Sheet остаётся простым** — без таблиц "впрок". Не делаем widе-таблицу с колонками
  Т5-Т9 (паттерн — не измерение для выбора в момент чтения, это константа клана) и не
  делаем widе-таблицу с 20 языковыми колонками. Три новые вкладки, по 2 колонки каждая:
  «Chest Catalog» (английское имя → очки, сейчас заполнена только для Т9), «Localizations»
  (английское имя → русский перевод, сейчас заполнен только `ru`), «Collector Settings»
  (slug → pattern, language). Когда понадобится другой паттерн/язык — добавляется такая
  же простая отдельная таблица, а не ретрофит существующей.
- **`pattern`/`language` коллектора передаются через уже существующий
  `POST /api/v1/chests/aliases/import`** (два новых опциональных поля), а не через новый
  4-й эндпоинт — минимизация количества admin-эндпойнтов.
- **Алиасы НЕ меняют свой механизм** — `PlayerAlias` (имена игроков) полностью без
  изменений, языковая привязка там не нужна (имя — собственное, не переводится). Только
  `ChestTypeAlias.canonical_type` меняет конвенцию заполнения.
- **Миграция Alembic.** В репозитории сейчас 3 несведённые "головы" (`h7c8e9s0t1c2`,
  `g3h4i5j6k7l8`, `22864ea6408d`) — это старая неприменённая ветка (см.
  [[project_gcloud_local_access]] и историю STATE.md про "p1q2r3s4t5u6 фиктивный merge").
  Реально на проде применена только `h7c8e9s0t1c2` (подтверждено `psql`). Новая миграция
  идёт от неё (`down_revision='h7c8e9s0t1c2'`), деплоится **явной ревизией**
  (`alembic upgrade <новая_ревизия>`), не `alembic upgrade head` — иначе упрёмся в
  ambiguity по трём головам. Не наша задача чинить старые ветки в рамках этой спеки.

## Модель данных

```python
# models.py — изменение существующей ChestCollector
class ChestCollector(Base):
    ...
    pattern  = Column(String(8),  nullable=True)   # "T5".."T9", NULL = ещё не назначен
    language = Column(String(8),  nullable=True)   # "ru", "uk", "zh", ... NULL = не назначен

# models.py — новые глобальные таблицы
class ChestTypeCatalog(Base):
    __tablename__ = "chest_type_catalog"
    __table_args__ = (
        UniqueConstraint("canonical_type", "pattern", name="uq_chest_catalog_type_pattern"),
    )
    id             = Column(Integer, primary_key=True)
    canonical_type = Column(String(200), nullable=False)   # английское имя из списка 138
    pattern        = Column(String(8),   nullable=False)   # "T5".."T9"
    points         = Column(Integer,     nullable=False)

class ChestLocalization(Base):
    __tablename__ = "chest_localizations"
    __table_args__ = (
        UniqueConstraint("canonical_type", "language", name="uq_chest_localizations_type_lang"),
    )
    id             = Column(Integer, primary_key=True)
    canonical_type = Column(String(200), nullable=False)
    language       = Column(String(8),   nullable=False)
    display_text   = Column(String(200), nullable=False)
```

## API

### `POST /api/v1/chests/catalog/import` (новый, `server/chest_catalog.py`)

Auth: Bearer `$ADMIN_TOKEN` (паттерн `chest_aliases.py`: `HTTPBearer(auto_error=False)` +
явная проверка `creds is None`, а не bare `HTTPBearer()` как в `clan.py` — фиксируем
правильный паттерн сразу, не повторяем известный 401-вместо-403 баг,
см. [[project_clan_auth_401_gap]]).

```json
{"entries": [{"canonical_type": "Common Crypt 25", "pattern": "T9", "points": 5}]}
```
Полная замена ВСЕЙ таблицы `chest_type_catalog` (не per-pattern) при каждом вызове —
Sheet полностью описывает каталог целиком. Ответ `200 {"ok": true, "count": <int>}`.

### `POST /api/v1/chests/localizations/import` (новый, `server/chest_catalog.py`)

Auth: тот же паттерн.
```json
{"entries": [{"canonical_type": "Common Crypt 25", "language": "ru", "display_text": "Склеп 25 уровня"}]}
```
Полная замена ВСЕЙ таблицы `chest_localizations`. Ответ `200 {"ok": true, "count": <int>}`.

### `POST /api/v1/chests/aliases/import` (изменение существующего, `server/chest_aliases.py`)

`AliasImportPayload` получает два новых опциональных поля:
```python
class AliasImportPayload(BaseModel):
    collector_slug: str
    player_aliases: List[PlayerAliasIn] = []
    chest_aliases: List[ChestAliasIn] = []
    pattern: Optional[str] = None
    language: Optional[str] = None
```
Если `pattern`/`language` присутствуют (не `None`) — обновляют соответствующие поля
найденного `ChestCollector`. Остальная логика (full-replace алиасов) не меняется.

### `GET /api/v1/chests/summary/{slug}` (изменение существующего, `server/chests.py`)

Если `collector.pattern is None` — текущее поведение без изменений (полный LEFT JOIN с
алиасами, без очков, без фильтрации).

Если `collector.pattern` задан:
```sql
SELECT coalesce(loc.display_text, c.alias_canonical_type) AS display_name,
       coalesce(pa.canonical_name, ch.sender_raw)          AS sender,
       cat.points,
       count(*)
FROM chests ch
JOIN <alias-join, как сейчас, дающий canonical_type>  -- INNER, не LEFT
JOIN chest_type_catalog cat
  ON cat.canonical_type = <canonical_type> AND cat.pattern = :collector_pattern
LEFT JOIN chest_localizations loc
  ON loc.canonical_type = <canonical_type> AND loc.language = :collector_language
LEFT JOIN player_aliases pa ON ... (как сейчас)
WHERE ch.collector_id = :id
GROUP BY ...
```
Ключевая разница от текущей реализации — JOIN с `chest_type_catalog` **INNER**, не
`OUTER`: строки сундука, для которого нет записи в каталоге для текущего паттерна клана,
не попадают в результат вообще (ни в `chest_types`, ни в `players`, ни в `totals`).

Ответ:
```json
{
  "kingdom": "...", "clan": "...",
  "chest_types": ["Склеп 25 уровня", "..."],
  "players": [{"name": "Иванов", "counts": {"Склеп 25 уровня": 12}, "total": 300, "points": 4200}],
  "totals": {"Склеп 25 уровня": 340, "...": 0, "grand_total": 3852, "total_points": 58000}
}
```
`name`/`chest_types` — локализованные тексты (фолбэк на `canonical_type`, если перевода
для `collector.language` нет). `total`/`grand_total` — теперь сумма ТОЛЬКО по каталожным
типам (не всех сундуков игрока, как раньше). `points`/`total_points` — новые поля.

## Sheet — финальная структура (3 новые вкладки + изменение существующей)

- **«Chest Catalog»**: `Canonical Type (EN) | Points` — 18 строк сейчас, всё под T9
  (явный заголовок-комментарий в листе "Pattern: T9").
- **«Localizations»**: `Canonical Type (EN) | RU` — 18 строк сейчас (та же 18, что в
  каталоге; перевод нужен только для сундуков, которые реально считаются).
- **«Collector Settings»**: `Collector Slug | Pattern | Language` — одна строка на клан,
  сейчас одна строка: `m00bqgjcl1xqUHRDvEa8bQ | T9 | ru`.
- Старая вкладка «Сундуки» (пример лидерборда + перемешанные K:L данные) — становится
  неактуальной, владелец может очистить/архивировать после переноса. Не часть кода,
  ручное действие владельца.

## Итоговая таблица (`export_chests_to_sheet.py`, изменение существующего)

Новый формат строки: `Игрок | Очки | Всего сундуков | [18 колонок — по одной на каждый
canonical_type из ответа `chest_types`, локализованное имя как заголовок]`. Источник
данных не меняется (тот же `GET /summary/{slug}`), меняется только `build_rows()` —
вставляет `player["points"]` и `player["total"]` сразу после имени, перед разбивкой по
`counts`.

## Тестирование

- `server/tests/test_chest_catalog.py` (новый): 403 без токена/с неверным токеном для
  обоих новых эндпойнтов, full-replace заменяет старые записи, пустой список очищает
  таблицу.
- `server/tests/test_chests.py`: новый тест — коллектор с `pattern="T9"`, каталог с 2
  типами из 3 принесённых игроком → в ответе только 2 типа, `total`/`grand_total`
  не включают третий (внеформатный) тип, `points` считаются верно. Отдельный тест — игрок,
  принёсший ТОЛЬКО внеформатный сундук, отсутствует в `players` совсем. Отдельный тест —
  `pattern=None` → старое поведение (обратная совместимость).
- `server/tests/test_chest_aliases.py`: новый тест на `pattern`/`language` в payload
  обновляют `ChestCollector`.

## Известная неопределённость — требует проверки владельцем перед заполнением Sheet

Часть из 18 текущих русских названий в старой K:L таблице неоднозначно соответствуют
английскому списку 138 (например, «Темные предзнаменования» может соответствовать любому
из 6 разных "Dark Omens..." вариантов в списке). Точное сопоставление RU→EN для всех 18
записей — ручная задача владельца при заполнении новой вкладки «Chest Catalog», не
угадывается кодом или этой спекой.

## Явно вне рамок

- Паттерны Т5-Т8 и другие языки — таблицы создаются по той же простой схеме, когда
  появятся реальные кланы на них. Не строим заранее.
- Тайм-ивенты (Древний, Dark Omens Event и т.п.) и подсистема распределения нормы урона —
  Фаза 3, см. [[project_chest_events_phase2]].
- Веб-страница на сайте — отдельная будущая спека (как и раньше).
- Валидация `canonical_type` на принадлежность списку 138 — не делаем, админ
  ответственен за корректность ввода (как и существующие алиасы сейчас).
