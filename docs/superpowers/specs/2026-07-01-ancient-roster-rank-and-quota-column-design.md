# Древний — редактирование звания в ростере + колонка «Квота»

## Контекст

После задачи Д (подсветка недобора квоты, следующий шаг) владельцу сначала нужна
видимая квота **на каждого игрока прямо в таблице ростера** (`/dashboard/ancients`),
а не только в отдельном блоке результата после нажатия «Рассчитать». Это отдельная
самостоятельная фича, обсуждённая 2026-07-01 в чате (владелец явно поправил: `points`
в ростере — это уже ФАКТ по конкретному Древнему через `tournament_reader.py`, не
посторонние турнирные очки — см. [[project_ancient_points_is_fact]]).

При проектировании выяснилось: для Стратегии Б (по войскам) колонка «Квота» тривиальна
— `troop_level` уже полностью редактируется в таблице. Но для Стратегии А (по званию)
редактирования звания в таблице ростера **не существует вообще** — поле `rank` есть в
БД (`AncientRoster.rank`), но:
- `_roster_rows()` (`server/ancients_dashboard.py:74-117`) не возвращает его в JSON.
- Нет `PATCH`-эндпоинта для звания (есть только для `troop_level`).
- Фронтенд не показывает и не редактирует звание в таблице ростера (только в форме
  ручного добавления нового участника, `RANKS` уже определён в `AncientsPage.jsx:14`).

Владелец подтвердил: делать оба куска сразу (звание + квота), не откладывать.

## Маппинг званий на вёдра Стратегии А

Расчёт Стратегии А берёт агрегатные числа `officer_count`/`veteran_count`, вручную
введённые в форме — они НЕ связаны со званиями отдельных игроков в ростере. Для
отображения квоты по строке используем звание игрока только как признак, в какое
из двух готовых чисел (`officer_quota`/`veteran_quota` из `result_json`) он попадает:

| Звание | Ведро |
|---|---|
| Глава, Старший, Офицер | `officer_quota` |
| Ветеран, Рядовой | `veteran_quota` |
| не задано (`None`) | квота не показывается (`—`) |

Это только для отображения — не меняет и не согласовывает введённые вручную
`officer_count`/`veteran_count` с фактическим числом игроков по званиям.

## Backend

### `server/ancient_quota.py`
Добавить:
```python
RANKS: list[str] = ["Глава", "Старший", "Офицер", "Ветеран", "Рядовой"]
OFFICER_RANKS: set[str] = {"Глава", "Старший", "Офицер"}
```

### `server/ancients_dashboard.py`

**Новый эндпоинт** (по образцу `PATCH /{slug}/troop-level`):
```python
class RankPayload(BaseModel):
    player_name: str
    rank: Optional[str] = None

@router.patch("/{slug}/rank")
async def patch_rank(slug: str, payload: RankPayload,
                     user: User = Depends(get_web_user),
                     db: AsyncSession = Depends(get_db)):
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    if payload.rank is not None and payload.rank not in RANKS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown rank: {payload.rank!r}")

    row = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == payload.player_name,
        )
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Player not in roster")

    row.rank = payload.rank
    await db.commit()
    return {"ok": True}
```

**`_roster_rows`** — добавить `rank` в возвращаемый dict (строка `"troop_level": ...`
уже есть на 111 — добавить рядом `"rank": r.AncientRoster.rank,`) и вычислить `quota`:

```python
async def _roster_rows(
    db, collector_id, mappings_dict, canonical_names, fuzzy_threshold,
    latest_calc: Optional[AncientCalculation],
) -> list:
    ...
    for r in rows:
        ...
        quota = None
        if latest_calc is not None:
            if latest_calc.strategy == "A":
                bucket = "officer_quota" if (r.AncientRoster.rank in OFFICER_RANKS) else (
                    "veteran_quota" if r.AncientRoster.rank is not None else None)
                if bucket is not None:
                    quota = latest_calc.result_json.get(bucket)
            else:
                lookup_name = mapped_name if confirmed else raw
                match = next((p for p in latest_calc.result_json.get("players", [])
                             if p["name"] == lookup_name), None)
                if match is not None:
                    quota = match["quota"]
        result.append({
            ..., "rank": r.AncientRoster.rank, "quota": quota,
        })
    return result
```

`latest_calc` fetched once per collector in `get_dashboard_ancients` (одним запросом
`select(AncientCalculation).where(collector_id==...).order_by(computed_at.desc()).limit(1)`)
и передаётся в `_roster_rows` — не по одному расчёту на строку.

## Frontend (`AncientsPage.jsx`)

- Новая функция `handleRankChange(slug, playerName, rank)` — вызывает
  `api.dashboardAncientsRank(slug, playerName, rank || null)`, `refresh()` (зеркалирует
  `handleTroopLevelChange`).
- Новый `<select>` «Звание» в строке таблицы ростера, между колонками «Войска» и
  (новой) «Квота» — значения `RANKS` (уже есть константа, включая `''` = не задано),
  `value={p.rank || ''}`, `onChange` → `handleRankChange`.
- Новая колонка «Квота» — `<td>{p.quota != null ? fmtNum(p.quota, 2) : '—'}</td>`
  (переиспользует существующий хелпер `fmtNum`, уже применяется для `points`).
- Новые заголовки `<th>` в `thead` (строка ~522): «Звание», «Квота».
- `web/src/api.js` — новая функция `dashboardAncientsRank(slug, playerName, rank) =>
  request('PATCH', .../rank, {player_name, rank})`.
- `dashboard_content.js`/`.en.js` — новые ключи `cx.rank` ("Звание"/"Rank"),
  `cx.quota` ("Квота"/"Quota").

## Тестирование (TDD)

`server/tests/test_ancients_dashboard.py`:
- `PATCH /{slug}/rank`: успешная запись, 400 на невалидное звание, 404 на
  несуществующего игрока (зеркалирует существующие тесты `troop-level`).
- `GET /dashboard/ancients`: roster row возвращает `rank`.
- Quota-резолюция Стратегии Б: игрок с валидным `troop_level`, присутствующий в
  последнем расчёте → `quota` совпадает с суммой из `result_json`; игрок без
  `troop_level` (excluded) → `quota is None`.
- Quota-резолюция Стратегии А: игрок со званием `Глава`/`Старший`/`Офицер` →
  `quota == officer_quota`; `Ветеран`/`Рядовой` → `quota == veteran_quota`; без
  звания → `quota is None`.
- Нет расчётов в истории коллектора → `quota is None` у всех строк ростера.
- Регрессия: существующие тесты `test_roster_uses_profile_troop_level_as_fallback` и
  подобные продолжают проходить (rank-логика не трогает troop_level fallback).

## Явно не входит в эту спеку

- Условное форматирование недобора (задача Д) — следующий шаг, зависит от этой
  колонки «Квота».
- Согласование `officer_count`/`veteran_count` (вручную вводимых в форме расчёта) с
  фактическим количеством игроков по званиям в ростере — не запрошено, вне рамок.
- Валидация `rank` на уже существующем эндпоинте ручного добавления участника
  (`POST /{slug}/roster/manual`) — сейчас принимает произвольную строку, не трогаем.
