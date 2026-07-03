# Древний: сохранение сырых OCR-имён турнира + слияние с Сундуками + кнопка «Очистить»

**Дата:** 2026-07-03 (ревизия 2 — добавлена Часть 3, слияние строк)
**Статус:** черновик, ждёт ревью владельца перед переходом к implementation plan

## Проблема

В личном кабинете «Древний» уже есть колонка «Игрок (OCR)» и соседняя колонка
«Правильное имя» (ручное подтверждение через `AncientNameMapping`, задеплоено).
Но сейчас `POST /api/v1/tournaments/import` (`server/tournaments.py`) **на лету**
подменяет сырой OCR-текст на найденное каноническое имя через
`_resolve_player_name()`: точное совпадение с `PlayerAlias.raw_name` или
fuzzy-match (cutoff 0.75) против канонических имён Сундуков. Из-за этого
`AncientRoster.player_name` хранит уже подменённое имя, и колонка «Игрок (OCR)»
не всегда показывает то, что реально прочитал бот — сырой текст теряется
безвозвратно для успешно сматченных строк.

Владелец хочет:
1. Видеть в кабинете и настоящее сырое имя из турнирной таблицы, и подтверждённое
   правильное имя (с публичной страницы Сундуков) — раздельно, без молчаливой
   автоподмены.
2. Кнопку «Очистить» над колонкой сырых имён, которая одним кликом стирает
   результаты последнего турнирного импорта (имена + очки), не трогая ручные
   записи и записи из «Заполнить из Сундуков».
3. **(Добавлено в ревизии 2)** Чтобы очки турнира и квота (войска/звание) одного
   и того же игрока сходились в одну строку и формула недобора
   (`quota − points`) реально считалась — а не были разорваны на две отдельные
   строки `AncientRoster` (одна из Сундуков с войсками, другая из OCR с
   очками), которые визуально дублируют игрока и не суммируются.

**Почему это одна задача, а не две:** отключение автоподмены в п.1 — это то,
из-за чего проблема п.3 становится частой (без автоподмены почти каждое имя,
не попавшее в алиасы Сундуков буква-в-букву, требует ручного маппинга — и до
этой ревизии ручной маппинг не сливал данные физически, только красил строку
зелёным). Без Части 3 отключение автоподмены превращает единичный
край-кейс в постоянный источник раздвоенных строк.

## Архитектурное решение

### Часть 1 — сырое имя всегда сохраняется, разрешение имени через AncientNameMapping

`AncientRoster` получает новую колонку `raw_ocr_name` (String(200), nullable) —
последний сырой OCR-текст, когда-либо полученный для этой строки. Не путать с
`player_name`, который остаётся стабильным идентификатором строки (uniq-ключ
вместе с `collector_id`) и служит целью для всех PATCH/DELETE-мутаций
(`troop-level`, `rank`, удаление строки) — это не меняется.

В `tournaments.py`:
- Убрать `_resolve_player_name()`, `PlayerAlias`-резолвинг и
  `NAME_FUZZY_MATCH_CUTOFF` — больше никакого fuzzy-угадывания на импорте.
- Вместо этого: загрузить подтверждённые `AncientNameMapping` для коллектора
  (`{raw_ocr_name: canonical_name}`), и для каждой строки турнира
  `target_name = confirmed_mappings.get(item.name, item.name)` — точное
  совпадение по уже подтверждённому маппингу (никакого fuzzy здесь, только
  то, что лидер явно подтвердил на дашборде).
- Апсерт `AncientRoster` по `(collector_id, player_name=target_name)`:
  `place`, `points`, `source='ocr'`, `manual_expires_at=None` — как сейчас, и
  **всегда** `raw_ocr_name = item.name` (даже когда `target_name` уже
  канонический — колонка «Игрок (OCR)» должна показывать точный сырой текст
  последнего импорта).

Итог: если маппинг для этого сырого имени уже подтверждён на дашборде, турнир
сразу пишет очки в каноническую строку, без дублей. Если не подтверждён —
строка создаётся под сырым именем, как и раньше, и ждёт ручного подтверждения.

**Осознанно теряемое поведение:** тесты `test_fuzzy_match_uses_close_alias_canonical_name`
и `test_fuzzy_match_does_not_match_dissimilar_name` проверяют автоподмену по
`PlayerAlias` на импорте — удаляются/переписываются под новое поведение.
Автоматическое молчаливое угадывание по алиасам Сундуков полностью уходит;
остаётся только явное подтверждение лидером через дашборд.

### Часть 2 — кнопка «Очистить»

Новый эндпоинт:

```
DELETE /web/dashboard/ancients/{slug}/roster/ocr-import
```

Доступ: `_get_own_or_editor_collector` (как остальные мутации ростера).

Логика (учитывает, что после Части 3 строка может быть физически слитой с
Сундуками и нести войска/звание — такую строку удалять целиком нельзя):

- Для каждой строки коллектора, где `place is not None or points is not None`:
  - Если строка «чисто турнирная» (`source == 'ocr'` **и** `troop_level is None`
    **и** `rank is None` — то есть в ней нет ничего, кроме данных импорта) →
    строка удаляется целиком.
  - Иначе (строка несёт войска/звание, то есть это слитая или ручная/из
    Сундуков строка, к которой позже пристыковались очки турнира) →
    `place = None`, `points = None`, сама строка и её `troop_level`/`rank`/
    `raw_ocr_name` остаются нетронутыми.
- Возвращает `{"deleted": <count>, "cleared": <count>}`.

Фронтенд (`AncientsPage.jsx`):
- Кнопка «Очистить» над таблицей ростера, с двухшаговым подтверждением
  (тот же паттерн confirm/cancel, что у удаления отдельной строки).
- Новый хелпер в `api.js`: `dashboardAncientsClearOcrImport(slug)`.
- После успешного вызова — `refresh()`.

### Часть 3 — физическое слияние строк при подтверждении маппинга

Это то, что было упущено в первой версии спеки и обязано быть частью этой
задачи, иначе п.3 из «Проблемы» не решается.

**Общий хелпер** (новый, `server/ancients_dashboard.py`):

```python
def _coalesce_roster_fields(base: dict, row: AncientRoster) -> dict:
    """Собирает словарь полей, беря значение из row там, где оно не NULL,
    и сохраняя то, что уже было в base, иначе."""
    return {
        "place": row.place if row.place is not None else base.get("place"),
        "points": row.points if row.points is not None else base.get("points"),
        "troop_level": row.troop_level if row.troop_level is not None else base.get("troop_level"),
        "rank": row.rank if row.rank is not None else base.get("rank"),
        "raw_ocr_name": row.raw_ocr_name if row.raw_ocr_name is not None else base.get("raw_ocr_name"),
        "source": "ocr" if row.source == "ocr" else base.get("source", row.source),
    }
```

Это обобщение уже существующей бесхитростной логики `preserved`-словаря внутри
`populate_roster_from_chests` — та функция **рефакторится** на использование
этого же хелпера (плюс теперь коалесит `raw_ocr_name`), вместо дублирования
той же идеи второй раз.

**Новый хелпер слияния** (`server/ancients_dashboard.py`):

```python
async def _merge_roster_on_mapping_confirm(db, collector_id, raw_ocr_name, canonical_name):
    if raw_ocr_name == canonical_name:
        return
    raw_row = (await db.execute(select(AncientRoster).where(
        AncientRoster.collector_id == collector_id,
        AncientRoster.player_name == raw_ocr_name,
    ))).scalar_one_or_none()
    if raw_row is None:
        return  # ничего не импортировано под этим сырым именем — будущие
                 # импорты сами попадут сразу в каноническую строку (Часть 1)
    canonical_row = (await db.execute(select(AncientRoster).where(
        AncientRoster.collector_id == collector_id,
        AncientRoster.player_name == canonical_name,
    ))).scalar_one_or_none()
    merged = {}
    if canonical_row is not None:
        merged = _coalesce_roster_fields(merged, canonical_row)
        await db.delete(canonical_row)
    merged = _coalesce_roster_fields(merged, raw_row)
    merged["raw_ocr_name"] = merged.get("raw_ocr_name") or raw_row.player_name
    await db.delete(raw_row)
    await db.flush()
    db.add(AncientRoster(
        collector_id=collector_id, player_name=canonical_name,
        place=merged.get("place"), points=merged.get("points"),
        troop_level=merged.get("troop_level"), rank=merged.get("rank"),
        raw_ocr_name=merged.get("raw_ocr_name"),
        source=merged.get("source", "ocr"), manual_expires_at=None,
    ))
```

Порядок коалесации: сначала каноническая строка (Сундуки/ручная — войска,
звание уже там), потом сырая OCR-строка поверх (свежие место/очки
перезаписывают, но `None`-поля сырой строки не затирают то, что уже было у
канонической). `troop_level`/`rank`, выставленные вручную на канонической
строке, переживают слияние.

`patch_name_mappings` (`PATCH /{slug}/name-mappings`) вызывает
`_merge_roster_on_mapping_confirm` для каждого элемента с `confirmed=True`
**после** апсерта самой записи `AncientNameMapping`. Это закрывает случай из
примера владельца: лидер видит сырую строку `Пeтрoв*VIP` рядом с уже
существующей канонической `Петров`, выбирает в дропдауне «Петров», жмёт
«Сохранить маппинги» — обе физические строки сливаются в одну немедленно, не
дожидаясь следующего импорта турнира.

**Изменение в `_roster_rows`** (`GET /web/dashboard/ancients`): строка
считается уже физически слитой, если `raw_ocr_name is not None and
raw_ocr_name != player_name`. Для таких строк `mapped_name = player_name`
(он и есть каноническое имя), `suggested_name = None`, `mapping_confirmed = True`
— без обращения к `mappings_dict`. Для ещё не слитых строк логика остаётся в
точности как сейчас (поиск в `mappings_dict` по `player_name`, затем
fuzzy-подсказка) — это сохраняет обратную совместимость с уже существующими
тестами, где `AncientNameMapping` вставлена в БД напрямую, без физического
слияния (например `test_get_roster_confirmed_mapping_applied`).

Колонка «Игрок (OCR)» на фронтенде теперь читает `p.raw_ocr_name ??
p.player_name` вместо `p.player_name` (для строк из Сундуков/ручных без
единого импорта туда ещё ничего не прилетало — тогда `raw_ocr_name` пуст,
показываем текущее имя как раньше).

**Фикс существующего фронтенд-бага, который слияние обнажает:** кнопка
«Разблокировать» у уже подтверждённой строки сейчас вызывает
`api.dashboardAncientsNameMappingDelete(c.slug, p.player_name)`. После
физического слияния `p.player_name` — это уже каноническое имя, а не тот
сырой ключ, под которым лежит запись в `AncientNameMapping`. Нужно передавать
`p.raw_ocr_name` (у слитой строки он всегда установлен и отличается от
`player_name`).

Поскольку слияние необратимо (см. ограничение ниже), кнопку «Разблокировать»
для уже физически слитых строк (`raw_ocr_name != player_name`) показывать не
нужно — иначе клик будет выглядеть как рабочее действие (запрос вернёт `ok`),
но визуально ничего не изменится, что похоже на баг. Вместо кнопки — статичная
иконка 🔒 без обработчика.

## Известное и осознанно не устраняемое ограничение

«Разблокировать» удаляет только запись `AncientNameMapping` (чтобы будущие
импорты больше не сливали автоматически под этим именем) — она **не**
разъединяет уже слитые физически данные обратно на две строки: это было бы
разрушением истории (какие очки к кому относились) без однозначного способа
восстановить границу. Такое поведение не баг, а сознательный компромисс —
аналогично уже принятому в `populate_roster_from_chests` (см. существующий
docstring этой функции).

## Изменяемые файлы

| Файл | Изменение |
|---|---|
| `server/models.py` | `AncientRoster.raw_ocr_name` (String(200), nullable) |
| `server/alembic/versions/<new>_add_ancient_roster_raw_ocr_name.py` | Новая миграция |
| `server/tournaments.py` | Убрать `_resolve_player_name`/`PlayerAlias`-резолвинг; резолвить только через подтверждённый `AncientNameMapping`; всегда писать `raw_ocr_name` |
| `server/tests/test_tournaments.py` | Удалить/переписать 2 теста автоподмены; добавить тест на резолвинг через подтверждённый маппинг + сохранение `raw_ocr_name` |
| `server/ancients_dashboard.py` | `_coalesce_roster_fields`, `_merge_roster_on_mapping_confirm`, вызов слияния из `patch_name_mappings`, рефакторинг `populate_roster_from_chests` на общий хелпер, обновление `_roster_rows` (учёт уже слитых строк), новый `DELETE /{slug}/roster/ocr-import` |
| `server/tests/test_ancients_dashboard.py` | Тесты слияния (дубль строк схлопывается, войска/звание переживают слияние, quota/shortfall считается после слияния), тесты «Очистить» (удаление чистых OCR-строк vs очистка слитых) |
| `web/src/api.js` | `dashboardAncientsClearOcrImport(slug)` |
| `web/src/pages/AncientsPage.jsx` | Колонка «Игрок (OCR)» читает `raw_ocr_name`; фикс аргумента кнопки «Разблокировать»; кнопка «Очистить» с confirm/cancel |

## Вне рамок

- `calculate()` (расчёт квот) не меняется: к моменту расчёта слияние уже
  произошло (либо на импорте, либо на подтверждении маппинга), поэтому
  `AncientRoster.player_name` уже несёт каноническое имя — существующий
  fallback через `mapped_names` в стратегии B становится в основном мёртвым
  кодом для уже слитых строк, но не мешает и не удаляется (защитный запасной
  путь для ещё не слитых строк).
- Слияние срабатывает только на точное совпадение подтверждённого
  `raw_ocr_name` — повторное fuzzy-угадывание в момент слияния не делается
  (сознательно, чтобы не дублировать логику подсказки, которая уже отдельно
  считается в `_roster_rows` для конкретно этого превью на дашборде).
