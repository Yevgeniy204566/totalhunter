# Сундуки — управление алиасами через Google Sheets («Админская таблица», часть 1)

Дата: 2026-06-20

## Контекст

`GET /api/v1/chests/summary/{slug}` (см. `docs/superpowers/specs/2026-06-20-chests-summary-export-design.md`)
живой, владелец проверил живой прогон (103 игрока, 3852 сундука, коллектор
`m00bqgjcl1xqUHRDvEa8bQ`). Глядя на реальные данные обнаружились дубли из-за OCR-ошибок
(обрывки имён игроков и названий сундуков) — уже существующий механизм `PlayerAlias`/
`ChestTypeAlias` умеет это исправлять, но редактировать их сейчас можно только прямым
INSERT в БД, без UI.

Gemini (`docs/Входящие_Gemini.md`, 2026-06-20) предложил «Админскую таблицу» в Google
Sheets как UI для редактирования алиасов + глобальный каталог сундуков с очками + систему
паттернов T5-T9. Это три разные подсистемы. Эта спека покрывает **только алиасы**
(Player Aliases + Chest Aliases). Каталог очков и паттерны T5-T9 — отдельная будущая спека,
после того как алиасы уже чистят данные (см. `project_chest_history_2week_cycles.md` в
памяти — там это уже было предвидено).

## Решённые архитектурные вопросы

- **Алиасы применяются на чтении (в `summary`), не на записи (при импорте).** Сейчас
  `chest_type_canonical`/`sender_canonical` высчитываются один раз при импорте и навечно
  записываются в строку `chests` — новый алиас не подхватывает старые записи без
  переимпорта. Меняем `GET /summary/{slug}` на `LEFT JOIN` с `player_aliases`/
  `chest_type_aliases` и `COALESCE(canonical, raw)` — один SQL-запрос, агрегация всё ещё
  на стороне БД (не в Python), новый алиас сразу исправляет всю историю. Существующие
  `chest_type_canonical`/`sender_canonical` в таблице `chests` НЕ удаляются и не
  трогаются (становятся неиспользуемым снимком на момент импорта) — `import_chests`
  не меняется в этой работе.
- **Один Google Sheet, новые листы.** Используем уже существующий Sheet
  (`1EjUF5TIj3gAD4kv-XYYoQMKTHqOVn7OySYumAtNukug`, создан для экспорта сводки) — добавляем
  два новых листа: «Player Aliases» (`Raw Name | Canonical Name`) и «Chest Aliases»
  (`Raw Type | Canonical Type`). Один файл на коллектора — сводка для чтения, два листа для
  правки.
- **Auth — Bearer `$ADMIN_TOKEN`**, тот же токен и тот же паттерн, что уже в `server/clan.py`
  (`_require_auth` через `HTTPBearer` + сравнение с `os.getenv("ADMIN_TOKEN")`). Не
  hwid-based (это не действие рядового пользователя бота, а админское редактирование).
- **Полная замена алиасов коллектора при каждой синхронизации**, не инкрементальный upsert.
  Лист — источник правды (симметрично направлению экспорта: `clear()+update()` туда,
  `DELETE+INSERT` обратно). Одна транзакция: `DELETE FROM player_aliases WHERE
  collector_id=?` + bulk insert новых строк, аналогично для `chest_type_aliases`.
- **Идентификация коллектора — по `collector_slug`** в теле запроса (не hwid/kingdom/clan)
  — тот же slug, что уже используется в `export_chests_to_sheet.py`, согласованно с
  остальной читающей/админской частью системы.

## API

### `POST /api/v1/chests/aliases/import`

Auth: `Authorization: Bearer $ADMIN_TOKEN` (403 при несовпадении/отсутствии, паттерн
`server/clan.py:_require_auth`).

Тело запроса:
```json
{
  "collector_slug": "m00bqgjcl1xqUHRDvEa8bQ",
  "player_aliases": [{"raw_name": "Machet", "canonical_name": "MACHETE"}],
  "chest_aliases":  [{"raw_type": "Эпический отр", "canonical_type": "Эпический отряд"}]
}
```

Ответ `200`: `{"ok": true, "player_aliases": <count>, "chest_aliases": <count>}`.
Неизвестный `collector_slug` → `404`.

Реализация — новый файл `server/chest_aliases.py` (отдельно от `chests.py`, своя
ответственность: админ-эндпойнт против эндпойнтов бота), роутер монтируется в
`server/main.py` рядом с `chests_router`.

### `GET /api/v1/chests/summary/{slug}` (изменение существующего)

`server/chests.py:get_chest_summary` — заменить текущий `GROUP BY Chest.sender_canonical,
Chest.chest_type_canonical` на запрос с `LEFT JOIN PlayerAlias`/`LEFT JOIN ChestTypeAlias`
по `(collector_id, raw_name)`/`(collector_id, raw_type)` и `func.coalesce(...)` для имени и
типа в `SELECT`/`GROUP BY`. Остальная форма ответа (`chest_types`, `players`, `totals`,
сортировка по `total` убыв. + имя tie-break) не меняется.

## Sync-скрипт (`sync_admin_sheet_to_db.py`, корень репозитория)

По аналогии с `export_chests_to_sheet.py`:
- Константы: `SLUG`, `SHEET_ID` (тот же, что в экспорт-скрипте), `SA_PATH`.
- Читает листы `"Player Aliases"` и `"Chest Aliases"` через `spreadsheets().values().get()`,
  пропускает заголовочную строку.
- `requests.post(f"{API_BASE}/api/v1/chests/aliases/import", json=payload,
  headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})`, `ADMIN_TOKEN` — из переменной
  окружения, не хардкод в файле (см. `feedback_no_tokens_in_public_files`).
- Печатает количество загруженных алиасов каждого типа.

## Тестирование

- `server/tests/test_chest_aliases.py` (новый файл, парный к новому `chest_aliases.py`):
  401/403 без верного токена, 404 на неизвестный slug, успешная полная замена (старые
  алиасы удаляются, новые применяются), пустые списки очищают алиасы коллектора.
- `server/tests/test_chests.py`: обновить/добавить тест на `GET /summary/{slug}` —
  алиас, добавленный ПОСЛЕ импорта сундука, должен поменять `players[].name` в ответе без
  повторного импорта (это и есть проверка «на чтении, не на записи»).

## Явно вне рамок

- Глобальный `chest_type_catalog` (очки) и система паттернов T5-T9 — следующая спека.
- Редактирование `import_chests` — не меняется, продолжает писать `*_canonical` как раньше
  (просто эти поля больше не читаются `summary`).
- Версионирование/история изменений алиасов — полная замена, без аудита кто/когда менял.
