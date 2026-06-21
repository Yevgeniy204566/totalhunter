# Сундуки — Фильтрация публичной сводки по сезону + квота Epic-склепов (Спека 2 из 3)

Дата: 2026-06-21

## Контекст

Спека 1 добавила хранение настроек сезона (`timezone_offset_minutes`,
`period_start`, `period_end`, `target_points`, `target_chests` на
`ChestCollector`, `counts_toward_quota` на `ChestConfiguration`) и кабинет
для их редактирования — ничего из этого пока не влияет на публичную сводку.
Эта спека подключает их к `GET /api/v1/chests/summary/{slug}`
(`server/chests.py`). Спека 3 (после этой) возьмёт переданные данные и
отрисует шапку/таймер/цвета на публичной странице.

Решено по итогам обсуждения: сезоны идут подряд, перманентно (например,
двухнедельными блоками без зазоров) — система просто фильтрует сундуки по
факту получения на сервере (`Chest.collected_at`) в рамках текущего
настроенного диапазона `period_start`/`period_end`. Никакой отдельной
логики «активного» сезона сверх самого диапазона дат не требуется.

## Решённые вопросы

- **Границы диапазона** — обе включительно:
  `Chest.collected_at BETWEEN period_start AND period_end`.
- **`updated_at`** при настроенном сезоне — `max(collected_at)` **внутри**
  того же диапазона дат (не глобальный максимум) — надпись «Последнее
  обновление» должна относиться к тем же данным, что видны в таблице.
- **Квота сундуков** (Gemini, важное уточнение) — считается **только** по
  сундукам, отмеченным конкретным кланом как `counts_toward_quota=true`
  (переключатель «Считать в квоту» из Спеки 1), не по всем сундукам
  паттерна. Очки (`points`) продолжают считаться по всем сундукам паттерна,
  как раньше — это два разных числа, не путать.
- Без настроенного сезона (`period_start`/`period_end` оба `NULL`) —
  поведение полностью как сейчас, без фильтрации, без квоты в ответе как
  значимого поля (квота всё равно посчитается, просто будет 0 у всех, если
  никто не включил переключатель — это не баг, не требует отдельной ветки
  кода).

## Backend (`server/chests.py`)

### Фильтрация по датам

В `get_chest_summary`, после получения `collector`, перед выполнением
основного запроса на `rows`, добавляется условие в `.where(...)`:

```python
    query = (
        select(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points,
               ChestConfiguration.counts_toward_quota, func.count())
        .select_from(Chest)
        .outerjoin(PlayerAlias, ...)
        .outerjoin(ChestTypeAlias, ...)
        .join(ChestConfiguration, ...)
        .outerjoin(ChestLocalization, ...)
        .where(Chest.collector_id == collector.id)
    )
    if collector.period_start is not None:
        query = query.where(Chest.collected_at >= collector.period_start)
    if collector.period_end is not None:
        query = query.where(Chest.collected_at <= collector.period_end)
    query = query.group_by(sender_expr, chest_type_expr, display_expr,
                           ChestConfiguration.points, ChestConfiguration.counts_toward_quota)
    rows = (await db.execute(query)).all()
```

`ChestConfiguration.counts_toward_quota` добавляется и в `SELECT`, и в
`GROUP BY` — нужен для подсчёта квоты в `_pivot_summary` (см. ниже).

### `_pivot_summary` — новый параметр строки и `quota_chests` на игрока

Сигнатура строки меняется с `(sender, chest_type_en, display_name, points, count)`
на `(sender, chest_type_en, display_name, points, counts_toward_quota, count)`.
Внутри цикла добавляется отдельный аккумулятор `player_quota: dict[str, int]`:

```python
    player_quota: dict[str, int] = {}
    ...
    for sender, chest_type_en, display_name, points, counts_toward_quota, count in rows:
        ...
        if counts_toward_quota:
            player_quota[sender] = player_quota.get(sender, 0) + count
```

В объекте каждого игрока добавляется поле:

```python
        players.append({
            "name": sender,
            "counts": counts,
            "total": sum(counts_by_en.values()),
            "points": player_points[sender],
            "quota_chests": player_quota.get(sender, 0),
        })
```

`total`/`points` не меняются по смыслу — `quota_chests` это новое,
самостоятельное поле, существующие consumers (если какие-то есть кроме
самой публичной страницы) не ломаются, так как это чисто аддитивное
изменение.

### `updated_at` — учитывает диапазон дат

```python
    updated_at_query = select(func.max(Chest.collected_at)).where(
        Chest.collector_id == collector.id)
    if collector.period_start is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at >= collector.period_start)
    if collector.period_end is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at <= collector.period_end)
    updated_at = (await db.execute(updated_at_query)).scalar_one_or_none()
```

### Новые поля верхнего уровня в ответе

После вызова `_pivot_summary(...)`, перед `return result`:

```python
    result["updated_at"] = updated_at.isoformat() if updated_at else None
    result["period_start"] = collector.period_start.isoformat() if collector.period_start else None
    result["period_end"] = collector.period_end.isoformat() if collector.period_end else None
    result["timezone_offset_minutes"] = collector.timezone_offset_minutes
    result["targets"] = {
        "points": collector.target_points,
        "chests": collector.target_chests,
    }
```

`targets` — отдельный вложенный объект (а не два плоских поля), чтобы
Спека 3 могла проверить «настроен ли сезон вообще» одним условием
(`targets.points != null || targets.chests != null`), не разбираясь в
пяти отдельных полях.

## Вне рамок (Спека 3)

- Любая отрисовка: шапка с целями, таймер обратного отсчёта, колонка `#`,
  закреплённые колонки, кастомный скроллбар, цветовая подсветка строк.
- Переименование колонки «Всего сундуков» → «Epic склепов» в UI — данные
  для этого (`quota_chests`) уже есть из этой спеки, переименование и
  отображение делает Спека 3.

## Тестирование

- `server/tests/test_chests.py`: новые тесты на
  (1) фильтрацию по `period_start`/`period_end` (сундук вне диапазона не
  попадает в сводку, сундук на самой границе — попадает, обе границы
  включительно);
  (2) `quota_chests` считает только сундуки с `counts_toward_quota=true`,
  игнорируя обычные сундуки паттерна у того же игрока;
  (3) `updated_at` внутри настроенного диапазона не превышает `period_end`,
  даже если в БД есть более поздние сундуки;
  (4) коллектор без настроенного сезона — `period_start`/`period_end`/
  `targets.points`/`targets.chests` все `null`, фильтрация не применяется
  (существующее поведение не ломается, регрессия по старым тестам).
