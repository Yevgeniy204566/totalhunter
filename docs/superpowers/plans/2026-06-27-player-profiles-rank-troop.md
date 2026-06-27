# Player Profiles (Звание + Состав войск) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-player Звание and Состав войск fields to the chest system — stored in a new `player_profiles` table, editable in the leader dashboard and by players on the public clan page, auto-populated in the Ancient calculator.

**Architecture:** New `player_profiles` table (collector_id + canonical_name unique key). Backend exposes two endpoints: authenticated dashboard batch-save and anonymous public per-row upsert. Summary API enriches each player object with rank/troop_level. Ancient roster falls back to `player_profiles.troop_level` when `AncientRoster.troop_level` is NULL. Frontend adds two select columns to the Players tab and a toggle edit mode on the public page.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy async · Alembic · SQLite (tests) · PostgreSQL (prod) · React 18 · httpx/pytest-asyncio

## Global Constraints

- All test commands run from `C:\BattleBot\server\` directory
- Tests use in-memory SQLite via conftest.py `setup_test_db` fixture — no PostgreSQL needed locally
- Alembic migrations run only on GCP — `Base.metadata.create_all` covers tests automatically
- `TROOP_STEPS` list stays in `server/ancient_quota.py` as the single source of truth; frontend hardcodes the same 13 values (no extra API call)
- Ranks: `["Глава", "Старший", "Офицер", "Ветеран", "Рядовой"]` — hardcoded both backend and frontend
- No auth on the public upsert endpoint — data is non-critical, leader can override from dashboard
- `pivot_summary()` signature is NOT changed — profile enrichment happens after the call in each route handler

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `server/alembic/versions/p1r2o3f4i5l6_add_player_profiles.py` | Create | Alembic migration for `player_profiles` table |
| `server/models.py` | Modify | Add `PlayerProfile` ORM model |
| `server/chest_dashboard.py` | Modify | `_player_alias_rows()` enrichment + new dashboard POST endpoint |
| `server/chests.py` | Modify | Public upsert endpoint + summary enrichment |
| `server/ancients_dashboard.py` | Modify | `_roster_rows()` LEFT JOIN with `player_profiles` |
| `server/tests/test_chest_dashboard.py` | Modify | Tests for dashboard endpoint and enriched GET |
| `server/tests/test_chests.py` | Modify | Tests for public upsert + summary enrichment |
| `server/tests/test_ancients_dashboard.py` | Modify | Tests for troop_level fallback |
| `web/src/api.js` | Modify | Add `dashboardChestsPlayerProfiles` + `postPublicPlayerProfile` |
| `web/src/pages/ChestsPage.jsx` | Modify | Звание/Состав selects in Players tab, combined save |
| `web/src/pages/ChestSummaryPage.jsx` | Modify | Edit mode toggle button, pass editMode to table |
| `web/src/components/ChestSummaryTable.jsx` | Modify | Edit mode: 2 new columns + per-row 💾 save |

---

### Task 1: DB Migration + `PlayerProfile` model

**Files:**
- Create: `server/alembic/versions/p1r2o3f4i5l6_add_player_profiles.py`
- Modify: `server/models.py`

**Interfaces:**
- Produces: `PlayerProfile` class importable from `models`, with `.collector_id`, `.canonical_name`, `.rank`, `.troop_level`, `.updated_at`

- [ ] **Step 1: Add `PlayerProfile` to `models.py`**

Open `server/models.py`. After the `PlayerAlias` class (around line 463), add:

```python
class PlayerProfile(Base):
    """Звание и состав войск игрока — один профиль на (collector, canonical_name).
    Источников два: лидер правит в кабинете, игрок — на публичной странице.
    Лидерский dashboard-сейв авторитетен (delete+insert весь список),
    публичный upsert — select+update/insert одной строки."""
    __tablename__ = "player_profiles"
    __table_args__ = (
        UniqueConstraint("collector_id", "canonical_name", name="uq_player_profile"),
    )

    id             = Column(Integer, primary_key=True)
    collector_id   = Column(Integer, ForeignKey("chest_collectors.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    canonical_name = Column(String(100), nullable=False)
    rank           = Column(String(20), nullable=True)
    troop_level    = Column(String(20), nullable=True)
    updated_at     = Column(TIMESTAMP(timezone=True), nullable=False,
                            server_default=func.now())
```

- [ ] **Step 2: Create the Alembic migration file**

Create `server/alembic/versions/p1r2o3f4i5l6_add_player_profiles.py` with this exact content:

```python
"""add player_profiles table for per-player rank and troop composition

Revision ID: p1r2o3f4i5l6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa

revision      = 'p1r2o3f4i5l6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'player_profiles',
        sa.Column('id',             sa.Integer(),               primary_key=True),
        sa.Column('collector_id',   sa.Integer(),               nullable=False),
        sa.Column('canonical_name', sa.String(100),             nullable=False),
        sa.Column('rank',           sa.String(20),              nullable=True),
        sa.Column('troop_level',    sa.String(20),              nullable=True),
        sa.Column('updated_at',     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(
            ['collector_id'], ['chest_collectors.id'],
            name=op.f('fk_player_profiles_collector_id_chest_collectors'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_player_profiles')),
        sa.UniqueConstraint('collector_id', 'canonical_name', name='uq_player_profile'),
    )
    op.create_index(op.f('ix_player_profiles_collector_id'), 'player_profiles', ['collector_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_player_profiles_collector_id'), table_name='player_profiles')
    op.drop_table('player_profiles')
```

- [ ] **Step 3: Verify model is picked up by test infra**

Run:
```powershell
cd C:\BattleBot\server
python -c "from models import PlayerProfile; print('OK', PlayerProfile.__tablename__)"
```
Expected output: `OK player_profiles`

- [ ] **Step 4: Commit**

```powershell
git add server/models.py server/alembic/versions/p1r2o3f4i5l6_add_player_profiles.py
git commit -m "feat: add player_profiles table (rank + troop_level per collector/player)"
```

---

### Task 2: Backend — Dashboard endpoint + enriched GET

**Files:**
- Modify: `server/chest_dashboard.py`
- Modify: `server/tests/test_chest_dashboard.py`

**Interfaces:**
- Consumes: `PlayerProfile` from `models`
- Produces:
  - `GET /web/dashboard/chests` → each `player_alias_rows` entry now includes `"rank": str|null, "troop_level": str|null`
  - `POST /web/dashboard/chests/player-profiles` → payload `{collector_slug, rows: [{canonical_name, rank, troop_level}]}` → `{"ok": true}`

- [ ] **Step 1: Write failing tests**

Append to `server/tests/test_chest_dashboard.py`:

```python
from models import PlayerProfile  # add to existing imports at top of file


@pytest.mark.asyncio
async def test_post_player_profiles_saves_rank_and_troop(db_session):
    user, token = await _create_user_with_token(db_session, email="pp1@test.com")
    collector = await _create_collector(db_session, user.id, slug="pp-slug-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-profiles",
            json={"collector_slug": "pp-slug-1", "rows": [
                {"canonical_name": "Alice", "rank": "Офицер", "troop_level": "G8 S8 M8"},
                {"canonical_name": "Bob",   "rank": "Рядовой", "troop_level": None},
            ]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    from sqlalchemy import select
    profiles = (await db_session.execute(
        select(PlayerProfile).where(PlayerProfile.collector_id == collector.id)
    )).scalars().all()
    by_name = {p.canonical_name: p for p in profiles}
    assert by_name["Alice"].rank == "Офицер"
    assert by_name["Alice"].troop_level == "G8 S8 M8"
    assert by_name["Bob"].rank == "Рядовой"
    assert by_name["Bob"].troop_level is None


@pytest.mark.asyncio
async def test_post_player_profiles_forbidden_for_other_collector(db_session):
    user, token = await _create_user_with_token(db_session, email="pp2@test.com")
    other_user, _ = await _create_user_with_token(db_session, email="pp3@test.com")
    await _create_collector(db_session, other_user.id, slug="other-slug-pp")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-profiles",
            json={"collector_slug": "other-slug-pp", "rows": []},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_chests_player_alias_rows_include_profile_fields(db_session):
    user, token = await _create_user_with_token(db_session, email="pp4@test.com")
    collector = await _create_collector(db_session, user.id, slug="pp-slug-4")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="alice_ocr",
                               canonical_name="Alice"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Alice",
                                 rank="Глава", troop_level="G9 S9 M9"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    player_rows = resp.json()["collectors"][0]["player_alias_rows"]
    alice = next(r for r in player_rows if r["raw_name"] == "alice_ocr")
    assert alice["rank"] == "Глава"
    assert alice["troop_level"] == "G9 S9 M9"
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd C:\BattleBot\server
python -m pytest tests/test_chest_dashboard.py::test_post_player_profiles_saves_rank_and_troop tests/test_chest_dashboard.py::test_get_chests_player_alias_rows_include_profile_fields -v
```
Expected: FAILED (ImportError or 404/422)

- [ ] **Step 3: Implement — modify `chest_dashboard.py`**

**3a.** Add `PlayerProfile` to the import block at line ~29:

```python
from models import (
    Chest, ChestCatalogReference, ChestCollector, ChestConfiguration, ChestLocalization,
    ChestSeasonHistory, ChestTypeAlias, ChestTypeCatalog, PlayerAlias, PlayerProfile, User,
)
```

Also add `delete` to the sqlalchemy imports if not already there (it is).

**3b.** Replace `_player_alias_rows()` function (lines ~180–198) with this enriched version:

```python
async def _player_alias_rows(db: AsyncSession, collector: ChestCollector,
                             global_alias_map: dict | None = None) -> list:
    aliases = (await db.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()

    profiles = (await db.execute(
        select(PlayerProfile).where(PlayerProfile.collector_id == collector.id)
    )).scalars().all()
    profile_map = {p.canonical_name: p for p in profiles}

    rows = []
    for a in aliases:
        profile = profile_map.get(a.canonical_name)
        rows.append({
            "raw_name": a.raw_name,
            "canonical_name": a.canonical_name,
            "rank": profile.rank if profile else None,
            "troop_level": profile.troop_level if profile else None,
        })

    mapped_raw_names = {a.raw_name for a in aliases}
    unmapped = (await db.execute(
        select(Chest.sender_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_name in unmapped:
        if raw_name in mapped_raw_names:
            continue
        canonical = (global_alias_map or {}).get(raw_name)
        rows.append({
            "raw_name": raw_name,
            "canonical_name": canonical,
            "rank": None,
            "troop_level": None,
        })

    return rows
```

**3c.** After the `post_player_aliases` endpoint (after line ~329), add new models + endpoint:

```python
class PlayerProfileRowIn(BaseModel):
    canonical_name: str
    rank: Optional[str] = None
    troop_level: Optional[str] = None


class PlayerProfilesPayload(BaseModel):
    collector_slug: str
    rows: List[PlayerProfileRowIn] = []


@router.post("/player-profiles")
async def post_player_profiles(payload: PlayerProfilesPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)

    await db.execute(delete(PlayerProfile).where(PlayerProfile.collector_id == collector.id))

    for row in payload.rows:
        canonical = (row.canonical_name or "").strip()
        if not canonical:
            continue
        db.add(PlayerProfile(
            collector_id=collector.id,
            canonical_name=canonical,
            rank=row.rank or None,
            troop_level=row.troop_level or None,
        ))

    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
cd C:\BattleBot\server
python -m pytest tests/test_chest_dashboard.py::test_post_player_profiles_saves_rank_and_troop tests/test_chest_dashboard.py::test_post_player_profiles_forbidden_for_other_collector tests/test_chest_dashboard.py::test_get_chests_player_alias_rows_include_profile_fields -v
```
Expected: 3 PASSED

- [ ] **Step 5: Run full dashboard test suite to verify no regressions**

```powershell
python -m pytest tests/test_chest_dashboard.py -v
```
Expected: all PASSED

- [ ] **Step 6: Commit**

```powershell
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat: dashboard player-profiles endpoint + rank/troop enrichment in GET"
```

---

### Task 3: Backend — Public upsert + summary enrichment

**Files:**
- Modify: `server/chests.py`
- Modify: `server/tests/test_chests.py`

**Interfaces:**
- Consumes: `PlayerProfile` from `models`
- Produces:
  - `POST /api/v1/chests/public/player-profile` → no auth, payload `{collector_slug, canonical_name, rank, troop_level}` → `{"ok": true}`
  - `GET /api/v1/chests/summary/{slug}` → each player object now includes `"rank": str|null, "troop_level": str|null`
  - `GET /api/v1/chests/by/{kingdom}/{slug}` → same enrichment

- [ ] **Step 1: Write failing tests**

Append to `server/tests/test_chests.py`:

```python
from models import PlayerProfile  # add to existing imports at top of file

@pytest.mark.asyncio
async def test_public_upsert_player_profile_creates(db_session):
    from models import User, ChestCollector
    user = User(hwid="a" * 16, ref_code="z" * 6, email="pub1@test.com")
    db_session.add(user)
    await db_session.flush()
    collector = ChestCollector(kingdom="K1", clan="Clan1", user_id=user.id, slug="pub-slug-1")
    db_session.add(collector)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/public/player-profile", json={
            "collector_slug": "pub-slug-1",
            "canonical_name": "Alice",
            "rank": "Ветеран",
            "troop_level": "G7 S7 M7",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    from sqlalchemy import select
    profile = (await db_session.execute(
        select(PlayerProfile).where(
            PlayerProfile.collector_id == collector.id,
            PlayerProfile.canonical_name == "Alice",
        )
    )).scalar_one()
    assert profile.rank == "Ветеран"
    assert profile.troop_level == "G7 S7 M7"


@pytest.mark.asyncio
async def test_public_upsert_player_profile_updates(db_session):
    from models import User, ChestCollector
    user = User(hwid="b" * 16, ref_code="y" * 6, email="pub2@test.com")
    db_session.add(user)
    await db_session.flush()
    collector = ChestCollector(kingdom="K1", clan="Clan2", user_id=user.id, slug="pub-slug-2")
    db_session.add(collector)
    await db_session.flush()
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Bob",
                                 rank="Рядовой", troop_level="G5 S5 M5"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/public/player-profile", json={
            "collector_slug": "pub-slug-2",
            "canonical_name": "Bob",
            "rank": "Офицер",
            "troop_level": "G8 S8 M8",
        })
    assert resp.status_code == 200

    from sqlalchemy import select
    await db_session.expire_all()
    profile = (await db_session.execute(
        select(PlayerProfile).where(
            PlayerProfile.collector_id == collector.id,
            PlayerProfile.canonical_name == "Bob",
        )
    )).scalar_one()
    assert profile.rank == "Офицер"
    assert profile.troop_level == "G8 S8 M8"


@pytest.mark.asyncio
async def test_summary_includes_rank_and_troop_level(db_session):
    from datetime import datetime
    from models import User, ChestCollector, Chest, ChestConfiguration, PlayerProfile
    user = User(hwid="c" * 16, ref_code="x" * 6, email="sum1@test.com")
    db_session.add(user)
    await db_session.flush()
    collector = ChestCollector(kingdom="K1", clan="SumClan", user_id=user.id, slug="sum-slug-1")
    db_session.add(collector)
    await db_session.flush()
    db_session.add(Chest(
        collector_id=collector.id, sender_raw="Alice", sender_canonical="Alice",
        chest_type_raw="Epic Crypt 25", chest_type_canonical="Epic Crypt 25",
        collected_at=datetime.fromisoformat("2026-06-27T10:00:00"),
    ))
    db_session.add(ChestConfiguration(
        collector_id=collector.id, catalog_id="Epic Crypt 25",
        points=45, is_in_pattern=True, counts_toward_quota=True,
    ))
    db_session.add(PlayerProfile(
        collector_id=collector.id, canonical_name="Alice",
        rank="Старший", troop_level="G8 S8 M9",
    ))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/chests/summary/sum-slug-1")
    assert resp.status_code == 200
    players = resp.json()["players"]
    assert len(players) == 1
    assert players[0]["name"] == "Alice"
    assert players[0]["rank"] == "Старший"
    assert players[0]["troop_level"] == "G8 S8 M9"
```

- [ ] **Step 2: Run to verify failures**

```powershell
cd C:\BattleBot\server
python -m pytest tests/test_chests.py::test_public_upsert_player_profile_creates tests/test_chests.py::test_summary_includes_rank_and_troop_level -v
```
Expected: FAILED (404 on unknown route, KeyError on missing rank field)

- [ ] **Step 3: Add `PlayerProfile` to imports in `chests.py`**

Modify the import at line ~27:

```python
from models import (
    Chest, ChestCollector, ChestTypeAlias, Hunt,
    PlayerAlias, PlayerProfile, Transaction, User,
)
```

Also add `select` to sqlalchemy imports if not already present (it is).

- [ ] **Step 4: Add public upsert endpoint to `chests.py`**

After the `_clan_to_slug` helper (around line 237), add:

```python
class PublicPlayerProfileIn(BaseModel):
    collector_slug: str
    canonical_name: str
    rank: Optional[str] = None
    troop_level: Optional[str] = None


@router.post("/public/player-profile")
async def public_upsert_player_profile(payload: PublicPlayerProfileIn,
                                       db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == payload.collector_slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    canonical = (payload.canonical_name or "").strip()
    if not canonical:
        raise HTTPException(status_code=400, detail="canonical_name required")

    existing = (await db.execute(
        select(PlayerProfile).where(
            PlayerProfile.collector_id == collector.id,
            PlayerProfile.canonical_name == canonical,
        )
    )).scalar_one_or_none()

    if existing:
        existing.rank = payload.rank or None
        existing.troop_level = payload.troop_level or None
    else:
        db.add(PlayerProfile(
            collector_id=collector.id,
            canonical_name=canonical,
            rank=payload.rank or None,
            troop_level=payload.troop_level or None,
        ))

    await db.commit()
    return {"ok": True}
```

Also add `Optional` to the `typing` import: `from typing import List, Optional`

- [ ] **Step 5: Add profile enrichment to `get_chest_summary()` and `get_chest_by_kingdom_slug()`**

In `get_chest_summary` (line ~221), after `result = pivot_summary(...)`:

```python
    result = pivot_summary(collector.kingdom, collector.clan, rows)

    # Enrich each player with rank + troop_level from player_profiles
    profiles = (await db.execute(
        select(PlayerProfile).where(PlayerProfile.collector_id == collector.id)
    )).scalars().all()
    profile_map = {p.canonical_name: p for p in profiles}
    for player in result["players"]:
        profile = profile_map.get(player["name"])
        player["rank"] = profile.rank if profile else None
        player["troop_level"] = profile.troop_level if profile else None
```

Apply the identical block in `get_chest_by_kingdom_slug()` after its `result = pivot_summary(...)` call.

- [ ] **Step 6: Run tests to verify they pass**

```powershell
cd C:\BattleBot\server
python -m pytest tests/test_chests.py::test_public_upsert_player_profile_creates tests/test_chests.py::test_public_upsert_player_profile_updates tests/test_chests.py::test_summary_includes_rank_and_troop_level -v
```
Expected: 3 PASSED

- [ ] **Step 7: Run full chests test suite**

```powershell
python -m pytest tests/test_chests.py -v
```
Expected: all PASSED

- [ ] **Step 8: Commit**

```powershell
git add server/chests.py server/tests/test_chests.py
git commit -m "feat: public player-profile upsert + rank/troop in summary response"
```

---

### Task 4: Backend — Ancient auto-populate from `player_profiles`

**Files:**
- Modify: `server/ancients_dashboard.py`
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `PlayerProfile` from `models`
- Produces: `_roster_rows()` → each row's `troop_level` is `AncientRoster.troop_level` if set, else `player_profiles.troop_level` if exists, else `None`

- [ ] **Step 1: Write failing tests**

Read the top of `server/tests/test_ancients_dashboard.py` to find existing helper functions, then append:

```python
from models import PlayerProfile  # add to existing imports at top of file


@pytest.mark.asyncio
async def test_roster_uses_profile_troop_level_as_fallback(db_session):
    user, token = await _make_user(db_session, "anc_prof1@test.com")
    collector = await _make_collector(db_session, user.id, slug="anc-pf-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Alice",
                                 place=1, points=1000, troop_level=None))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Alice",
                                 rank="Старший", troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    roster = resp.json()["collectors"][0]["roster"]
    alice = next(r for r in roster if r["player_name"] == "Alice")
    assert alice["troop_level"] == "G8 S8 M8"


@pytest.mark.asyncio
async def test_roster_manual_troop_level_wins_over_profile(db_session):
    user, token = await _make_user(db_session, "anc_prof2@test.com")
    collector = await _make_collector(db_session, user.id, slug="anc-pf-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Bob",
                                 place=1, points=2000, troop_level="G9 S9 M9"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Bob",
                                 rank="Глава", troop_level="G5 S5 M5"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    roster = resp.json()["collectors"][0]["roster"]
    bob = next(r for r in roster if r["player_name"] == "Bob")
    assert bob["troop_level"] == "G9 S9 M9"
```

Note: `_make_user` and `_make_collector` are the existing helpers in that test file — read the file first to get their exact names, adjust if needed.

- [ ] **Step 2: Run to verify failures**

```powershell
cd C:\BattleBot\server
python -m pytest tests/test_ancients_dashboard.py::test_roster_uses_profile_troop_level_as_fallback tests/test_ancients_dashboard.py::test_roster_manual_troop_level_wins_over_profile -v
```
Expected: FAILED (alice troop_level is None instead of "G8 S8 M8")

- [ ] **Step 3: Modify `_roster_rows()` in `ancients_dashboard.py`**

First add imports at top of file:

```python
from sqlalchemy import and_, delete, select  # add `and_` if not already there
from models import AncientCalculation, AncientRoster, ChestCollector, PlayerProfile, User
```

Then replace `_roster_rows()` (lines ~38–47):

```python
async def _roster_rows(db: AsyncSession, collector_id: int) -> list:
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
    return [
        {
            "player_name": r.AncientRoster.player_name,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
        }
        for r in rows
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
cd C:\BattleBot\server
python -m pytest tests/test_ancients_dashboard.py -v
```
Expected: all PASSED including new tests

- [ ] **Step 5: Commit**

```powershell
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "feat: ancient roster auto-populates troop_level from player_profiles"
```

---

### Task 5: Frontend — ChestsPage Players tab (Звание + Состав selects)

**Files:**
- Modify: `web/src/api.js`
- Modify: `web/src/pages/ChestsPage.jsx`

**Interfaces:**
- Consumes: enriched `player_alias_rows` from GET `/web/dashboard/chests` (now has `rank`, `troop_level` fields)
- Consumes: `POST /web/dashboard/chests/player-profiles`
- Produces: saved rank+troop_level on "Сохранить" click in Players tab

- [ ] **Step 1: Add API call to `api.js`**

In `web/src/api.js`, after `dashboardChestsPlayerAliases` (line ~45), add:

```js
  dashboardChestsPlayerProfiles: (slug, rows) =>
    request('POST', '/web/dashboard/chests/player-profiles', { collector_slug: slug, rows }),
```

Also at the bottom of the file, after `fetchChestByKingdomSlug`, add:

```js
export async function postPublicPlayerProfile(collector_slug, canonical_name, rank, troop_level) {
  const res = await fetch(`${BASE}/api/v1/chests/public/player-profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ collector_slug, canonical_name, rank, troop_level }),
  })
  if (!res.ok) throw new Error('Save failed')
  return res.json()
}
```

- [ ] **Step 2: Update `savePlayerAliases()` in `ChestsPage.jsx` to also save profiles**

Find `savePlayerAliases` (around line 143) and replace it:

```jsx
  async function savePlayerAliases(slug) {
    try {
      await api.dashboardChestsPlayerAliases(slug, playerRowsByCollector[slug])
      // Save rank + troop_level profiles in the same action
      const profileRows = (playerRowsByCollector[slug] || [])
        .filter(r => (r.canonical_name || '').trim())
        .map(r => ({
          canonical_name: r.canonical_name,
          rank: r.rank || null,
          troop_level: r.troop_level || null,
        }))
      await api.dashboardChestsPlayerProfiles(slug, profileRows)
      setMsg(cx.saved)
      await refresh()
    } catch (e) { setMsg(e.message) }
  }
```

- [ ] **Step 3: Add Звание and Состав columns to the Players table in `ChestsPage.jsx`**

The TROOP_STEPS and RANKS constants — add near the top of the file (after imports):

```jsx
const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TROOP_STEPS = [
  '', 'G5 S5 M5', 'G5 S5 M6', 'G5 S6 M6',
  'G6 S6 M6', 'G6 S6 M7', 'G6 S7 M7',
  'G7 S7 M7', 'G7 S7 M8', 'G7 S8 M8',
  'G8 S8 M8', 'G8 S8 M9', 'G8 S9 M9',
  'G9 S9 M9',
]
```

Find the Players tab table (around line 452). Add two `<th>` to the header after the existing ones:

Before (find this exact block):
```jsx
                  <tr>
                    <th>{cx.playerRawCol}</th>
                    <th>{cx.playerCanonicalCol}</th>
                  </tr>
```

After:
```jsx
                  <tr>
                    <th>{cx.playerRawCol}</th>
                    <th>{cx.playerCanonicalCol}</th>
                    <th>Звание</th>
                    <th>Состав</th>
                  </tr>
```

Find the table row rendering (around line 460). Before (find this exact block):
```jsx
                  {playerRowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td>{row.raw_name || '—'}</td>
                      <td>
                        <input
                          className="input-dark"
                          value={row.canonical_name || ''}
                          onChange={e => updatePlayerRow(collector.slug, i, 'canonical_name', e.target.value)}
                        />
                      </td>
                    </tr>
```

After:
```jsx
                  {playerRowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td>{row.raw_name || '—'}</td>
                      <td>
                        <input
                          className="input-dark"
                          value={row.canonical_name || ''}
                          onChange={e => updatePlayerRow(collector.slug, i, 'canonical_name', e.target.value)}
                        />
                      </td>
                      <td>
                        <select
                          className="input-dark"
                          value={row.rank || ''}
                          onChange={e => updatePlayerRow(collector.slug, i, 'rank', e.target.value)}
                        >
                          {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                        </select>
                      </td>
                      <td>
                        <select
                          className="input-dark"
                          value={row.troop_level || ''}
                          onChange={e => updatePlayerRow(collector.slug, i, 'troop_level', e.target.value)}
                        >
                          {TROOP_STEPS.map(s => <option key={s} value={s}>{s || '—'}</option>)}
                        </select>
                      </td>
                    </tr>
```

- [ ] **Step 4: Manually verify in browser**

Start dev server: `cd C:\BattleBot\web && npm run dev`
Navigate to `http://localhost:5173`, log in, go to Сундуки → Players tab.
Verify: two new columns appear, selects populate correctly, "Сохранить" saves without error.

- [ ] **Step 5: Commit**

```powershell
git add web/src/api.js web/src/pages/ChestsPage.jsx
git commit -m "feat: Звание and Состав selects in ChestsPage Players tab"
```

---

### Task 6: Frontend — Public page edit mode + deploy

**Files:**
- Modify: `web/src/pages/ChestSummaryPage.jsx`
- Modify: `web/src/components/ChestSummaryTable.jsx`

**Interfaces:**
- Consumes: `postPublicPlayerProfile` from `api.js`
- Consumes: `rank`, `troop_level` fields on each player object in summary response
- Produces: "✏️ Ввести состав" button → edit mode → per-row 💾 save → exit edit mode

- [ ] **Step 1: Add edit mode state + toggle to `ChestSummaryPage.jsx`**

Add import at top:
```jsx
import { postPublicPlayerProfile } from '../api.js'
```

Add state inside component (after existing state declarations):
```jsx
  const [editMode, setEditMode] = useState(false)
```

In the JSX, find the line with `<ChestSummaryTable` inside `{tab === 'current' && (...)}`  and replace the entire block:

```jsx
      {tab === 'current' && (
        <>
          <div style={{ marginBottom: 12 }}>
            <button
              className="btn-secondary"
              style={{ fontSize: 13, padding: '4px 12px' }}
              onClick={() => setEditMode(m => !m)}
            >
              {editMode ? '✕ Закрыть' : '✏️ Ввести состав'}
            </button>
          </div>
          <ChestSummaryTable
            chestTypes={data.chest_types}
            players={data.players}
            targets={targets}
            editMode={editMode}
            collectorSlug={internalSlug}
            onSaveDone={() => setEditMode(false)}
          />
        </>
      )}
```

- [ ] **Step 2: Add edit columns to `ChestSummaryTable.jsx`**

Add RANKS and TROOP_STEPS constants at top of file (same values as in ChestsPage):

```jsx
const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TROOP_STEPS = [
  '', 'G5 S5 M5', 'G5 S5 M6', 'G5 S6 M6',
  'G6 S6 M6', 'G6 S6 M7', 'G6 S7 M7',
  'G7 S7 M7', 'G7 S7 M8', 'G7 S8 M8',
  'G8 S8 M8', 'G8 S8 M9', 'G8 S9 M9',
  'G9 S9 M9',
]
```

Import `postPublicPlayerProfile` and `useState`:
```jsx
import { useEffect, useRef, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'
```

Update the function signature:
```jsx
export default function ChestSummaryTable({ chestTypes, players, targets, editMode = false, collectorSlug, onSaveDone }) {
```

Add per-row edit state inside the component (after the existing `useEffect`):
```jsx
  const [editRows, setEditRows] = useState({})
  const [saving, setSaving] = useState(null)

  useEffect(() => {
    if (!editMode) return
    const init = {}
    players.forEach(p => {
      init[p.name] = { rank: p.rank || '', troop_level: p.troop_level || '' }
    })
    setEditRows(init)
  }, [editMode, players])

  async function handleSave(playerName) {
    const row = editRows[playerName] || {}
    setSaving(playerName)
    try {
      await postPublicPlayerProfile(collectorSlug, playerName, row.rank || null, row.troop_level || null)
      if (onSaveDone) onSaveDone()
    } catch (e) {
      alert('Ошибка сохранения: ' + e.message)
    } finally {
      setSaving(null)
    }
  }
```

In the `<thead>` block, add two `<th>` columns when `editMode` is true. Find the header row and replace:

```jsx
            <tr>
              <th>#</th>
              <th>Player</th>
              {editMode && <th>Звание</th>}
              {editMode && <th>Состав</th>}
              {editMode && <th></th>}
              <th>Points</th>
              <th className="public-epic-cell">Epic Crypts</th>
              {chestTypes.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>{t}</th>
              ))}
            </tr>
```

In the `<tbody>` row rendering, add edit cells. Find the `<tr key={p.name} ...>` block and add after the player name `<td>`:

```jsx
                  {editMode && (
                    <td>
                      <select
                        value={editRows[p.name]?.rank || ''}
                        onChange={e => setEditRows(prev => ({
                          ...prev,
                          [p.name]: { ...prev[p.name], rank: e.target.value },
                        }))}
                        style={{ fontSize: 12, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                      >
                        {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                      </select>
                    </td>
                  )}
                  {editMode && (
                    <td>
                      <select
                        value={editRows[p.name]?.troop_level || ''}
                        onChange={e => setEditRows(prev => ({
                          ...prev,
                          [p.name]: { ...prev[p.name], troop_level: e.target.value },
                        }))}
                        style={{ fontSize: 12, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                      >
                        {TROOP_STEPS.map(s => <option key={s} value={s}>{s || '—'}</option>)}
                      </select>
                    </td>
                  )}
                  {editMode && (
                    <td>
                      <button
                        onClick={() => handleSave(p.name)}
                        disabled={saving === p.name}
                        style={{ fontSize: 12, padding: '2px 8px', cursor: 'pointer', background: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                      >
                        {saving === p.name ? '...' : '💾'}
                      </button>
                    </td>
                  )}
```

- [ ] **Step 3: Manually test in browser**

Start dev server: `cd C:\BattleBot\web && npm run dev`
Navigate to a public clan page (e.g. `http://localhost:5173/chests/<slug>`).
Verify:
1. "✏️ Ввести состав" button appears above table
2. Click → two columns + 💾 buttons appear
3. Select rank and troop_level in a row, click 💾
4. Columns disappear, edit mode exits
5. Click again → values persist (pre-filled from response)

- [ ] **Step 4: Deploy — push + Vercel hook + alias**

```powershell
git add web/src/pages/ChestSummaryPage.jsx web/src/components/ChestSummaryTable.jsx
git commit -m "feat: public page edit mode for player rank+troop composition"
git push origin main
```

Trigger Vercel build:
```powershell
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```

Wait for READY and attach alias:
```powershell
$TOKEN = (Get-Content "C:\BattleBot\settings.local.json" | ConvertFrom-Json).vercel_token
$TEAM = "team_CkkRPXdwtRtsL9YCk8n4Fzla"
$PROJECT = "prj_mWtcb6hJCkl40YLWheeIlxD5NmXj"
$state = ""
while ($state -ne "READY") {
    Start-Sleep 10
    $resp = Invoke-RestMethod "https://api.vercel.com/v6/deployments?projectId=$PROJECT&teamId=$TEAM&limit=1" -Headers @{Authorization="Bearer $TOKEN"}
    $state = $resp.deployments[0].state
    Write-Host "State: $state"
}
$uid = $resp.deployments[0].uid
Invoke-RestMethod -Method POST "https://api.vercel.com/v2/deployments/$uid/aliases?teamId=$TEAM" `
  -Headers @{Authorization="Bearer $TOKEN"; "Content-Type"="application/json"} `
  -Body '{"alias":"total-hunter.com"}'
```

- [ ] **Step 5: Deploy backend — GCP git pull + restart**

```powershell
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git pull origin main && sudo systemctl restart totalhunter"
```

Run migration on GCP:
```powershell
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo -u totalhunter bash -c 'source venv/bin/activate && DATABASE_URL=\$(sudo cat /etc/systemd/system/totalhunter.service.d/override.conf | grep DATABASE_URL | cut -d= -f2-) alembic upgrade head'"
```

- [ ] **Step 6: Smoke test on prod**

1. Open `https://total-hunter.com/chests/<your-slug>`
2. Click "✏️ Ввести состав" — columns appear
3. Set rank + troop, click 💾 — columns disappear
4. Open `/dashboard/chests` → Players tab — rank+troop visible and editable

- [ ] **Step 7: Final commit (if any local changes remain)**

```powershell
git status
# commit any remaining changes
```
