# Сундуки — Фильтрация публичной сводки по сезону + квота Epic-склепов (2/3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scope the public `GET /api/v1/chests/summary/{slug}` endpoint to the clan's configured season window (`period_start`/`period_end`), add a per-player Epic-crypt-only quota count, and pass season metadata through to the JSON response — with zero behavior change for collectors that never configured a season.

**Architecture:** All changes live in `server/chests.py`. The existing single aggregation query in `get_chest_summary` grows two optional `WHERE` clauses (date range) and one extra selected/grouped column (`ChestConfiguration.counts_toward_quota`); `_pivot_summary` grows one extra accumulator dict and one extra field on each player object. A handful of new top-level keys are appended to the response dict after `_pivot_summary` returns.

**Tech Stack:** FastAPI + SQLAlchemy async (`server/chests.py`), pytest + httpx.

## Global Constraints

- Date range is inclusive on both ends: `Chest.collected_at >= period_start` AND `Chest.collected_at <= period_end`, each clause applied only if the corresponding field is not `None` on the collector.
- `updated_at` is `max(collected_at)` scoped to the same date-range filter as the main query — not a separate, wider global max — so the "last updated" label never refers to data outside what the table currently shows.
- Quota (`quota_chests` per player) counts only chests whose resolved `ChestConfiguration.counts_toward_quota` is `True` — a strict subset of the already-`is_in_pattern`-filtered chests (the existing `JOIN ... is_in_pattern.is_(True)` is untouched, so a chest must already be in-pattern to reach `_pivot_summary` at all). `points`/`total` continue to count every in-pattern chest, unchanged — `quota_chests` is an additional, independent field, not a replacement.
- Collectors with `period_start`/`period_end` both `None` (the default — see Spec 1) get unfiltered behavior identical to before this plan — every existing test in `test_chests.py` that doesn't set these fields must keep passing unmodified.
- `targets` in the response is a nested object `{"points": int|None, "chests": int|None}`, not two flat top-level keys — so the frontend (Spec 3) can check "is a season configured" with one condition.

---

### Task 1: Date-range filtering on the summary query + updated_at

**Files:**
- Modify: `server/chests.py:258-307` (`get_chest_summary`)
- Test: `server/tests/test_chests.py` (append)

**Interfaces:**
- No new functions. `get_chest_summary`'s behavior gains date-scoping; its return shape (keys) is unchanged by this task — `targets`/`period_start`/`period_end`/`timezone_offset_minutes` are added in Task 3, not here.

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chests.py`:

```python
@pytest.mark.asyncio
async def test_summary_filters_chests_by_period_inclusive_both_ends(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "perioduser000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K15", clan="PeriodClan",
            items=[
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-20T23:59:59"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-21T00:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-30T12:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-07-05T00:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-07-05T00:00:01"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
        collector.period_end = datetime.fromisoformat("2026-07-05T00:00:00")
        db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    # In range (inclusive both ends): 06-21T00:00:00, 06-30T12:00:00, 07-05T00:00:00 = 3
    # Excluded: 06-20T23:59:59 (before start), 07-05T00:00:01 (after end)
    assert body["players"][0]["total"] == 3
    assert body["updated_at"] == "2026-07-05T00:00:00"


@pytest.mark.asyncio
async def test_summary_unconfigured_period_applies_no_filter(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "noperioduser0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K16", clan="NoPeriodClan",
            items=[
                {"chest_type": "Common", "sender": "P1", "timestamp": "2020-01-01T00:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2030-12-31T23:59:59"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["players"][0]["total"] == 2
    assert body["updated_at"] == "2030-12-31T23:59:59"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -k "period" -v`
Expected: `test_summary_filters_chests_by_period_inclusive_both_ends` FAILS (`body["players"][0]["total"] == 5`, not `3` — no filtering applied yet). `test_summary_unconfigured_period_applies_no_filter` PASSES already (no behavior change needed for this case) — that's fine, it's a regression guard for the next step, not a red/green test on its own.

- [ ] **Step 3: Implement the date-range filter**

In `server/chests.py`, replace the body of `get_chest_summary` from the `rows = (await db.execute(...` line through the `updated_at = (await db.execute(...` line (currently):

```python
    rows = (await db.execute(
        select(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points,
               func.count())
        .select_from(Chest)
        .outerjoin(
            PlayerAlias,
            and_(PlayerAlias.collector_id == Chest.collector_id,
                 PlayerAlias.raw_name == Chest.sender_raw),
        )
        .outerjoin(
            ChestTypeAlias,
            and_(ChestTypeAlias.collector_id == Chest.collector_id,
                 ChestTypeAlias.raw_type == Chest.chest_type_raw),
        )
        .join(
            ChestConfiguration,
            and_(ChestConfiguration.collector_id == Chest.collector_id,
                 ChestConfiguration.catalog_id == chest_type_expr,
                 ChestConfiguration.is_in_pattern.is_(True)),
        )
        .outerjoin(
            ChestLocalization,
            and_(ChestLocalization.canonical_type == chest_type_expr,
                 ChestLocalization.language == collector.language),
        )
        .where(Chest.collector_id == collector.id)
        .group_by(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points)
    )).all()

    updated_at = (await db.execute(
        select(func.max(Chest.collected_at)).where(Chest.collector_id == collector.id)
    )).scalar_one_or_none()
```

with:

```python
    rows_query = (
        select(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points,
               func.count())
        .select_from(Chest)
        .outerjoin(
            PlayerAlias,
            and_(PlayerAlias.collector_id == Chest.collector_id,
                 PlayerAlias.raw_name == Chest.sender_raw),
        )
        .outerjoin(
            ChestTypeAlias,
            and_(ChestTypeAlias.collector_id == Chest.collector_id,
                 ChestTypeAlias.raw_type == Chest.chest_type_raw),
        )
        .join(
            ChestConfiguration,
            and_(ChestConfiguration.collector_id == Chest.collector_id,
                 ChestConfiguration.catalog_id == chest_type_expr,
                 ChestConfiguration.is_in_pattern.is_(True)),
        )
        .outerjoin(
            ChestLocalization,
            and_(ChestLocalization.canonical_type == chest_type_expr,
                 ChestLocalization.language == collector.language),
        )
        .where(Chest.collector_id == collector.id)
    )
    updated_at_query = select(func.max(Chest.collected_at)).where(
        Chest.collector_id == collector.id)

    if collector.period_start is not None:
        rows_query = rows_query.where(Chest.collected_at >= collector.period_start)
        updated_at_query = updated_at_query.where(Chest.collected_at >= collector.period_start)
    if collector.period_end is not None:
        rows_query = rows_query.where(Chest.collected_at <= collector.period_end)
        updated_at_query = updated_at_query.where(Chest.collected_at <= collector.period_end)

    rows_query = rows_query.group_by(sender_expr, chest_type_expr, display_expr,
                                     ChestConfiguration.points)

    rows = (await db.execute(rows_query)).all()
    updated_at = (await db.execute(updated_at_query)).scalar_one_or_none()
```

The `result = _pivot_summary(...)` and `result["updated_at"] = ...` lines immediately after stay exactly as they are — do not touch them in this task.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -v`
Expected: all tests PASS, including both new ones and every pre-existing summary test (none of them set `period_start`/`period_end`, so they exercise the unfiltered path, which must behave exactly as before).

- [ ] **Step 5: Commit**

```bash
git add server/chests.py server/tests/test_chests.py
git commit -m "feat(chests): filter public summary by configured season period (inclusive both ends)"
```

---

### Task 2: Epic-crypt-only quota count per player

**Files:**
- Modify: `server/chests.py:201-255` (`_pivot_summary`), and the `rows_query`'s `select(...)`/`group_by(...)` from Task 1
- Test: `server/tests/test_chests.py` (append)

**Interfaces:**
- Consumes: the `rows_query` built in Task 1 (this task adds one more selected/grouped column to it).
- Produces: `_pivot_summary(kingdom, clan, rows)` now expects 6-tuples `(sender, chest_type_en, display_name, points, counts_toward_quota, count)` instead of 5-tuples. Each player object in the returned `"players"` list gains a `"quota_chests": int` field. Consumed by the public API response (no further plumbing needed — `_pivot_summary`'s return dict is returned as-is from `get_chest_summary`).

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chests.py`:

```python
@pytest.mark.asyncio
async def test_summary_quota_chests_counts_only_quota_marked_types(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "quotauser0000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K17", clan="QuotaClan",
            items=[
                {"chest_type": "EpicCrypt", "sender": "P1", "timestamp": "2026-06-18T10:00:00"},
                {"chest_type": "EpicCrypt", "sender": "P1", "timestamp": "2026-06-18T10:01:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T10:02:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T10:03:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T10:04:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="EpicCrypt",
                                          points=80, is_in_pattern=True,
                                          counts_toward_quota=True))
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="Common",
                                          points=5, is_in_pattern=True,
                                          counts_toward_quota=False))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    player = resp.json()["players"][0]
    assert player["quota_chests"] == 2
    assert player["total"] == 5
    assert player["points"] == 2 * 80 + 3 * 5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -k quota_chests_counts -v`
Expected: FAIL — `KeyError: 'quota_chests'` (the field doesn't exist on the player object yet).

- [ ] **Step 3: Add the column to the query and thread it through `_pivot_summary`**

In `server/chests.py`, in the `rows_query` built in Task 1, change the `select(...)` line from:

```python
    rows_query = (
        select(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points,
               func.count())
```

to:

```python
    rows_query = (
        select(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points,
               ChestConfiguration.counts_toward_quota, func.count())
```

And change the `group_by(...)` call from:

```python
    rows_query = rows_query.group_by(sender_expr, chest_type_expr, display_expr,
                                     ChestConfiguration.points)
```

to:

```python
    rows_query = rows_query.group_by(sender_expr, chest_type_expr, display_expr,
                                     ChestConfiguration.points,
                                     ChestConfiguration.counts_toward_quota)
```

Now update `_pivot_summary`. Change its docstring line and the unpacking loop — replace:

```python
def _pivot_summary(kingdom: str, clan: str, rows) -> dict:
    """rows: iterable of (sender, chest_type_en, display_name, points_per_unit, count).

    chest_type_en is used as the internal dedup/grouping key (stable, language-
    independent) — display_name is only substituted in at the very end, so two
    different chest types that happen to share an identical translation can never be
    merged into one row by mistake.
    """
    chest_type_order: list[str] = []
    seen_types = set()
    display_names: dict[str, str] = {}
    per_player: dict[str, dict[str, int]] = {}
    player_points: dict[str, int] = {}
    totals: dict[str, int] = {}
    grand_total = 0
    total_points = 0

    for sender, chest_type_en, display_name, points, count in rows:
        if chest_type_en not in seen_types:
            seen_types.add(chest_type_en)
            chest_type_order.append(chest_type_en)
            display_names[chest_type_en] = display_name
        per_player.setdefault(sender, {})
        per_player[sender][chest_type_en] = per_player[sender].get(chest_type_en, 0) + count
        player_points[sender] = player_points.get(sender, 0) + count * points
        totals[chest_type_en] = totals.get(chest_type_en, 0) + count
        grand_total += count
        total_points += count * points
```

with:

```python
def _pivot_summary(kingdom: str, clan: str, rows) -> dict:
    """rows: iterable of (sender, chest_type_en, display_name, points_per_unit,
    counts_toward_quota, count).

    chest_type_en is used as the internal dedup/grouping key (stable, language-
    independent) — display_name is only substituted in at the very end, so two
    different chest types that happen to share an identical translation can never be
    merged into one row by mistake.
    """
    chest_type_order: list[str] = []
    seen_types = set()
    display_names: dict[str, str] = {}
    per_player: dict[str, dict[str, int]] = {}
    player_points: dict[str, int] = {}
    player_quota: dict[str, int] = {}
    totals: dict[str, int] = {}
    grand_total = 0
    total_points = 0

    for sender, chest_type_en, display_name, points, counts_toward_quota, count in rows:
        if chest_type_en not in seen_types:
            seen_types.add(chest_type_en)
            chest_type_order.append(chest_type_en)
            display_names[chest_type_en] = display_name
        per_player.setdefault(sender, {})
        per_player[sender][chest_type_en] = per_player[sender].get(chest_type_en, 0) + count
        player_points[sender] = player_points.get(sender, 0) + count * points
        if counts_toward_quota:
            player_quota[sender] = player_quota.get(sender, 0) + count
        totals[chest_type_en] = totals.get(chest_type_en, 0) + count
        grand_total += count
        total_points += count * points
```

Finally, update the `players.append(...)` call — change:

```python
        players.append({
            "name": sender,
            "counts": counts,
            "total": sum(counts_by_en.values()),
            "points": player_points[sender],
        })
```

to:

```python
        players.append({
            "name": sender,
            "counts": counts,
            "total": sum(counts_by_en.values()),
            "points": player_points[sender],
            "quota_chests": player_quota.get(sender, 0),
        })
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -v`
Expected: all tests PASS, including the new one and every pre-existing test in the file (the 5-tuple-to-6-tuple change is internal to `_pivot_summary` and `get_chest_summary`'s own query — no external caller of `_pivot_summary` exists outside this file).

- [ ] **Step 5: Commit**

```bash
git add server/chests.py server/tests/test_chests.py
git commit -m "feat(chests): add per-player quota_chests count (counts_toward_quota chests only)"
```

---

### Task 3: Pass season metadata through to the public response

**Files:**
- Modify: `server/chests.py:303-307` (the tail of `get_chest_summary`, after `_pivot_summary` is called)
- Test: `server/tests/test_chests.py` (append)

**Interfaces:**
- Produces: the `GET /api/v1/chests/summary/{slug}` response gains 4 new top-level keys: `"period_start"` (ISO string or `null`), `"period_end"` (ISO string or `null`), `"timezone_offset_minutes"` (int or `null`), `"targets"` (`{"points": int|None, "chests": int|None}`). Consumed by Spec 3 (frontend), not by anything in this plan.

- [ ] **Step 1: Write the failing tests**

Append to `server/tests/test_chests.py`:

```python
@pytest.mark.asyncio
async def test_summary_includes_season_metadata_when_configured(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "seasonmetauser")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K18", clan="SeasonMetaClan",
            items=[{"chest_type": "Common", "sender": "P1",
                    "timestamp": "2026-06-25T00:00:00"}],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
        collector.period_end = datetime.fromisoformat("2026-07-05T00:00:00")
        collector.timezone_offset_minutes = 180
        collector.target_points = 5000
        collector.target_chests = 50
        db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_start"] == "2026-06-21T00:00:00"
    assert body["period_end"] == "2026-07-05T00:00:00"
    assert body["timezone_offset_minutes"] == 180
    assert body["targets"] == {"points": 5000, "chests": 50}


@pytest.mark.asyncio
async def test_summary_season_metadata_is_null_when_unconfigured(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "noseasonmeta0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K19", clan="NoSeasonMetaClan",
            items=[{"chest_type": "Common", "sender": "P1",
                    "timestamp": "2026-06-25T00:00:00"}],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_start"] is None
    assert body["period_end"] is None
    assert body["timezone_offset_minutes"] is None
    assert body["targets"] == {"points": None, "chests": None}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -k season_metadata -v`
Expected: FAIL — `KeyError: 'period_start'` (the keys don't exist in the response yet).

- [ ] **Step 3: Add the fields to the response**

In `server/chests.py`, the tail of `get_chest_summary` currently reads:

```python
    result = _pivot_summary(collector.kingdom, collector.clan, rows)
    result["updated_at"] = updated_at.isoformat() if updated_at else None
    return result
```

Change it to:

```python
    result = _pivot_summary(collector.kingdom, collector.clan, rows)
    result["updated_at"] = updated_at.isoformat() if updated_at else None
    result["period_start"] = collector.period_start.isoformat() if collector.period_start else None
    result["period_end"] = collector.period_end.isoformat() if collector.period_end else None
    result["timezone_offset_minutes"] = collector.timezone_offset_minutes
    result["targets"] = {
        "points": collector.target_points,
        "chests": collector.target_chests,
    }
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -v`
Expected: all tests PASS, including both new ones and every pre-existing test in the file (this is a purely additive change to the response dict).

- [ ] **Step 5: Commit**

```bash
git add server/chests.py server/tests/test_chests.py
git commit -m "feat(chests): pass season period, timezone, and targets through public summary response"
```

---

### Task 4: Deploy and verify

**Files:** none (deployment only)

- [ ] **Step 1: Push to main**

Run: `git push origin main`

- [ ] **Step 2: Deploy backend to GCP**

Run:
```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter && sleep 2 && sudo systemctl is-active totalhunter"
```
Expected output ends with `active`. No new migration in this plan — Task 1-3 are pure application-code changes on top of the columns Spec 1 already added and migrated.

- [ ] **Step 3: Live verification on production**

Run:
```bash
curl -s "http://34.68.86.57:8000/api/v1/chests/summary/m00bqgjcl1xqUHRDvEa8bQ" | head -c 800
```
Confirm the response now includes `"period_start"`, `"period_end"`, `"timezone_offset_minutes"`, `"targets"` keys (all `null`/`{"points": null, "chests": null}` for this real clan, since 229/BERS has not configured a season yet — confirming zero behavior change for it), and that the player list's totals are unchanged from before this deploy (no accidental filtering applied when period is unconfigured).

If the owner wants to see the date filter and quota count actually do something, that requires first setting a season + a quota toggle through `/dashboard/chests` (already shipped in Spec 1) — not part of this plan's verification, just a note for the next live demo.
