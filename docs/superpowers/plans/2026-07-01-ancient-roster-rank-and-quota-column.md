# Ancient Roster Rank Editing + Quota Column Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let clan leaders edit a player's rank directly in the Ancient roster table
(currently only settable via the manual-add form), and show each player's computed
quota from the latest calculation as a new "Квота" column in that same table.

**Architecture:** Backend adds a `PATCH /{slug}/rank` endpoint mirroring the existing
`PATCH /{slug}/troop-level`, plus a per-row `quota` resolution in `_roster_rows()` that
reads the collector's most recent `AncientCalculation` (fetched once, not per row) and
maps Strategy A ranks to `officer_quota`/`veteran_quota` or looks up Strategy B's
per-player `quota` by name. Frontend adds a rank `<select>` and a read-only quota
column mirroring the existing troop-level UI pattern.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, pytest + pytest-asyncio, React
(no build step / plain JSX, no test framework for this file — matches existing project
convention of no automated frontend tests for `/dashboard` pages).

## Global Constraints

- Rank bucket mapping (from the spec, exact and final): `Глава`, `Старший`, `Офицер` →
  `officer_quota`; `Ветеран`, `Рядовой` → `veteran_quota`; rank `None` → quota `None`.
- This is display-only — does NOT reconcile or change the manually-entered
  `officer_count`/`veteran_count` used by the actual Strategy A calculation.
- `POST /{slug}/roster/manual`'s existing `rank` field validation is unchanged (out of
  scope per the spec).
- No automated frontend test layer for this file (matches existing project convention).

---

### Task 1: Backend — rank endpoint + quota resolution

**Files:**
- Modify: `server/ancient_quota.py` (add `RANKS`, `OFFICER_RANKS` constants)
- Modify: `server/ancients_dashboard.py:21-24` (import), `:74-117` (`_roster_rows`),
  `:135-200` (`get_dashboard_ancients`), add new `PATCH /{slug}/rank` route
- Test: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `AncientCalculation` model (already imported), `VALID_PRESETS`/
  `parse_troop_level` from `ancient_quota.py` (already wired from the prior plan).
- Produces: `RANKS: list[str]`, `OFFICER_RANKS: set[str]` (importable from
  `ancient_quota.py`); `_roster_rows(db, collector_id, mappings_dict, canonical_names,
  fuzzy_threshold, latest_calc)` — note the new required 6th parameter
  `latest_calc: Optional[AncientCalculation]`; each roster row dict now includes
  `"rank"` and `"quota"` keys.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py`, near the existing
`test_patch_troop_level` test:

```python
@pytest.mark.asyncio
async def test_patch_rank_saves_value(db_session):
    user, token = await _create_user_with_token(db_session, "rank1@test.com")
    collector = await _create_collector(db_session, user.id, slug="rank-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/rank-1/rank",
            json={"player_name": "Петров", "rank": "Офицер"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.rank == "Офицер"


@pytest.mark.asyncio
async def test_patch_rank_rejects_unknown_value(db_session):
    user, token = await _create_user_with_token(db_session, "rank2@test.com")
    collector = await _create_collector(db_session, user.id, slug="rank-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/rank-2/rank",
            json={"player_name": "Петров", "rank": "Новичок"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_patch_rank_404_for_unknown_player(db_session):
    user, token = await _create_user_with_token(db_session, "rank3@test.com")
    collector = await _create_collector(db_session, user.id, slug="rank-3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/rank-3/rank",
            json={"player_name": "НетТакого", "rank": "Офицер"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_roster_get_includes_rank_field(db_session):
    user, token = await _create_user_with_token(db_session, "rankget1@test.com")
    collector = await _create_collector(db_session, user.id, slug="rankget-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, rank="Ветеран"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["rank"] == "Ветеран"


@pytest.mark.asyncio
async def test_roster_quota_strategy_a_officer_bucket(db_session):
    user, token = await _create_user_with_token(db_session, "quotaA1@test.com")
    collector = await _create_collector(db_session, user.id, slug="quota-a-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Глава1",
                                 place=1, points=100, rank="Глава"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Рядовой1",
                                 place=2, points=50, rank="Рядовой"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="БезЗвания",
                                 place=3, points=10, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/quota-a-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        officer_quota = calc_resp.json()["result"]["officer_quota"]
        veteran_quota = calc_resp.json()["result"]["veteran_quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    roster = {p["player_name"]: p for p in resp.json()["collectors"][0]["roster"]}
    assert roster["Глава1"]["quota"] == pytest.approx(officer_quota)
    assert roster["Рядовой1"]["quota"] == pytest.approx(veteran_quota)
    assert roster["БезЗвания"]["quota"] is None


@pytest.mark.asyncio
async def test_roster_quota_strategy_b_matches_by_name(db_session):
    user, token = await _create_user_with_token(db_session, "quotaB1@test.com")
    collector = await _create_collector(db_session, user.id, slug="quota-b-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="БезВойск",
                                 place=2, points=50, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/quota-b-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        ivanov_quota = calc_resp.json()["result"]["players"][0]["quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    roster = {p["player_name"]: p for p in resp.json()["collectors"][0]["roster"]}
    assert roster["Иванов"]["quota"] == pytest.approx(ivanov_quota)
    assert roster["БезВойск"]["quota"] is None


@pytest.mark.asyncio
async def test_roster_quota_none_when_no_calculation_yet(db_session):
    user, token = await _create_user_with_token(db_session, "quotanone1@test.com")
    collector = await _create_collector(db_session, user.id, slug="quota-none-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, rank="Глава", troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["quota"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "rank or quota" -v`
Expected: FAIL — `PATCH /{slug}/rank` doesn't exist (404 instead of 200/400/404-by-design),
roster rows have no `"rank"`/`"quota"` keys (`KeyError` in assertions).

- [ ] **Step 3: Add `RANKS`/`OFFICER_RANKS` to `ancient_quota.py`**

Append to the end of `server/ancient_quota.py` (after `split_strategy_b`):

```python
RANKS: list[str] = ["Глава", "Старший", "Офицер", "Ветеран", "Рядовой"]
OFFICER_RANKS: set[str] = {"Глава", "Старший", "Офицер"}
```

- [ ] **Step 4: Add the `PATCH /{slug}/rank` endpoint**

Modify the import at `server/ancients_dashboard.py:21-24` from:
```python
from ancient_quota import (
    ANCIENT_LEVEL_HP, VALID_PRESETS, parse_troop_level,
    split_strategy_a, split_strategy_b, total_quota_millions,
)
```
to:
```python
from ancient_quota import (
    ANCIENT_LEVEL_HP, OFFICER_RANKS, RANKS, VALID_PRESETS, parse_troop_level,
    split_strategy_a, split_strategy_b, total_quota_millions,
)
```

Add this new route immediately after the existing `patch_troop_level` function (which
ends at `server/ancients_dashboard.py:251` with `return {"ok": True}`):

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

- [ ] **Step 5: Wire `rank` + `quota` into `_roster_rows` and its caller**

Replace `server/ancients_dashboard.py:74-117` (the entire `_roster_rows` function) with:

```python
async def _roster_rows(
    db: AsyncSession,
    collector_id: int,
    mappings_dict: dict,        # raw_ocr_name → AncientNameMapping
    canonical_names: list,
    fuzzy_threshold: float,
    latest_calc,                # Optional[AncientCalculation]
) -> list:
    rows = (await db.execute(
        select(AncientRoster, PlayerProfile.troop_level.label("profile_troop"))
        .outerjoin(
            PlayerProfile,
            and_(
                PlayerProfile.collector_id == AncientRoster.collector_id,
                PlayerProfile.canonical_name == AncientRoster.player_name,
            )
        )
        .where(AncientRoster.collector_id == collector_id)
        .order_by(AncientRoster.place.asc().nullslast())
    )).all()

    result = []
    for r in rows:
        raw = r.AncientRoster.player_name
        mapping = mappings_dict.get(raw)
        if mapping and mapping.confirmed:
            mapped_name = mapping.canonical_name
            suggested_name = None
            confirmed = True
        else:
            mapped_name = None
            matches = get_close_matches(raw, canonical_names, n=1, cutoff=fuzzy_threshold)
            suggested_name = matches[0] if matches else None
            confirmed = False

        quota = None
        if latest_calc is not None:
            if latest_calc.strategy == "A":
                rank = r.AncientRoster.rank
                if rank in OFFICER_RANKS:
                    quota = latest_calc.result_json.get("officer_quota")
                elif rank is not None:
                    quota = latest_calc.result_json.get("veteran_quota")
            else:
                lookup_name = mapped_name if confirmed else raw
                match = next(
                    (p for p in latest_calc.result_json.get("players", [])
                     if p["name"] == lookup_name),
                    None,
                )
                if match is not None:
                    quota = match["quota"]

        result.append({
            "player_name": raw,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
            "rank": r.AncientRoster.rank,
            "quota": quota,
            "mapped_name": mapped_name,
            "suggested_name": suggested_name,
            "mapping_confirmed": confirmed,
            "is_alias_source": suggested_name is not None,  # True = авто-найдено из Сундуков
        })
    return result
```

Modify `get_dashboard_ancients` (`server/ancients_dashboard.py:135-200`): inside the
`for collector, is_owner in all_pairs:` loop (right after the existing `mappings_dict =
{m.raw_ocr_name: m for m in mappings}` line), add a fetch of the latest calculation and
pass it through:

```python
        latest_calc = (await db.execute(
            select(AncientCalculation)
            .where(AncientCalculation.collector_id == collector.id)
            .order_by(AncientCalculation.computed_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        result.append({
            "slug": collector.slug,
            "kingdom": collector.kingdom,
            "clan": collector.clan,
            "is_owner": is_owner,
            "canonical_names": canonical_names,
            "roster": await _roster_rows(
                db, collector.id, mappings_dict, canonical_names, fuzzy_threshold,
                latest_calc),
            "history": await _history_rows(db, collector.id),
            "presets": sorted(VALID_PRESETS),
        })
```

(This replaces the existing `result.append({...})` block that calls `_roster_rows`
without the `latest_calc` argument — the only change inside it is adding the
`latest_calc` fetch above it and passing `latest_calc` as `_roster_rows`'s 6th
positional argument.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -v`
Expected: PASS — full file green, including all 7 new tests and every pre-existing test
(`test_roster_uses_profile_troop_level_as_fallback`, `test_calculate_strategy_b_uses_confirmed_mapped_name`,
etc. — none of them assert on `rank`/`quota` keys being absent, so adding new keys to
the roster row dict doesn't break them).

- [ ] **Step 7: Commit**

```bash
git add server/ancient_quota.py server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): PATCH /rank endpoint + per-row quota resolution

Roster rows now expose rank and a resolved quota from the most recent
calculation (Strategy A via rank->officer/veteran bucket, Strategy B via
per-player name lookup), fetched once per collector rather than per row.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Frontend — rank select + quota column

**Files:**
- Modify: `web/src/api.js` (add `dashboardAncientsRank`)
- Modify: `web/src/pages/AncientsPage.jsx` (add `handleRankChange`, rank `<select>`,
  quota `<td>`, two new `<th>`)
- Modify: `web/src/dashboard_content.js`, `web/src/dashboard_content.en.js` (add
  `rank`/`quota` i18n keys)

**Interfaces:**
- Consumes: `PATCH /{slug}/rank` and the `rank`/`quota` fields on each roster row from
  Task 1.
- Produces: nothing consumed by later tasks — this is the final integration point for
  this plan.

- [ ] **Step 1: Add the API call**

In `web/src/api.js`, add this line immediately after `dashboardAncientsTroopLevel`
(currently at line 61-63):

```javascript
  dashboardAncientsRank: (slug, playerName, rank) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/rank`,
            { player_name: playerName, rank }),
```

- [ ] **Step 2: Add i18n keys**

In `web/src/dashboard_content.js`, modify line 92 from:
```javascript
    player: 'Игрок', place: 'Место', points: 'Очки', troopLevel: 'Состав',
```
to:
```javascript
    player: 'Игрок', place: 'Место', points: 'Очки', troopLevel: 'Состав',
    rank: 'Звание', quota: 'Квота',
```

In `web/src/dashboard_content.en.js`, modify line 92 from:
```javascript
    player: 'Player', place: 'Place', points: 'Points', troopLevel: 'Composition',
```
to:
```javascript
    player: 'Player', place: 'Place', points: 'Points', troopLevel: 'Composition',
    rank: 'Rank', quota: 'Quota',
```

- [ ] **Step 3: Add `handleRankChange` handler**

In `web/src/pages/AncientsPage.jsx`, add this function immediately after
`handleTroopLevelChange` (currently `AncientsPage.jsx:152-159`):

```javascript
  async function handleRankChange(slug, playerName, rank) {
    try {
      await api.dashboardAncientsRank(slug, playerName, rank || null)
      refresh()
    } catch (e) {
      alert(e.message || 'Ошибка сохранения')
    }
  }
```

- [ ] **Step 4: Add table headers**

Modify `web/src/pages/AncientsPage.jsx:521-523` from:
```javascript
                      <th>{cx.points}</th>
                      <th>{cx.troopLevel}</th>
                      <th></th>
```
to:
```javascript
                      <th>{cx.points}</th>
                      <th>{cx.troopLevel}</th>
                      <th>{cx.rank}</th>
                      <th>{cx.quota}</th>
                      <th></th>
```

- [ ] **Step 5: Add the rank select and quota cell**

Modify `web/src/pages/AncientsPage.jsx` — insert two new `<td>` elements immediately
after the closing `</td>` of the troop-level cell (currently ending at line 603, right
before the `<td>` that starts the delete-button column at line 604):

```javascript
                          <td>
                            <select className="input-dark" value={p.rank || ''}
                              style={{ width: 100 }}
                              onChange={e => handleRankChange(c.slug, p.player_name, e.target.value)}>
                              {RANKS.map(r => <option key={r} value={r}>{r || cx.noTroopLevel}</option>)}
                            </select>
                          </td>
                          <td>{p.quota != null ? fmtNum(p.quota, 2) : '—'}</td>
```

- [ ] **Step 6: Manual verification (no automated frontend test layer for this page)**

Run: `cd web && npm run build`
Expected: build succeeds with no errors (confirms no syntax errors, unused-variable
lint failures, etc. introduced by the new JSX).

- [ ] **Step 7: Commit**

```bash
git add web/src/api.js web/src/pages/AncientsPage.jsx web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "$(cat <<'EOF'
feat(ancients): editable rank + quota column in roster table

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

## Self-Review Notes

- Spec coverage: `PATCH /rank` endpoint (Task 1 Step 4), `_roster_rows`
  rank+quota fields (Task 1 Step 5), latest-calculation single-fetch wiring (Task 1
  Step 5), Strategy A bucket mapping and Strategy B name lookup (both in the same
  step, matching the spec's exact table), frontend rank select + quota column (Task 2
  Steps 3-5), i18n keys (Task 2 Step 2) — all covered. Manual-entry endpoint validation
  explicitly left untouched per spec's "не входит" section — no task touches it.
- Placeholder scan: none found — every step has literal code/commands.
- Type consistency: `_roster_rows(db, collector_id, mappings_dict, canonical_names,
  fuzzy_threshold, latest_calc)` signature is used identically in its definition (Task
  1 Step 5) and its call site (same step) — the added 6th parameter is threaded through
  correctly. `RANKS`/`OFFICER_RANKS` defined in `ancient_quota.py` (Task 1 Step 3) and
  imported with matching names in `ancients_dashboard.py` (Task 1 Step 4). Frontend's
  `RANKS` constant (`AncientsPage.jsx:14`) already exists from prior work and is reused
  as-is, not redefined.
