# Публичная страница «Древнего» + PlayerProfile fallback — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give clans that don't track Chests a no-auth public page (`/ancients/:slug`) where players self-report rank/troop composition (reusing the existing Chests public self-service mechanism) and see their computed quota/shortfall — and make sure that self-reported data actually feeds the real quota calculation, not just the display.

**Architecture:** Two small backend fallback fixes (`_roster_rows`, `calculate()`) make `PlayerProfile` a real data source for Ancients' quota math, not just its dashboard display. A new `server/ancients_public.py` exposes a single no-auth `GET /api/v1/ancients/public/{slug}` mirroring the read side of `_roster_rows` without the leader-only mapping fields. Writes reuse the existing `POST /api/v1/chests/public/player-profile` endpoint unchanged — no new mutation endpoint, since `PlayerProfile` and its collector are already shared between Chests and Ancients. Frontend adds one new route/page/table (modeled on `ChestSummaryPage.jsx`/`ChestSummaryTable.jsx`) and a dashboard link block (modeled on `ChestsPage.jsx`'s existing one).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, pytest + pytest-asyncio (SQLite in-memory), React (plain JSX, no test framework for `.jsx` files — verification is `npm run build`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-03-public-ancients-page-design.md` — this plan implements both Part A (PlayerProfile fallback) and Part Б (public page) in full.
- **No new database migration** — this feature uses only existing tables (`AncientRoster`, `PlayerProfile`, `AncientCalculation`, `ChestCollector`).
- The public GET endpoint must NOT expose `raw_ocr_name`, `mapped_name`, `suggested_name`, or `mapping_confirmed` — those are leader-only dashboard concerns.
- `PlayerProfile.troop_level` is writable through a *different, less strict* validator than Ancients requires (`chests.py`'s `_TROOP_RE` accepts tiers 1–9; Ancients' `parse_troop_level` in `ancient_quota.py` only accepts tiers 5–9). Any code that feeds a `PlayerProfile.troop_level` value into `parse_troop_level`/`split_strategy_b` MUST catch `ValueError` and treat that player as if they had no troop_level set (excluded), never crash the whole `calculate()` call for one bad value.
- Test auth pattern for `server/tests/test_ancients_dashboard.py`: `_create_user_with_token(db, email)` + `create_jwt` from `web_routes` (already in the file). The new public endpoint needs NO auth — no token in its tests.
- Route ordering is not a concern for this plan (no new dynamic-vs-static path collisions are introduced).
- No new pip/npm dependencies.

---

## File Map

| File | Change |
|---|---|
| `server/ancients_dashboard.py` | `_roster_rows` gets `PlayerProfile.rank` fallback (Task 1); `calculate()` Strategy B gets `PlayerProfile.troop_level` fallback with validation guard (Task 2) |
| `server/tests/test_ancients_dashboard.py` | Tests for both fallbacks |
| `server/ancients_public.py` | New file — `GET /api/v1/ancients/public/{slug}` |
| `server/tests/test_ancients_public.py` | New file — tests for the public endpoint |
| `server/main.py` | Register the new router |
| `server/ancients_dashboard.py` | `public_url` field added to `GET /web/dashboard/ancients` response (Task 4) |
| `web/src/lib/ancientQuota.js` | New file — `rowShortfallClass` extracted from `AncientsPage.jsx` so both the dashboard and the new public table can use it |
| `web/src/pages/AncientsPage.jsx` | Import `rowShortfallClass` from the new shared module instead of defining it locally; add «🔗 Публичная страница» link block |
| `web/src/pages/PublicAncientsPage.jsx` | New file — public page shell (modeled on `ChestSummaryPage.jsx`) |
| `web/src/components/AncientPublicTable.jsx` | New file — roster table with self-service rank/troop selects (modeled on `ChestSummaryTable.jsx`) |
| `web/src/api.js` | `fetchAncientsPublic(slug)` — new fetcher |
| `web/src/App.jsx` | Register `/ancients/:slug` route |

---

### Task 1: Backend — `PlayerProfile.rank` fallback in `_roster_rows`

**Files:**
- Modify: `server/ancients_dashboard.py` (`_roster_rows`, currently lines 135–209)
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Produces: `_roster_rows(...)` roster row dicts now report `"rank"` falling back to `PlayerProfile.rank` when `AncientRoster.rank` is `None`, and this same effective rank is used for Strategy-A per-row quota lookup (previously only the raw `AncientRoster.rank` was used for both).

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_ancients_dashboard.py` (near the other `_roster_rows`-adjacent tests, e.g. after `test_get_roster_raw_ocr_name_none_for_pure_chests_row`):

```python
@pytest.mark.asyncio
async def test_get_roster_rank_falls_back_to_player_profile(db_session):
    """A row with no AncientRoster.rank set falls back to PlayerProfile.rank
    (the same table players self-report through on the public Chests page),
    both in the displayed 'rank' field and in Strategy-A quota lookup."""
    from models import PlayerProfile
    user, token = await _create_user_with_token(db_session, "rankfallback1@test.com")
    collector = await _create_collector(db_session, user.id, slug="rankfallback-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Кузнецов",
                                 place=1, points=100, rank=None, source="ocr"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Кузнецов",
                                 rank="Офицер", troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/rankfallback-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        officer_quota = calc_resp.json()["result"]["officer_quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["rank"] == "Офицер"
    assert row["quota"] == pytest.approx(officer_quota)
```

- [ ] **Step 2: Run the test — verify it fails**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py::test_get_roster_rank_falls_back_to_player_profile -v`
Expected: FAIL — `row["rank"]` is `None` and `row["quota"]` is `None` (no fallback exists yet).

- [ ] **Step 3: Update `_roster_rows`**

Find:

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
```

Replace with (adds `PlayerProfile.rank`):

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
        select(AncientRoster, PlayerProfile.troop_level.label("profile_troop"),
               PlayerProfile.rank.label("profile_rank"))
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
```

Then find the quota-lookup block inside the loop:

```python
        quota = None
        if latest_calc is not None:
            if latest_calc.strategy == "A":
                rank = r.AncientRoster.rank
                if rank in OFFICER_RANKS:
```

Replace with (computes the effective rank once, reuses it below):

```python
        effective_rank = r.AncientRoster.rank or r.profile_rank

        quota = None
        if latest_calc is not None:
            if latest_calc.strategy == "A":
                rank = effective_rank
                if rank in OFFICER_RANKS:
```

Then find the `result.append({...})` block's `"rank"` line:

```python
            "rank": r.AncientRoster.rank,
```

Replace with:

```python
            "rank": effective_rank,
```

- [ ] **Step 4: Run the test — verify it passes**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py::test_get_roster_rank_falls_back_to_player_profile -v`
Expected: PASS

- [ ] **Step 5: Run the full test file — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -v --tb=short 2>&1 | tail -15`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): _roster_rows falls back to PlayerProfile.rank

Mirrors the troop_level fallback that already existed — a player who only
set their rank via the public Chests page (same PlayerProfile row) now
shows it in the Ancients dashboard too, and it feeds Strategy-A per-row
quota lookup, not just the display.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Backend — `PlayerProfile.troop_level` fallback in `calculate()` Strategy B, with validation guard

**Files:**
- Modify: `server/ancients_dashboard.py` (`calculate()`, Strategy B branch, currently lines 557–574)
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `parse_troop_level` (already imported from `ancient_quota`)
- Produces: `calculate()` with `strategy="B"` now includes players whose `AncientRoster.troop_level` is unset but `PlayerProfile.troop_level` is set (and valid for Ancients' 5–9 tier range); a value that fails `parse_troop_level` (e.g. written directly via the Chests public endpoint's laxer 1–9 validator) is treated as absent, never raises.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_calculate_strategy_b_uses_player_profile_troop_fallback(db_session):
    """A roster row with no AncientRoster.troop_level but a valid
    PlayerProfile.troop_level is included in the Strategy-B quota split —
    not silently excluded just because the leader never re-typed it."""
    from models import PlayerProfile
    user, token = await _create_user_with_token(db_session, "calcfallback1@test.com")
    collector = await _create_collector(db_session, user.id, slug="calcfallback-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 troop_level=None, source="manual"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Иванов",
                                 rank=None, troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/calcfallback-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    players = resp.json()["result"]["players"]
    assert len(players) == 1
    assert players[0]["name"] == "Иванов"
    assert players[0]["troop_level"] == "G8 S8 M8"
    assert resp.json()["result"]["excluded"] == []


@pytest.mark.asyncio
async def test_calculate_strategy_b_ignores_invalid_player_profile_troop(db_session):
    """A PlayerProfile.troop_level value that passes the laxer Chests
    validator (tiers 1-9) but fails Ancients' stricter parse_troop_level
    (tiers 5-9 only) must not crash calculate() — the player is excluded,
    same as if troop_level had never been set."""
    from models import PlayerProfile
    user, token = await _create_user_with_token(db_session, "calcfallback2@test.com")
    collector = await _create_collector(db_session, user.id, slug="calcfallback-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 troop_level=None, source="manual"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Петров",
                                 rank=None, troop_level="G3 S2 M4"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/calcfallback-2/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400  # no players with a valid troop_level at all
```

Note on the second test: with only one roster row and its only troop source being invalid, `split_strategy_b` raises `ValueError("no players with a troop_level set")`, which `calculate()` already turns into a 400 (see the existing `except ValueError as e: raise HTTPException(status_code=400, ...)` around the `split_strategy_b` call) — this proves the invalid value was excluded rather than crashing the request with a 500.

- [ ] **Step 2: Run the tests — verify they fail**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "player_profile_troop_fallback or invalid_player_profile_troop" -v`
Expected: FAIL — the first test fails because the player is currently excluded (`len(players) == 0`); the second test currently fails with a 500 (unhandled `ValueError` from `parse_troop_level` inside `split_strategy_b`, not caught since the value is passed through unvalidated today).

- [ ] **Step 3: Update `calculate()`'s Strategy B branch**

Find:

```python
        roster = (await db.execute(
            select(AncientRoster).where(AncientRoster.collector_id == collector.id)
        )).scalars().all()
        confirmed_mappings = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.confirmed == True,
            )
        )).scalars().all()
        mapped_names = {m.raw_ocr_name: m.canonical_name for m in confirmed_mappings}
        players = [(mapped_names.get(r.player_name, r.player_name), r.troop_level) for r in roster]
```

Replace with:

```python
        roster = (await db.execute(
            select(AncientRoster, PlayerProfile.troop_level.label("profile_troop"))
            .outerjoin(
                PlayerProfile,
                and_(
                    PlayerProfile.collector_id == AncientRoster.collector_id,
                    PlayerProfile.canonical_name == AncientRoster.player_name,
                )
            )
            .where(AncientRoster.collector_id == collector.id)
        )).all()
        confirmed_mappings = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.confirmed == True,
            )
        )).scalars().all()
        mapped_names = {m.raw_ocr_name: m.canonical_name for m in confirmed_mappings}
        players = []
        for r in roster:
            troop_level = r.AncientRoster.troop_level or r.profile_troop
            if troop_level is not None:
                try:
                    parse_troop_level(troop_level)
                except ValueError:
                    troop_level = None
            players.append((
                mapped_names.get(r.AncientRoster.player_name, r.AncientRoster.player_name),
                troop_level,
            ))
```

- [ ] **Step 4: Run the 2 new tests — verify they pass**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "player_profile_troop_fallback or invalid_player_profile_troop" -v`
Expected: 2 × PASS

- [ ] **Step 5: Run the full test file — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -v --tb=short 2>&1 | tail -15`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): calculate() Strategy B falls back to PlayerProfile.troop_level

Without this, a player who only entered their composition on the public
Ancients/Chests page (never re-typed by the leader in the dashboard) was
silently excluded from the real quota split — the crowdsourcing feature
looked like it worked (dashboard display already had this fallback) but
didn't actually feed the calculator. Guards against PlayerProfile values
that pass Chests' laxer tier-1-9 validator but fail Ancients' tier-5-9
parse_troop_level — such values are excluded, not a 500.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Backend — public `GET /api/v1/ancients/public/{slug}`

**Files:**
- Create: `server/ancients_public.py`
- Create: `server/tests/test_ancients_public.py`
- Modify: `server/main.py` (register the router)

**Interfaces:**
- Consumes: `AncientRoster`, `PlayerProfile`, `AncientCalculation`, `ChestCollector` (existing models); `OFFICER_RANKS`, `shortfall_pct` from `ancient_quota.py`
- Produces: `GET /api/v1/ancients/public/{slug}` → `{"kingdom": str, "clan": str, "quota_thresholds": {...}, "roster": [{"player_name", "rank", "troop_level", "points", "quota", "shortfall_pct"}]}`, no auth required, 404 if slug unknown.

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_ancients_public.py`:

```python
"""Tests for ancients_public.py — no-auth public roster page for «Древний»."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import (
    AncientCalculation, AncientRoster, ChestCollector, PlayerProfile, User,
)


async def _create_user(db):
    u = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6))
    db.add(u)
    await db.flush()
    return u


async def _create_collector(db, user_id, slug=None, clan="ClanA", **kwargs):
    collector = ChestCollector(kingdom="K1", clan=clan, user_id=user_id,
                               slug=slug or secrets.token_urlsafe(16), **kwargs)
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_public_ancients_404_for_unknown_slug(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_ancients_returns_roster_without_mapping_fields(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, rank="Офицер",
                                 troop_level="G8 S8 M8", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["kingdom"] == "K1"
    assert data["clan"] == "ClanA"
    row = data["roster"][0]
    assert row["player_name"] == "Иванов"
    assert row["rank"] == "Офицер"
    assert row["troop_level"] == "G8 S8 M8"
    assert row["points"] == 100
    assert "raw_ocr_name" not in row
    assert "mapped_name" not in row
    assert "suggested_name" not in row
    assert "mapping_confirmed" not in row


@pytest.mark.asyncio
async def test_public_ancients_falls_back_to_player_profile(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Сидоров",
                                 troop_level=None, rank=None, source="manual"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Сидоров",
                                 rank="Ветеран", troop_level="G7 S7 M7"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-2")
    row = resp.json()["roster"][0]
    assert row["rank"] == "Ветеран"
    assert row["troop_level"] == "G7 S7 M7"


@pytest.mark.asyncio
async def test_public_ancients_includes_quota_and_shortfall(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-3")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 points=50, rank="Глава", source="manual"))
    db_session.add(AncientCalculation(
        collector_id=collector.id, strategy="A", summon_levels=[81],
        amplification_coef=1.0, officer_count=1, veteran_count=0,
        total_quota_millions=100.0,
        result_json={"officer_quota": 100.0, "veteran_quota": 0.0},
    ))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-3")
    row = resp.json()["roster"][0]
    assert row["quota"] == pytest.approx(100.0)
    assert row["shortfall_pct"] == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_public_ancients_includes_quota_thresholds(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-4",
                                        ancient_shortfall_light_pct=15.0,
                                        ancient_shortfall_medium_pct=40.0,
                                        ancient_shortfall_critical_pct=70.0)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-4")
    assert resp.json()["quota_thresholds"] == {
        "light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0,
    }


@pytest.mark.asyncio
async def test_public_ancients_visible_even_when_hidden_from_owner_dashboard(db_session):
    """ancient_hidden only affects the owner's own dashboard list — it must
    not block public access, same as documented for set_ancient_visibility."""
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-5",
                                        ancient_hidden=True)
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Скрытый",
                                 source="manual"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-5")
    assert resp.status_code == 200
    assert len(resp.json()["roster"]) == 1
```

- [ ] **Step 2: Run the tests — verify they fail**

Run: `cd server && python -m pytest tests/test_ancients_public.py -v`
Expected: FAIL — `404 Not Found` for every test (the route doesn't exist yet; `ModuleNotFoundError` is not expected since the test file itself has no bad imports, only the HTTP calls fail).

- [ ] **Step 3: Create `server/ancients_public.py`**

```python
"""
ancients_public.py — публичная (без авторизации) страница «Древнего» для
кланов, которые не ведут учёт Сундуков, но хотят пользоваться калькулятором
квот. Аналог публичной части chests.py (GET /summary/{slug}), только для
ростера Древнего.

Запись данных игроками (звание/состав войск) идёт НЕ через этот файл, а
через уже существующий POST /api/v1/chests/public/player-profile —
PlayerProfile — общая таблица с Сундуками (тот же collector), новый
мутирующий эндпоинт не нужен.

Наружу не выставляются raw_ocr_name/mapped_name/suggested_name/
mapping_confirmed — это исключительно внутренний инструмент лидера в личном
кабинете (ancients_dashboard.py), не публичная информация.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ancient_quota import OFFICER_RANKS, shortfall_pct
from database import get_db
from models import AncientCalculation, AncientRoster, ChestCollector, PlayerProfile

router = APIRouter(prefix="/api/v1/ancients/public", tags=["ancients-public"])


@router.get("/{slug}")
async def get_public_ancients(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    latest_calc = (await db.execute(
        select(AncientCalculation)
        .where(AncientCalculation.collector_id == collector.id)
        .order_by(AncientCalculation.computed_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    rows = (await db.execute(
        select(AncientRoster, PlayerProfile.troop_level.label("profile_troop"),
               PlayerProfile.rank.label("profile_rank"))
        .outerjoin(
            PlayerProfile,
            and_(
                PlayerProfile.collector_id == AncientRoster.collector_id,
                PlayerProfile.canonical_name == AncientRoster.player_name,
            )
        )
        .where(AncientRoster.collector_id == collector.id)
        .order_by(AncientRoster.place.asc().nullslast())
    )).all()

    roster = []
    for r in rows:
        player_name = r.AncientRoster.player_name
        effective_rank = r.AncientRoster.rank or r.profile_rank
        effective_troop = r.AncientRoster.troop_level or r.profile_troop

        quota = None
        if latest_calc is not None:
            if latest_calc.strategy == "A":
                if effective_rank in OFFICER_RANKS:
                    quota = latest_calc.result_json.get("officer_quota")
                elif effective_rank is not None:
                    quota = latest_calc.result_json.get("veteran_quota")
            else:
                match = next(
                    (p for p in latest_calc.result_json.get("players", [])
                     if p["name"] == player_name),
                    None,
                )
                if match is not None:
                    quota = match["quota"]

        roster.append({
            "player_name": player_name,
            "rank": effective_rank,
            "troop_level": effective_troop,
            "points": r.AncientRoster.points,
            "quota": quota,
            "shortfall_pct": shortfall_pct(quota, r.AncientRoster.points),
        })

    return {
        "kingdom": collector.kingdom,
        "clan": collector.clan,
        "quota_thresholds": {
            "light_pct": collector.ancient_shortfall_light_pct if collector.ancient_shortfall_light_pct is not None else 10.0,
            "medium_pct": collector.ancient_shortfall_medium_pct if collector.ancient_shortfall_medium_pct is not None else 30.0,
            "critical_pct": collector.ancient_shortfall_critical_pct if collector.ancient_shortfall_critical_pct is not None else 60.0,
        },
        "roster": roster,
    }
```

- [ ] **Step 4: Register the router in `server/main.py`**

Find:

```python
from ancients_dashboard import router as ancients_dashboard_router
from tournaments import router as tournaments_router
```

Replace with:

```python
from ancients_dashboard import router as ancients_dashboard_router
from ancients_public import router as ancients_public_router
from tournaments import router as tournaments_router
```

Find:

```python
app.include_router(ancients_dashboard_router)
app.include_router(tournaments_router)
```

Replace with:

```python
app.include_router(ancients_dashboard_router)
app.include_router(ancients_public_router)
app.include_router(tournaments_router)
```

- [ ] **Step 5: Run the tests — verify they pass**

Run: `cd server && python -m pytest tests/test_ancients_public.py -v`
Expected: 6 × PASS

- [ ] **Step 6: Run the full backend suite — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest -q 2>&1 | tail -10`
Expected: all PASS (no failures).

- [ ] **Step 7: Commit**

```bash
git add server/ancients_public.py server/tests/test_ancients_public.py server/main.py
git commit -m "$(cat <<'EOF'
feat(ancients): public no-auth roster endpoint for clans without Chests

GET /api/v1/ancients/public/{slug} mirrors the read side of the dashboard's
_roster_rows (PlayerProfile fallback, quota/shortfall_pct) without the
leader-only mapping fields (raw_ocr_name/mapped_name/suggested_name/
mapping_confirmed). No write endpoint added — public self-report reuses
the existing POST /api/v1/chests/public/player-profile as-is, since
PlayerProfile and the collector are already shared with Chests.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Backend — `public_url` field on the dashboard collector list

**Files:**
- Modify: `server/ancients_dashboard.py` (`get_dashboard_ancients`, the `result.append({...})` block, currently lines 288–304)
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Produces: each collector entry in `GET /web/dashboard/ancients` now includes `"public_url": "https://total-hunter.com/ancients/{slug}"`.

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_dashboard_includes_public_url(db_session):
    user, token = await _create_user_with_token(db_session, "puburl1@test.com")
    await _create_collector(db_session, user.id, slug="puburl-slug-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    collector_data = resp.json()["collectors"][0]
    assert collector_data["public_url"] == "https://total-hunter.com/ancients/puburl-slug-1"
```

- [ ] **Step 2: Run the test — verify it fails**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py::test_get_dashboard_includes_public_url -v`
Expected: FAIL — `KeyError: 'public_url'`.

- [ ] **Step 3: Add the field**

Find:

```python
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
            "quota_thresholds": {
```

Replace with (adds `public_url` after `"clan"`):

```python
        result.append({
            "slug": collector.slug,
            "kingdom": collector.kingdom,
            "clan": collector.clan,
            "public_url": f"https://total-hunter.com/ancients/{collector.slug}",
            "is_owner": is_owner,
            "canonical_names": canonical_names,
            "roster": await _roster_rows(
                db, collector.id, mappings_dict, canonical_names, fuzzy_threshold,
                latest_calc),
            "history": await _history_rows(db, collector.id),
            "presets": sorted(VALID_PRESETS),
            "quota_thresholds": {
```

- [ ] **Step 4: Run the test — verify it passes**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py::test_get_dashboard_includes_public_url -v`
Expected: PASS

- [ ] **Step 5: Run the full test file — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -v --tb=short 2>&1 | tail -10`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): expose public_url on dashboard collector list

Matches chest_dashboard.py's existing public_url field, pointing at the
new /ancients/:slug route so the dashboard can render a share link.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Frontend — extract `rowShortfallClass` into a shared module

**Files:**
- Create: `web/src/lib/ancientQuota.js`
- Modify: `web/src/pages/AncientsPage.jsx` (currently defines `rowShortfallClass` locally, lines 45–50 per the last known state)

**Interfaces:**
- Produces: `rowShortfallClass(shortfallPct, thresholds) -> string` exported from `web/src/lib/ancientQuota.js`, consumed by both `AncientsPage.jsx` (Task after this one, unchanged behavior) and the new `AncientPublicTable.jsx` (Task 6).

- [ ] **Step 1: Create the shared module**

In `AncientsPage.jsx`, find the current local definition:

```javascript
function rowShortfallClass(shortfallPct, thresholds) {
  if (shortfallPct == null || !thresholds) return ''
  if (shortfallPct <= thresholds.light_pct) return ''
  if (shortfallPct <= thresholds.medium_pct) return 'row-quota-light'
  if (shortfallPct <= thresholds.critical_pct) return 'row-lagging'
  return 'row-danger'
}
```

Create `web/src/lib/ancientQuota.js` with exactly this function, exported:

```javascript
export function rowShortfallClass(shortfallPct, thresholds) {
  if (shortfallPct == null || !thresholds) return ''
  if (shortfallPct <= thresholds.light_pct) return ''
  if (shortfallPct <= thresholds.medium_pct) return 'row-quota-light'
  if (shortfallPct <= thresholds.critical_pct) return 'row-lagging'
  return 'row-danger'
}
```

- [ ] **Step 2: Remove the local definition from `AncientsPage.jsx` and import it instead**

Delete the local `function rowShortfallClass(...) { ... }` block shown above from `AncientsPage.jsx`.

Find the top-of-file imports:

```javascript
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'
```

Replace with (adds the new import):

```javascript
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'
import { rowShortfallClass } from '../lib/ancientQuota.js'
```

- [ ] **Step 3: Verify the build**

Run: `cd web && npm run build`
Expected: build succeeds with no errors (this confirms `rowShortfallClass` is still resolvable everywhere `AncientsPage.jsx` used it before — the call site at `className={rowShortfallClass(p.shortfall_pct, c.quota_thresholds)}` is unchanged, only where the function is defined moved).

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/ancientQuota.js web/src/pages/AncientsPage.jsx
git commit -m "$(cat <<'EOF'
refactor(ancients): extract rowShortfallClass into a shared module

Needed by the new public Ancients page (next commit) in addition to the
dashboard — avoids a second copy of the same threshold logic.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Frontend — public page + table + route + API fetcher

**Files:**
- Modify: `web/src/api.js`
- Create: `web/src/components/AncientPublicTable.jsx`
- Create: `web/src/pages/PublicAncientsPage.jsx`
- Modify: `web/src/App.jsx`

**Interfaces:**
- Consumes: `GET /api/v1/ancients/public/{slug}` (Task 3), `postPublicPlayerProfile` (existing, `web/src/api.js`), `rowShortfallClass` (Task 5)
- Produces: route `/ancients/:slug` renders `PublicAncientsPage`

- [ ] **Step 1: Add the API fetcher**

In `web/src/api.js`, find:

```javascript
export async function fetchChestByKingdomSlug(kingdom, slug) {
  const res = await fetch(`${BASE}/api/v1/chests/by/${encodeURIComponent(kingdom)}/${encodeURIComponent(slug)}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}
```

Add immediately after it:

```javascript
export async function fetchAncientsPublic(slug) {
  const res = await fetch(`${BASE}/api/v1/ancients/public/${encodeURIComponent(slug)}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}
```

- [ ] **Step 2: Create `web/src/components/AncientPublicTable.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'
import { rowShortfallClass } from '../lib/ancientQuota.js'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TIERS = ['', '5', '6', '7', '8', '9']

function parseTroop(troop_level) {
  if (!troop_level) return { g: '', s: '', m: '' }
  const mat = troop_level.match(/G(\d+) S(\d+) M(\d+)/)
  return mat ? { g: mat[1], s: mat[2], m: mat[3] } : { g: '', s: '', m: '' }
}

export default function AncientPublicTable({ roster, quotaThresholds, editMode, collectorSlug }) {
  const [editRows, setEditRows] = useState({})
  const [saving, setSaving] = useState(null)
  const [savedRows, setSavedRows] = useState({})

  useEffect(() => {
    if (!editMode) return
    const init = {}
    roster.forEach(p => {
      const { g, s, m } = parseTroop(p.troop_level)
      init[p.player_name] = { rank: p.rank || '', g, s, m }
    })
    setEditRows(init)
  }, [editMode, roster])

  async function handleSave(playerName) {
    const row = editRows[playerName] || {}
    const troop = row.g && row.s && row.m ? `G${row.g} S${row.s} M${row.m}` : null
    setSaving(playerName)
    try {
      await postPublicPlayerProfile(collectorSlug, playerName, row.rank || null, troop)
      setSavedRows(prev => ({ ...prev, [playerName]: true }))
      setTimeout(() => setSavedRows(prev => { const n = { ...prev }; delete n[playerName]; return n }), 3000)
    } catch (e) {
      alert('Ошибка сохранения: ' + e.message)
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="public-table-wrap">
      <table className="public-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Имя</th>
            <th>Звание</th>
            <th>Войска</th>
            {editMode && <th></th>}
            <th>Очки</th>
            <th>Квота</th>
            <th>Недобор</th>
          </tr>
        </thead>
        <tbody>
          {roster.map((p, i) => (
            <tr key={p.player_name} className={rowShortfallClass(p.shortfall_pct, quotaThresholds)}>
              <td>{i + 1}</td>
              <td title={p.player_name}>{p.player_name}</td>
              <td>
                {editMode ? (
                  <select
                    value={editRows[p.player_name]?.rank || ''}
                    onChange={e => setEditRows(prev => ({
                      ...prev,
                      [p.player_name]: { ...prev[p.player_name], rank: e.target.value },
                    }))}
                    style={{ fontSize: 12, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                  >
                    {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                  </select>
                ) : (p.rank || '—')}
              </td>
              <td>
                {editMode ? (
                  <div style={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'nowrap' }}>
                    {['g', 's', 'm'].map((k, idx) => (
                      <select
                        key={k}
                        value={editRows[p.player_name]?.[k] || ''}
                        onChange={e => setEditRows(prev => ({
                          ...prev,
                          [p.player_name]: { ...prev[p.player_name], [k]: e.target.value },
                        }))}
                        style={{ fontSize: 11, padding: '2px 2px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4, width: 36 }}
                      >
                        <option value="">{'GSM'[idx]}</option>
                        {TIERS.slice(1).map(v => <option key={v} value={v}>{v}</option>)}
                      </select>
                    ))}
                  </div>
                ) : (p.troop_level || '—')}
              </td>
              {editMode && (
                <td>
                  <button
                    onClick={() => handleSave(p.player_name)}
                    disabled={saving === p.player_name}
                    style={{ fontSize: 12, padding: '2px 8px', cursor: 'pointer',
                      background: savedRows[p.player_name] ? '#1e3a1e' : '#313244',
                      color: savedRows[p.player_name] ? '#a6e3a1' : '#cdd6f4',
                      border: `1px solid ${savedRows[p.player_name] ? '#a6e3a1' : '#45475a'}`, borderRadius: 4 }}
                  >
                    {saving === p.player_name ? '...' : savedRows[p.player_name] ? '✓' : '💾'}
                  </button>
                </td>
              )}
              <td>{p.points ?? '—'}</td>
              <td>{p.quota != null ? p.quota.toFixed(2) : '—'}</td>
              <td>{p.shortfall_pct != null ? `${p.shortfall_pct.toFixed(1)}%` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 3: Create `web/src/pages/PublicAncientsPage.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchAncientsPublic } from '../api.js'
import AncientPublicTable from '../components/AncientPublicTable.jsx'

export default function PublicAncientsPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [editMode, setEditMode] = useState(false)

  useEffect(() => {
    fetchAncientsPublic(slug).then(setData).catch(e => setError(e.message || 'not found'))
  }, [slug])

  if (error) return <div className="page-content">{error}</div>
  if (!data) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h1 className="public-summary-title">
        <span className="public-kingdom-label">{data.kingdom}/</span>
        <span className="public-clan-label">{data.clan}</span>
      </h1>

      <div className="public-season-info">
        <button
          className="btn-secondary"
          style={{ fontSize: 13, padding: '4px 12px', marginLeft: 'auto' }}
          onClick={() => {
            if (editMode) { setEditMode(false); fetchAncientsPublic(slug).then(setData) }
            else { setEditMode(true) }
          }}
        >
          {editMode ? '✕ Закрыть' : '✏️ Ввести состав'}
        </button>
      </div>

      <div className="public-summary-divider" />

      <AncientPublicTable
        roster={data.roster}
        quotaThresholds={data.quota_thresholds}
        editMode={editMode}
        collectorSlug={slug}
      />
    </div>
  )
}
```

- [ ] **Step 4: Register the route**

In `web/src/App.jsx`, find:

```jsx
import ChestSummaryPage from './pages/ChestSummaryPage.jsx'
import AncientsPage from './pages/AncientsPage.jsx'
```

Replace with:

```jsx
import ChestSummaryPage from './pages/ChestSummaryPage.jsx'
import PublicAncientsPage from './pages/PublicAncientsPage.jsx'
import AncientsPage from './pages/AncientsPage.jsx'
```

Find:

```jsx
      <Route path="/chests/:slug" element={<ChestSummaryPage />} />
      <Route path="/c/:kingdom/:slug" element={<ChestSummaryPage />} />
```

Replace with:

```jsx
      <Route path="/chests/:slug" element={<ChestSummaryPage />} />
      <Route path="/c/:kingdom/:slug" element={<ChestSummaryPage />} />
      <Route path="/ancients/:slug" element={<PublicAncientsPage />} />
```

- [ ] **Step 5: Verify the build**

Run: `cd web && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/api.js web/src/components/AncientPublicTable.jsx web/src/pages/PublicAncientsPage.jsx web/src/App.jsx
git commit -m "$(cat <<'EOF'
feat(ancients): public self-service page at /ancients/:slug

Modeled directly on ChestSummaryPage.jsx/ChestSummaryTable.jsx — same
rank/troop selects, same 💾-to-✓ save button, same alert() surfacing the
15-minute cooldown from the shared POST /api/v1/chests/public/player-profile
endpoint (no new write endpoint). Adds Квота/Недобор columns with the same
threshold-based row highlighting as the leader's dashboard.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Frontend — «🔗 Публичная страница» link in the dashboard

**Files:**
- Modify: `web/src/pages/AncientsPage.jsx`

**Interfaces:**
- Consumes: `c.public_url` (Task 4)

- [ ] **Step 1: Add the link block**

Find (the collector card header):

```jsx
            <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600 }}>{c.kingdom} / {c.clan}</span>
```

Replace with (adds the link right after the kingdom/clan label):

```jsx
            <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600 }}>{c.kingdom} / {c.clan}</span>
              {c.public_url && (
                <a href={c.public_url} target="_blank" rel="noreferrer"
                   style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
                  {cx.publicLink}
                </a>
              )}
```

(`cx.publicLink` already exists — `dashboard_content.js:78` → `'Публичная страница клана'`, `dashboard_content.en.js:78` → `'Clan public page'`. It's a generic label already used by the Chests dashboard for the same purpose; no new i18n key needed.)

- [ ] **Step 2: Verify the build**

Run: `cd web && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/AncientsPage.jsx
git commit -m "$(cat <<'EOF'
feat(ancients): 🔗 public page link in the dashboard collector card

Reuses the existing cx.publicLink label already shown on the Chests
dashboard for the same purpose.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Deploy

**Files:** none (infra only)

- [ ] **Step 1: Push to main**

```bash
git push origin main
```

- [ ] **Step 2: GCP — restart (no migration needed — this plan adds no DB columns)**

```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter && sleep 3 && systemctl is-active totalhunter"
```

Expected: `active`.

- [ ] **Step 3: Vercel deploy + alias**

```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```

Wait for `READY`, then attach alias — standard 3-step procedure from `CLAUDE.md` §6.5.

- [ ] **Step 4: Smoke test**

1. Открыть `https://total-hunter.com/dashboard/ancients` — под названием клана появилась ссылка «Публичная страница клана».
2. Перейти по ней (`https://total-hunter.com/ancients/{slug}`) — таблица с ростером видна без входа в аккаунт.
3. Нажать «✏️ Ввести состав» — появились селекторы звания/войск, кнопка 💾.
4. Заполнить и сохранить — кнопка на 3 сек стала ✓, при обновлении страницы значение осталось.
5. Повторное сохранение той же строки сразу — `alert()` с текстом про кулдаун.
6. В личном кабинете (авторизованном) на вкладке «Древний» — только что введённые звание/состав видны в таблице ростера, и (если для клана есть последний расчёт квоты) участвуют в колонке «Квота».

---

## Self-Review Notes

- **Spec coverage:** Часть A (fallback `PlayerProfile.rank` в `_roster_rows`, fallback `PlayerProfile.troop_level` в `calculate()` со страховкой от рассинхрона диапазонов тиров) — Tasks 1–2. Часть Б (публичный GET, переиспользование существующего POST на запись, фронтенд-страница+таблица+роут, ссылка в кабинете) — Tasks 3–4, 6–7. Общий вынесенный хелпер `rowShortfallClass` — Task 5 (создан отдельной задачей, так как оба потребителя — Task 6 и уже существующий код — должны получить идентичный, не задублированный источник).
- **Placeholder scan:** none — каждый шаг содержит финальный код или точную команду.
- **Type consistency:** `rowShortfallClass(shortfallPct, thresholds)` определена в Task 5, используется без изменения сигнатуры в Task 6 (`AncientPublicTable.jsx`) и в уже существующем вызове в `AncientsPage.jsx`. Поля публичного ответа (`player_name`/`rank`/`troop_level`/`points`/`quota`/`shortfall_pct`) идентичны между Task 3 (бэкенд) и Task 6 (фронтенд-потребление в `AncientPublicTable.jsx`) — без расхождений в написании. `public_url` как имя поля идентично между Task 4 (бэкенд) и Task 7 (фронтенд).
- **Валидационная страховка (Global Constraints)** явно покрыта отдельным тестом в Task 2
  (`test_calculate_strategy_b_ignores_invalid_player_profile_troop`), а не только упомянута в тексте.
