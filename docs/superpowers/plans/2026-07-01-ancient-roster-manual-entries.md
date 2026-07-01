# Ancient Roster Manual Entries + Chests-Based Name Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the quota-calculation table show a leader's already-confirmed
player name instead of raw OCR text, and let a leader or trusted editor
manually add an Ancient roster participant (name + rank + troop composition)
who never appeared in the tournament OCR scan or the Chests name base — with
an auto-expiry tied to the game's "Trade Routes" event so stale manual
entries don't linger forever.

**Architecture:** `AncientRoster` gets three new columns
(`source`, `manual_expires_at`, `rank`). A new pure helper in `server/roy.py`
(`next_trade_routes_end()`) computes the manual-entry expiry deterministically
from the existing Trade-Routes cycle constants — no new scheduling state.
A new endpoint creates manual rows after a fuzzy-duplicate check against
`PlayerAlias.canonical_name`. The existing tournament-import full-replace
cascade is taught to skip manual rows and to "promote" one to a normal OCR
row (clearing its expiry) the moment real tournament data arrives for that
name. The existing daily Ancient-retention tick gets one more query: delete
expired, still-manual rows. The quota calculator resolves confirmed name
mappings before building its player list.

**Tech Stack:** FastAPI, SQLAlchemy async (asyncpg in prod, aiosqlite in
tests), Alembic, pytest + pytest-asyncio + httpx `AsyncClient`/`ASGITransport`,
React (Vite), vanilla `fetch`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-01-ancient-roster-manual-entries-design.md`
  — every task implements one part of it.
- `rank` on `AncientRoster` is display-only. Never wire it into
  `ancient_quota.py`'s `split_strategy_a`/`split_strategy_b` — neither
  strategy is per-player-rank-based today (A takes plain
  `officer_count`/`veteran_count`, B takes `troop_level`), and that does not
  change in this plan.
- Manual-entry duplicate protection is fuzzy-match (`difflib.get_close_matches`,
  cutoff=0.75) against `PlayerAlias.canonical_name` for the same collector —
  mirrors the cutoff already used everywhere else in this module
  (`ancients_dashboard.py`, `tournaments.py`). Do not invent a different
  threshold.
- The manual-add endpoint is owner-or-editor (`_get_own_or_editor_collector`),
  matching `troop-level` and `name-mappings` — not owner-only.
- Days/hours are plain arithmetic against the existing
  `_EVENT_ANCHOR_TS`/`_EVENT_CYCLE_H`/`_EVENT_DURATION_H` constants in
  `server/roy.py`. Do not introduce a second, separate schedule constant set.
- Run tests locally with `JWT_SECRET_KEY` set:
  `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/ -q`
- This repo has ~33 pre-existing unrelated test failures in
  `test_chests.py`/`test_roy.py`/`test_version_bump.py` (confirmed pre-existing
  in an earlier session, unrelated to this feature). Do not touch them; only
  verify the files you change stay green plus the overall pass count doesn't
  drop.
- Do not run `alembic upgrade head` against the real GCP database or restart
  `totalhunter.service` as part of this plan — that is a separate,
  explicitly-approved step at the end.

---

## Task 1: `AncientRoster` gets `source`/`manual_expires_at`/`rank` columns

**Files:**
- Modify: `server/models.py:578-596` (`AncientRoster` class)
- Create: `server/alembic/versions/m1n2u3a4l5r6_add_ancient_roster_manual_fields.py`
- Test: `server/tests/test_ancients_dashboard.py` (one smoke test that the
  columns exist and default correctly via the API)

**Interfaces:**
- Produces: `AncientRoster.source` (`str`, default `'ocr'`),
  `AncientRoster.manual_expires_at` (`Optional[datetime]`, timezone-aware),
  `AncientRoster.rank` (`Optional[str]`). Every later task in this plan reads
  or writes these exact attribute names.

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_ocr_roster_rows_default_to_ocr_source(db_session):
    """Existing (pre-manual-entries) rows created the normal way default to
    source='ocr' with no manual expiry — the new columns don't break the
    existing tournament-import path."""
    user, token = await _create_user_with_token(db_session, "sourcedefault1@test.com")
    collector = await _create_collector(db_session, user.id, slug="source-default-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100))
    await db_session.commit()

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.source == "ocr"
    assert row.manual_expires_at is None
    assert row.rank is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py::test_ocr_roster_rows_default_to_ocr_source -q`
Expected: FAIL — `AttributeError: 'AncientRoster' object has no attribute 'source'`

- [ ] **Step 3: Add the columns to the model**

In `server/models.py`, `class AncientRoster`, replace:

```python
    id            = Column(Integer, primary_key=True)
    collector_id  = Column(Integer, ForeignKey("chest_collectors.id"),
                           nullable=False, index=True)
    player_name   = Column(String(100), nullable=False)
    place         = Column(Integer, nullable=True)
    points        = Column(BigInteger, nullable=True)
    troop_level   = Column(String(20), nullable=True)
    updated_at    = Column(TIMESTAMP(timezone=True), nullable=False,
                           server_default=func.now())
```

with:

```python
    id                 = Column(Integer, primary_key=True)
    collector_id       = Column(Integer, ForeignKey("chest_collectors.id"),
                                nullable=False, index=True)
    player_name        = Column(String(100), nullable=False)
    place              = Column(Integer, nullable=True)
    points             = Column(BigInteger, nullable=True)
    troop_level        = Column(String(20), nullable=True)
    source             = Column(String(8), nullable=False, server_default=text("'ocr'"))
    manual_expires_at  = Column(TIMESTAMP(timezone=True), nullable=True)
    rank               = Column(String(20), nullable=True)
    updated_at         = Column(TIMESTAMP(timezone=True), nullable=False,
                                server_default=func.now())
```

(`text` is already imported at the top of `models.py` — confirm with
`grep -n "^from sqlalchemy import" server/models.py`, it's used by
`leader_excluded_catalog_ids` and `ancient_hidden` already.)

- [ ] **Step 4: Write the migration**

Create `server/alembic/versions/m1n2u3a4l5r6_add_ancient_roster_manual_fields.py`:

```python
"""add_ancient_roster_manual_fields

Revision ID: m1n2u3a4l5r6
Revises: h1d3n4t5c6l7
Create Date: 2026-07-01

Manual roster entries (leader/editor adds a participant missing from both
the tournament OCR scan and the Chests name base): source distinguishes
'ocr' from 'manual' rows, manual_expires_at is the Trade-Routes-anchored
expiry (NULL for 'ocr' rows), rank is a display-only field for manual
entries (never used by the quota formulas).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'm1n2u3a4l5r6'
down_revision: Union[str, None] = 'h1d3n4t5c6l7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'ancient_roster',
        sa.Column('source', sa.String(8), nullable=False, server_default=sa.text("'ocr'")),
    )
    op.add_column(
        'ancient_roster',
        sa.Column('manual_expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'ancient_roster',
        sa.Column('rank', sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ancient_roster', 'rank')
    op.drop_column('ancient_roster', 'manual_expires_at')
    op.drop_column('ancient_roster', 'source')
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 6: Commit**

```bash
git add server/models.py server/alembic/versions/m1n2u3a4l5r6_add_ancient_roster_manual_fields.py server/tests/test_ancients_dashboard.py
git commit -m "feat(ancients): add source/manual_expires_at/rank columns to AncientRoster"
```

---

## Task 2: `next_trade_routes_end()` helper in `roy.py`

**Files:**
- Modify: `server/roy.py`
- Test: `server/tests/test_roy.py`

**Interfaces:**
- Produces: `next_trade_routes_end() -> datetime` (timezone-aware, UTC) — the
  timestamp of the nearest upcoming completion of the "Trade Routes" event,
  computed from `is_trade_routes_active()`'s existing constants. Task 4
  (manual-add endpoint) imports and calls this.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_roy.py`:

```python
from roy import next_trade_routes_end, _EVENT_ANCHOR_TS, _EVENT_CYCLE_H, _EVENT_DURATION_H


def test_next_trade_routes_end_during_active_window(monkeypatch):
    """If we're inside the 24h active window, the nearest end is the end of
    THIS window (anchor + duration)."""
    import roy
    mid_active = datetime.fromtimestamp(_EVENT_ANCHOR_TS, tz=timezone.utc) + timedelta(hours=5)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return mid_active

    monkeypatch.setattr(roy, "datetime", FixedDatetime)
    expected = datetime.fromtimestamp(_EVENT_ANCHOR_TS, tz=timezone.utc) + timedelta(hours=_EVENT_DURATION_H)
    assert next_trade_routes_end() == expected


def test_next_trade_routes_end_during_pause_window(monkeypatch):
    """If we're inside the pause (event not active), the nearest end is the
    end of the NEXT cycle's active window."""
    import roy
    mid_pause = datetime.fromtimestamp(_EVENT_ANCHOR_TS, tz=timezone.utc) + timedelta(hours=_EVENT_DURATION_H + 10)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return mid_pause

    monkeypatch.setattr(roy, "datetime", FixedDatetime)
    expected = (datetime.fromtimestamp(_EVENT_ANCHOR_TS, tz=timezone.utc)
                + timedelta(hours=_EVENT_CYCLE_H + _EVENT_DURATION_H))
    assert next_trade_routes_end() == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_roy.py -k next_trade_routes_end -q`
Expected: FAIL — `ImportError: cannot import name 'next_trade_routes_end' from 'roy'`

- [ ] **Step 3: Implement the helper**

In `server/roy.py`, right after `is_trade_routes_active()` (after its closing
`return offset < duration_sec` line), add:

```python
def next_trade_routes_end() -> datetime:
    """
    Возвращает timestamp ближайшего завершения ивента «Торговые Пути» —
    либо конец текущего активного окна (если ивент сейчас идёт), либо конец
    следующего окна (если сейчас пауза). Детерминированная формула по тем же
    константам, без нового состояния.
    """
    cycle_sec    = _EVENT_CYCLE_H    * 3600
    duration_sec = _EVENT_DURATION_H * 3600
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    offset = (now_ts - _EVENT_ANCHOR_TS) % cycle_sec
    window_start_ts = now_ts - offset
    if offset < duration_sec:
        end_ts = window_start_ts + duration_sec
    else:
        end_ts = window_start_ts + cycle_sec + duration_sec
    return datetime.fromtimestamp(end_ts, tz=timezone.utc)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_roy.py -k next_trade_routes_end -q`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add server/roy.py server/tests/test_roy.py
git commit -m "feat(roy): add next_trade_routes_end() — deterministic expiry anchor for manual Ancient entries"
```

---

## Task 3: Quota calculation resolves confirmed name mappings

**Files:**
- Modify: `server/ancients_dashboard.py` (`calculate`, currently ~line 344-350)
- Test: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `AncientNameMapping` (already imported in `ancients_dashboard.py`).

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_calculate_strategy_b_uses_confirmed_mapped_name(db_session):
    """A confirmed AncientNameMapping's canonical name appears in the quota
    result table instead of the raw OCR player_name."""
    user, token = await _create_user_with_token(db_session, "mappedcalc1@test.com")
    collector = await _create_collector(db_session, user.id, slug="mapped-calc-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Ivan0v_raw",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="Ivan0v_raw",
                                      canonical_name="Иванов", confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/mapped-calc-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["result"]["players"]]
    assert names == ["Иванов"]


@pytest.mark.asyncio
async def test_calculate_strategy_b_uses_raw_name_when_unmapped(db_session):
    """No confirmed mapping -> raw player_name is used unchanged (no regression)."""
    user, token = await _create_user_with_token(db_session, "unmappedcalc1@test.com")
    collector = await _create_collector(db_session, user.id, slug="unmapped-calc-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Ivan0v_raw",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/unmapped-calc-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["result"]["players"]]
    assert names == ["Ivan0v_raw"]
```

- [ ] **Step 2: Run tests to verify the first fails**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py::test_calculate_strategy_b_uses_confirmed_mapped_name -q`
Expected: FAIL — `assert ['Ivan0v_raw'] == ['Иванов']`

- [ ] **Step 3: Implement the fix**

In `server/ancients_dashboard.py`, inside `calculate`, the `else` branch
(Strategy B) currently reads:

```python
        roster = (await db.execute(
            select(AncientRoster).where(AncientRoster.collector_id == collector.id)
        )).scalars().all()
        players = [(r.player_name, r.troop_level) for r in roster]
```

Change to:

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "feat(ancients): quota table shows confirmed player name, not raw OCR text"
```

---

## Task 4: Manual roster-entry endpoint

**Files:**
- Modify: `server/ancients_dashboard.py` (new route)
- Test: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `next_trade_routes_end()` (Task 2), `PlayerAlias`,
  `_get_own_or_editor_collector` (already defined in this file).
- Produces: `POST /{slug}/roster/manual` — later consumed by the frontend
  (Task 7) via a new `api.js` helper `dashboardAncientsAddManual`.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py` (add
`from difflib import get_close_matches` is not needed here — that's used
inside the endpoint, not the test):

```python
@pytest.mark.asyncio
async def test_add_manual_roster_entry_creates_row(db_session):
    user, token = await _create_user_with_token(db_session, "manual1@test.com")
    collector = await _create_collector(db_session, user.id, slug="manual-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-1/roster/manual",
            json={"player_name": "НовыйИгрок", "troop_level": "G7 S7 M8", "rank": "Ветеран"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == "НовыйИгрок",
        )
    )).scalar_one()
    assert row.source == "manual"
    assert row.rank == "Ветеран"
    assert row.troop_level == "G7 S7 M8"
    assert row.place is None
    assert row.points is None
    assert row.manual_expires_at is not None


@pytest.mark.asyncio
async def test_add_manual_roster_entry_rejects_exact_duplicate(db_session):
    user, token = await _create_user_with_token(db_session, "manual2@test.com")
    collector = await _create_collector(db_session, user.id, slug="manual-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Существующий",
                                 place=1, points=10))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-2/roster/manual",
            json={"player_name": "Существующий", "troop_level": None, "rank": None},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_manual_roster_entry_warns_on_similar_name(db_session):
    user, token = await _create_user_with_token(db_session, "manual3@test.com")
    collector = await _create_collector(db_session, user.id, slug="manual-3")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="raw1",
                               canonical_name="Иванов"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-3/roster/manual",
            json={"player_name": "Иваанов", "troop_level": None, "rank": None},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"]["similar_name"] == "Иванов"

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_add_manual_roster_entry_editor_can_add(db_session):
    """Editors (not just the owner) can add manual entries, matching the
    troop-level/name-mappings permission model."""
    from datetime import timedelta
    from models import AncientEditor
    owner, _ = await _create_user_with_token(db_session, "manualowner@test.com")
    editor, editor_token = await _create_user_with_token(db_session, "manualeditor@test.com")
    collector = await _create_collector(db_session, owner.id, slug="manual-4")
    db_session.add(AncientEditor(collector_id=collector.id, user_id=editor.id,
                                 expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-4/roster/manual",
            json={"player_name": "ДобавленРедактором", "troop_level": None, "rank": None},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
    assert resp.status_code == 200
```

(`datetime`/`timezone` are already imported at the top of
`test_ancients_dashboard.py` from Task 3 of the earlier retention plan;
`AncientEditor` needs importing inside the test function as shown, matching
the existing style in this file for tests that need a model not imported at
module scope.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py -k manual_roster_entry -q`
Expected: FAIL — 404 (route doesn't exist yet) on all 4 tests

- [ ] **Step 3: Implement the endpoint**

In `server/ancients_dashboard.py`, add near the top (with the other
`from difflib import get_close_matches` — already imported at the top of this
file, confirm with `grep -n "from difflib" server/ancients_dashboard.py`).
Add this new payload class and route after the `calculate` endpoint (after
its closing `return {"total_quota_millions": total, "result": result}`):

```python
class ManualRosterPayload(BaseModel):
    player_name: str
    troop_level: Optional[str] = None
    rank: Optional[str] = None


@router.post("/{slug}/roster/manual")
async def add_manual_roster_entry(slug: str, payload: ManualRosterPayload,
                                  user: User = Depends(get_web_user),
                                  db: AsyncSession = Depends(get_db)):
    """Ручное добавление участника Древнего — для игроков, которых нет ни
    в турнирной таблице (OCR), ни в базе Сундуков. Сгорает на ближайшем
    завершении «Торговых Путей», если реальные данные так и не появятся."""
    collector, _ = await _get_own_or_editor_collector(db, slug, user)

    existing = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == payload.player_name,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Player already in roster")

    canonical_names = list((await db.execute(
        select(PlayerAlias.canonical_name).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all())
    matches = get_close_matches(payload.player_name, canonical_names, n=1, cutoff=0.75)
    if matches and matches[0] != payload.player_name:
        raise HTTPException(status_code=409, detail={
            "message": "Similar name already confirmed",
            "similar_name": matches[0],
        })

    db.add(AncientRoster(
        collector_id=collector.id, player_name=payload.player_name,
        place=None, points=None, troop_level=payload.troop_level,
        rank=payload.rank, source="manual",
        manual_expires_at=next_trade_routes_end(),
    ))
    await db.commit()
    return {"ok": True}
```

Add the import at the top of `server/ancients_dashboard.py`, next to the
existing `from ancient_quota import (...)` line:

```python
from roy import next_trade_routes_end
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "feat(ancients): manual roster-entry endpoint with fuzzy duplicate guard"
```

---

## Task 5: Tournament import protects and promotes manual rows

**Files:**
- Modify: `server/tournaments.py`
- Test: `server/tests/test_tournaments.py`

**Interfaces:**
- Consumes: `AncientRoster.source`/`manual_expires_at` (Task 1).

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_tournaments.py`:

```python
@pytest.mark.asyncio
async def test_reimport_does_not_delete_manual_entry(db_session):
    """A manual roster row (no OCR name maps to it this cycle) survives a
    full tournament re-import, unlike normal OCR rows for players who left."""
    user = await _create_user(db_session, "hwid9000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS9",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS9")
    )).scalar_one()
    db_session.add(AncientRoster(collector_id=collector.id, player_name="РучнойИгрок",
                                 place=None, points=None, source="manual",
                                 manual_expires_at=datetime.now(timezone.utc) + timedelta(days=3)))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Иванов", "place": 1, "points": 100}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов", "РучнойИгрок"}


@pytest.mark.asyncio
async def test_reimport_promotes_manual_entry_when_matched(db_session):
    """A manual entry whose name matches an incoming tournament row gets
    real place/points and its source flips to 'ocr' — no duplicate row, no
    more expiry."""
    user = await _create_user(db_session, "hwidA000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERSA",
        items=[{"name": "Петров", "place": 1, "points": 50}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERSA")
    )).scalar_one()
    db_session.add(AncientRoster(collector_id=collector.id, player_name="СталНоситьСундуки",
                                 place=None, points=None, source="manual",
                                 manual_expires_at=datetime.now(timezone.utc) + timedelta(days=3)))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[
                                {"name": "Петров", "place": 1, "points": 50},
                                {"name": "СталНоситьСундуки", "place": 5, "points": 20},
                            ])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 2
    promoted = next(r for r in rows if r.player_name == "СталНоситьСундуки")
    assert promoted.source == "ocr"
    assert promoted.manual_expires_at is None
    assert promoted.place == 5
    assert promoted.points == 20
```

(Add `from datetime import datetime, timedelta, timezone` and
`from models import AncientRoster` at the top of `test_tournaments.py` if not
already present — check first, `AncientRoster` is already imported per the
existing test file header.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_tournaments.py -k "manual_entry" -q`
Expected: FAIL — `test_reimport_does_not_delete_manual_entry` fails
(`{'Иванов'} != {'Иванов', 'РучнойИгрок'}`, the manual row got deleted);
`test_reimport_promotes_manual_entry_when_matched` fails (a duplicate row is
inserted instead of promoting the existing manual one, or the existing one's
`source` stays `'manual'`).

- [ ] **Step 3: Implement the fix**

In `server/tournaments.py`, inside `import_tournament`'s loop, currently:

```python
        existing = (await db.execute(
            select(AncientRoster).where(
                AncientRoster.collector_id == collector.id,
                AncientRoster.player_name == canonical_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.place = item.place
            existing.points = item.points
        else:
            db.add(AncientRoster(
                collector_id=collector.id, player_name=canonical_name,
                place=item.place, points=item.points, troop_level=None,
            ))
```

Change to:

```python
        existing = (await db.execute(
            select(AncientRoster).where(
                AncientRoster.collector_id == collector.id,
                AncientRoster.player_name == canonical_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.place = item.place
            existing.points = item.points
            existing.source = "ocr"
            existing.manual_expires_at = None
        else:
            db.add(AncientRoster(
                collector_id=collector.id, player_name=canonical_name,
                place=item.place, points=item.points, troop_level=None,
                source="ocr",
            ))
```

And the full-replace delete right after, currently:

```python
    await db.flush()
    await db.execute(
        delete(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name.not_in(incoming_names),
        )
    )
```

Change to:

```python
    await db.flush()
    await db.execute(
        delete(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name.not_in(incoming_names),
            AncientRoster.source == "ocr",
        )
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_tournaments.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add server/tournaments.py server/tests/test_tournaments.py
git commit -m "feat(ancients): tournament re-import spares manual rows and promotes matches"
```

---

## Task 6: Expiry cleanup for stale manual entries

**Files:**
- Modify: `server/ancient_retention.py`
- Test: `server/tests/test_ancient_retention.py`

**Interfaces:**
- Produces: `run_manual_entry_expiry_tick(db: AsyncSession) -> int` (returns
  count of deleted rows), called from the existing `_retention_loop` next to
  `run_ancient_retention_tick`.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancient_retention.py`:

```python
from ancient_retention import run_manual_entry_expiry_tick


@pytest.mark.asyncio
async def test_expiry_tick_deletes_expired_manual_entry(db_session):
    collector = await _make_collector(db_session, slug="expired-manual-1")
    db_session.add(AncientRoster(
        collector_id=collector.id, player_name="Просрочен",
        source="manual", manual_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    ))
    await db_session.commit()

    deleted = await run_manual_entry_expiry_tick(db_session)

    assert deleted == 1
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_expiry_tick_ignores_not_yet_expired_manual_entry(db_session):
    collector = await _make_collector(db_session, slug="fresh-manual-1")
    db_session.add(AncientRoster(
        collector_id=collector.id, player_name="Свежий",
        source="manual", manual_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    ))
    await db_session.commit()

    deleted = await run_manual_entry_expiry_tick(db_session)

    assert deleted == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_expiry_tick_ignores_ocr_rows_regardless_of_dates(db_session):
    """source='ocr' rows never have manual_expires_at set, and must never be
    touched by this tick even if some future bug set a past timestamp on one."""
    collector = await _make_collector(db_session, slug="ocr-with-past-date-1")
    db_session.add(AncientRoster(
        collector_id=collector.id, player_name="ОбычныйИгрок",
        source="ocr", manual_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    ))
    await db_session.commit()

    deleted = await run_manual_entry_expiry_tick(db_session)

    assert deleted == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancient_retention.py -k expiry_tick -q`
Expected: FAIL — `ImportError: cannot import name 'run_manual_entry_expiry_tick' from 'ancient_retention'`

- [ ] **Step 3: Implement the tick**

In `server/ancient_retention.py`, add this function after
`run_ancient_retention_tick` (before `ensure_background_tasks`):

```python
async def run_manual_entry_expiry_tick(db: AsyncSession) -> int:
    """Удаляет вручную добавленные строки ростера, чьё время жизни истекло
    (ближайшее завершение «Торговых Путей» на момент добавления прошло, а
    реальные данные так и не подтвердили игрока). Возвращает количество
    удалённых строк."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(AncientRoster).where(
            AncientRoster.source == "manual",
            AncientRoster.manual_expires_at.is_not(None),
            AncientRoster.manual_expires_at < now,
        )
    )
    await db.commit()
    return result.rowcount or 0
```

Then update `_retention_loop` (currently only calls
`run_ancient_retention_tick`):

```python
async def _retention_loop() -> None:
    while True:
        await asyncio.sleep(RETENTION_TICK_SEC)
        async with AsyncSessionLocal() as db:
            await run_ancient_retention_tick(db)
            await run_manual_entry_expiry_tick(db)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancient_retention.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add server/ancient_retention.py server/tests/test_ancient_retention.py
git commit -m "feat(ancients): daily tick removes expired manual roster entries"
```

---

## Task 7: Frontend — manual-add form

**Files:**
- Modify: `web/src/api.js`
- Modify: `web/src/pages/AncientsPage.jsx`
- Modify: `web/src/dashboard_content.js`
- Modify: `web/src/dashboard_content.en.js`

**Interfaces:**
- Consumes: `POST /{slug}/roster/manual` (Task 4).
- Produces: `api.dashboardAncientsAddManual(slug, payload)` — resolves to
  the response body on success; on failure rejects with an `Error` whose
  `.message` is human-readable and whose `.similarName` (if present) is the
  suggested canonical name from a 409 similar-name response.

- [ ] **Step 1: Add the API helper**

In `web/src/api.js`, add near the other `dashboardAncients*` helpers (after
`dashboardAncientsSetHidden`):

```js
  dashboardAncientsAddManual: async (slug, payload) => {
    const token = getToken()
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${BASE}/web/dashboard/ancients/${slug}/roster/manual`, {
      method: 'POST', headers, body: JSON.stringify(payload),
    })
    let data
    try { data = await res.json() } catch { data = {} }
    if (!res.ok) {
      const err = new Error(data.detail?.message || data.detail || 'Request failed')
      err.similarName = data.detail?.similar_name
      throw err
    }
    return data
  },
```

(`getToken` is already imported at the top of `api.js` via
`import { getToken, clearToken } from './auth.js'` — this helper deliberately
does its own `fetch` instead of using the shared `request()` function, so it
can surface the structured `similar_name` field from a 409 response, which
`request()`'s generic error handling discards.)

- [ ] **Step 2: Add i18n strings**

In `web/src/dashboard_content.js`, inside the `ancients: { ... }` object,
after `showBtn: 'Показать',`:

```js
    manualAddTitle: 'Добавить участника вручную',
    manualNamePlaceholder: 'Имя игрока',
    manualRankLabel: 'Звание',
    manualAddButton: 'Добавить',
    manualSimilarNameWarning: name => `Похоже на «${name}» — использовать это имя?`,
    manualUseSuggested: 'Да, это он',
    manualAddAnyway: 'Нет, добавить как есть',
    manualDuplicateError: 'Такой игрок уже в ростере',
```

In `web/src/dashboard_content.en.js`, inside the `ancients: { ... }` object,
after `showBtn: 'Show',`:

```js
    manualAddTitle: 'Add participant manually',
    manualNamePlaceholder: 'Player name',
    manualRankLabel: 'Rank',
    manualAddButton: 'Add',
    manualSimilarNameWarning: name => `Looks like "${name}" — use this name?`,
    manualUseSuggested: 'Yes, that\'s them',
    manualAddAnyway: 'No, add as-is',
    manualDuplicateError: 'This player is already in the roster',
```

- [ ] **Step 3: Add the form to `AncientsPage.jsx`**

Add a `RANKS` constant near the top of the file, next to `TIERS`:

```js
const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
```

Add state, next to `troopEdits`:

```js
  const [manualForm, setManualForm] = useState({})
  const [manualSimilar, setManualSimilar] = useState({})
```

Add a handler function, next to `handleTroopFieldChange`:

```js
  async function handleAddManual(slug, useNameOverride) {
    const form = manualForm[slug] || {}
    const name = useNameOverride || form.name
    if (!name) return
    try {
      await api.dashboardAncientsAddManual(slug, {
        player_name: name, troop_level: form.troop_level || null, rank: form.rank || null,
      })
      setManualForm(prev => ({ ...prev, [slug]: {} }))
      setManualSimilar(prev => ({ ...prev, [slug]: null }))
      refresh()
    } catch (e) {
      if (e.similarName) {
        setManualSimilar(prev => ({ ...prev, [slug]: e.similarName }))
      } else {
        alert(e.message || cx.manualDuplicateError)
      }
    }
  }
```

Add the form JSX right after the roster table's closing `)}` (the
`sortedRoster.length === 0 ? ... : (<table>...</table>)}` block) and before
the `<button ... Сохранить маппинги` block, inside the roster `<div
className="card">`:

```jsx
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--outline)' }}>
                <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.manualAddTitle}</div>
                {manualSimilar[c.slug] && (
                  <div style={{ marginBottom: 8, fontSize: 13, color: '#f9a825' }}>
                    {cx.manualSimilarNameWarning(manualSimilar[c.slug])}
                    <button className="btn-secondary" style={{ fontSize: 12, marginLeft: 8, padding: '2px 8px' }}
                      onClick={() => handleAddManual(c.slug, manualSimilar[c.slug])}>
                      {cx.manualUseSuggested}
                    </button>
                    <button className="btn-secondary" style={{ fontSize: 12, marginLeft: 4, padding: '2px 8px' }}
                      onClick={() => setManualSimilar(prev => ({ ...prev, [c.slug]: null }))}>
                      {cx.manualAddAnyway}
                    </button>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <input
                    className="input-dark"
                    placeholder={cx.manualNamePlaceholder}
                    value={(manualForm[c.slug] || {}).name || ''}
                    onChange={e => setManualForm(prev => ({ ...prev, [c.slug]: { ...(prev[c.slug] || {}), name: e.target.value } }))}
                    style={{ minWidth: 140 }}
                  />
                  <select className="input-dark"
                    value={(manualForm[c.slug] || {}).rank || ''}
                    onChange={e => setManualForm(prev => ({ ...prev, [c.slug]: { ...(prev[c.slug] || {}), rank: e.target.value } }))}>
                    {RANKS.map(r => <option key={r} value={r}>{r || cx.manualRankLabel}</option>)}
                  </select>
                  <select className="input-dark" style={{ width: 44 }}
                    value={(manualForm[c.slug] || {}).g || ''}
                    onChange={e => setManualForm(prev => {
                      const f = { ...(prev[c.slug] || {}), g: e.target.value }
                      return { ...prev, [c.slug]: { ...f, troop_level: (f.g && f.s && f.m) ? `G${f.g} S${f.s} M${f.m}` : undefined } }
                    })}>
                    <option value="">G</option>
                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <select className="input-dark" style={{ width: 44 }}
                    value={(manualForm[c.slug] || {}).s || ''}
                    onChange={e => setManualForm(prev => {
                      const f = { ...(prev[c.slug] || {}), s: e.target.value }
                      return { ...prev, [c.slug]: { ...f, troop_level: (f.g && f.s && f.m) ? `G${f.g} S${f.s} M${f.m}` : undefined } }
                    })}>
                    <option value="">S</option>
                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <select className="input-dark" style={{ width: 44 }}
                    value={(manualForm[c.slug] || {}).m || ''}
                    onChange={e => setManualForm(prev => {
                      const f = { ...(prev[c.slug] || {}), m: e.target.value }
                      return { ...prev, [c.slug]: { ...f, troop_level: (f.g && f.s && f.m) ? `G${f.g} S${f.s} M${f.m}` : undefined } }
                    })}>
                    <option value="">M</option>
                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <button className="btn-primary" onClick={() => handleAddManual(c.slug)}>
                    {cx.manualAddButton}
                  </button>
                </div>
              </div>
```

- [ ] **Step 4: Build to verify no syntax errors**

Run: `cd web && npx vite build --mode production`
Expected: build succeeds (exit 0), no esbuild/JSX errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/api.js web/src/pages/AncientsPage.jsx web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "feat(ancients): manual participant form (name + rank + troop composition)"
```

---

## Task 8: Full local test suite + deploy (gated on owner approval)

**Files:** none (verification + deployment only)

- [ ] **Step 1: Run the full server test suite**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/ -q`
Expected: PASS count increases by the number of new tests added in Tasks
1-6 above the prior baseline (218 passed before this plan); the same ~33
pre-existing unrelated failures remain, no new failures.

- [ ] **Step 2: Do NOT deploy automatically**

Per this project's CLAUDE.md deploy protocol, do not run
`alembic upgrade head` on the GCP database, `git push`, or
`systemctl restart totalhunter`/trigger the Vercel hook until the owner
explicitly asks for it in this session. When they do:

```bash
git push origin main
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
# GCP:
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main"
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter/server && sudo -u ievgeniy2011 env DATABASE_URL='postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter' /opt/totalhunter/venv/bin/alembic upgrade head"
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="sudo systemctl restart totalhunter"
# then poll the Vercel deployment for READY and attach the total-hunter.com alias, as done earlier this session.
```

No commit for this task — verification + deployment checklist only.

---

## Self-Review Notes

- **Spec coverage:** Part 1 (quota table name resolution) — Task 3. Part 2
  (data model + manual-add endpoint) — Tasks 1, 4. Part 3 (tournament import
  interaction) — Task 5. Part 4 (expiry tick) — Task 6. Part 5 (frontend) —
  Task 7.
- **Type consistency:** `next_trade_routes_end() -> datetime` defined in Task
  2, imported and called identically in Task 4. `AncientRoster.source`/
  `manual_expires_at`/`rank` defined in Task 1, read/written identically in
  Tasks 3-6. `run_manual_entry_expiry_tick(db) -> int` defined and wired in
  Task 6 only (no other task references it). `api.dashboardAncientsAddManual`
  defined in Task 7, matching the endpoint from Task 4.
- **No placeholders:** every step has literal file paths, complete code, and
  exact pytest/build commands with expected outcomes.
