# Chest Dashboard Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global per-pattern Chest Catalog with a per-clan `ChestConfiguration`
table, expose it through a self-service Web Dashboard ("Сундуки" section) where any logged-in
user manages their own collector's chest mapping/points/scoring without Google Sheets, and add
a public no-login summary page.

**Architecture:** New `ChestConfiguration` model (per-collector points + pattern-membership)
replaces `ChestTypeCatalog` as the join target in `GET /summary/{slug}`. `ChestTypeAlias`
drops `custom_display_name`/`enabled` (now `ChestConfiguration.custom_name`/`is_in_pattern`).
New `server/chest_dashboard.py` exposes the dashboard CRUD behind the site's existing JWT user
auth (`get_web_user`), scoped to the caller's own `ChestCollector.user_id`. Frontend gets two
new pages: `/dashboard/chests` (self-service editor) and `/chests/:slug` (public, no login).

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, pytest+httpx (backend); React Router,
existing `web/src/api.js` fetch wrapper (frontend).

## Global Constraints

- Resolution/guessing of `catalog_id` from free text (Phase 3a) is fully removed — the client
  always picks `catalog_id` from a dropdown built from known IDs; an unknown `catalog_id` in a
  request is a `400` (frontend bug signal, not a user-input error).
- `ChestConfiguration` is per-collector: `UniqueConstraint(collector_id, catalog_id)`. One row
  per official chest type per clan, holding `custom_name`, `points`, `is_in_pattern`.
- `GET /summary/{slug}` joins unconditionally against `ChestConfiguration` filtered by
  `is_in_pattern = true` — no more "no pattern → unscored summary" branch. A collector with no
  configured rows gets an empty summary (`grand_total: 0`), not an unscored dump.
- Existing collectors with a non-null `ChestCollector.pattern` (today: only slug
  `m00bqgjcl1xqUHRDvEa8bQ`, pattern `T9`) get their current `ChestTypeCatalog` points backfilled
  into `ChestConfiguration` by the Alembic migration itself — no data loss on deploy.
- All new dashboard endpoints live under `/api/v1/web/dashboard/chests*`, authenticated via
  `Depends(get_web_user)` (imported from `web_routes.py`), and must verify
  `collector.user_id == current_user.id` before any write — `403` otherwise.
- Google Sheets / `sync_catalog_to_db.py` / `Chest Catalog` and `Localizations` tabs are
  untouched — they remain the source for `catalog_options` (the dropdown's list+labels) and
  the localization fallback when `custom_name` is empty.
- No automatic Google Sheet creation anywhere in this feature (service account has zero Drive
  quota — confirmed blocker). The public page is a plain React route, not a generated Sheet.

---

### Task 1: Schema migration + `summary` rewrite — `ChestConfiguration`, simplified `ChestTypeAlias`, `management_token`

This task is intentionally larger than usual: renaming `ChestTypeAlias.canonical_type` to
`catalog_id` and dropping `enabled` breaks `server/chests.py`'s `get_chest_summary` the moment
the model changes, so the migration and the summary rewrite must land in the same task — a
split here would leave an intermediate commit where the server fails to import.

**Files:**
- Modify: `server/models.py` (around line 379-450, the "Сундуки — tenant isolation" section)
- Create: `server/alembic/versions/<new_revision>_chest_configuration.py`
- Modify: `server/chest_aliases.py` (full rewrite of the chest-alias handling — drop resolver)
- Modify: `server/tests/test_chest_aliases.py` (fix tests broken by the schema change)
- Modify: `server/chests.py` (the `get_chest_summary` function, lines ~287-353, and its model
  import line)
- Modify: `server/tests/test_chests.py` (summary test block, lines ~327-700)

**Interfaces:**
- Produces: `ChestConfiguration` model (`id, collector_id, catalog_id, custom_name, points,
  is_in_pattern`), `ChestTypeAlias.catalog_id` (renamed from `canonical_type`, `enabled` and
  `custom_display_name` columns removed), `ChestCollector.management_token` (nullable unique
  string), `GET /summary/{slug}` scored from `ChestConfiguration`. Task 2 (dashboard endpoints)
  depends on these exact names.

- [ ] **Step 1: Update models.py**

In `server/models.py`, replace the `ChestCollector`, `ChestTypeAlias` class bodies (lines
~379-449) with:

```python
class ChestCollector(Base):
    """
    Один сборщик внутри одного клана/королевства — единица тенант-изоляции.
    slug — непредсказуемый публичный идентификатор публичной страницы /chests/{slug}.
    management_token — одноразовый код передачи владения коллектором другому user_id.
    """
    __tablename__ = "chest_collectors"
    __table_args__ = (
        UniqueConstraint("kingdom", "clan", "user_id", name="uq_chest_collectors_tenant"),
    )

    id                = Column(Integer, primary_key=True)
    kingdom           = Column(String(50),  nullable=False)
    clan              = Column(String(100), nullable=False)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    slug              = Column(String(32), nullable=False, unique=True)
    pattern           = Column(String(8),  nullable=True)
    language          = Column(String(8),  nullable=True)
    management_token  = Column(String(32), nullable=True, unique=True)
    created_at        = Column(TIMESTAMP(timezone=True), nullable=False,
                               server_default=func.now())
```

(only the new `management_token` line is added; everything else in `ChestCollector` is
unchanged — keep `pattern` column, it's still read by the data-backfill migration and by the
old admin catalog tooling, just no longer by `summary`.)

```python
class ChestTypeAlias(Base):
    """Словарь маппинга сырого OCR-текста на официальный catalog_id, отдельно на каждого
    сборщика. Очки/кастомное имя/включение в подсчёт — в ChestConfiguration, не здесь."""
    __tablename__ = "chest_type_aliases"
    __table_args__ = (
        UniqueConstraint("collector_id", "raw_type", name="uq_chest_type_aliases_raw_type"),
    )

    id             = Column(Integer, primary_key=True)
    collector_id   = Column(Integer, ForeignKey("chest_collectors.id"),
                            nullable=False, index=True)
    raw_type       = Column(String(200), nullable=False)
    catalog_id     = Column(String(200), nullable=False)


class ChestConfiguration(Base):
    """Per-collector настройка одного официального сундука: свои очки, своё имя, входит ли
    в подсчёт клана. Заменяет глобальный ChestTypeCatalog как источник очков в summary."""
    __tablename__ = "chest_configurations"
    __table_args__ = (
        UniqueConstraint("collector_id", "catalog_id", name="uq_chest_config_collector_catalog"),
    )

    id            = Column(Integer, primary_key=True)
    collector_id  = Column(Integer, ForeignKey("chest_collectors.id"),
                           nullable=False, index=True)
    catalog_id    = Column(String(200), nullable=False)
    custom_name   = Column(String(200), nullable=True)
    points        = Column(Integer, nullable=False, server_default=text("0"))
    is_in_pattern = Column(Boolean, nullable=False, server_default=text("false"))
```

Place `ChestConfiguration` directly after `ChestTypeAlias` in the file (same "Сундуки" section,
before `ChestTypeCatalog`).

- [ ] **Step 2: Find the current migration head**

Run: `cd C:\BattleBot\server && python -c "from alembic.config import Config; from alembic.script import ScriptDirectory; print(ScriptDirectory.from_config(Config('alembic.ini')).get_current_head())"`
Expected: prints `z9z8z7z6z5z4` (the current head, confirmed in this plan's research — verify
it matches before continuing; if it printed something else, use that value as `down_revision`
below instead).

- [ ] **Step 3: Write the migration**

Create `server/alembic/versions/c4d5e6f7g8h9_chest_configuration.py`:

```python
"""add chest_configurations (per-collector points/pattern), rename chest_type_aliases.
canonical_type to catalog_id, drop enabled/custom_display_name, add management_token

Revision ID: c4d5e6f7g8h9
Revises: z9z8z7z6z5z4
Create Date: 2026-06-20

Phase 4: points and pattern-membership move from the global ChestTypeCatalog (one shared
table for every clan) to a new per-collector ChestConfiguration — each clan sets its own
points and decides which chests count, per docs/superpowers/specs/2026-06-20-chest-dashboard-
phase4-design.md. Existing collectors with a pattern set get their current catalog points
backfilled so they don't lose data on deploy.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'c4d5e6f7g8h9'
down_revision = 'z9z8z7z6z5z4'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'chest_configurations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey('chest_collectors.id'),
                  nullable=False, index=True),
        sa.Column('catalog_id', sa.String(200), nullable=False),
        sa.Column('custom_name', sa.String(200), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_in_pattern', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
        sa.UniqueConstraint('collector_id', 'catalog_id',
                            name='uq_chest_config_collector_catalog'),
    )

    op.alter_column('chest_type_aliases', 'canonical_type', new_column_name='catalog_id')
    op.drop_column('chest_type_aliases', 'enabled')

    op.add_column(
        'chest_collectors',
        sa.Column('management_token', sa.String(32), nullable=True, unique=True),
    )

    # Backfill: collectors that already have a pattern keep their current catalog points.
    op.execute("""
        INSERT INTO chest_configurations (collector_id, catalog_id, points, is_in_pattern)
        SELECT cc.id, ctc.canonical_type, ctc.points, true
        FROM chest_collectors cc
        JOIN chest_type_catalog ctc ON ctc.pattern = cc.pattern
        WHERE cc.pattern IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column('chest_collectors', 'management_token')
    op.add_column(
        'chest_type_aliases',
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.alter_column('chest_type_aliases', 'catalog_id', new_column_name='canonical_type')
    op.drop_table('chest_configurations')
```

If Step 2 printed a different head than `z9z8z7z6z5z4`, replace `down_revision` above with
that value before continuing.

- [ ] **Step 4: Run the migration against the test/dev DB to verify it applies cleanly**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/ -k "chest" -v 2>&1 | head -60`
Expected: many failures right now (models/tests reference the old `canonical_type`/`enabled`
fields) — this step is just confirming the test DB schema (SQLite, created fresh per test via
`Base.metadata.create_all`, not via Alembic) reflects the new model without import errors. A
`sqlalchemy.exc` error or Python `ImportError` here means Step 1's model edit has a syntax
problem — fix before continuing. Assertion failures are expected and addressed in Step 5-6.

- [ ] **Step 5: Rewrite chest_aliases.py — drop the Phase 3a resolver, adapt to renamed column**

Replace the full contents of `server/chest_aliases.py` with:

```python
"""
chest_aliases.py — admin endpoint for syncing alias dictionaries from the
"Admin Sheet" (Google Sheets) into player_aliases / chest_type_aliases.

Auth: Bearer $ADMIN_TOKEN (same pattern as clan.py) — this is an owner/admin action,
not something the bot calls on a user's behalf.

Each sync is a full replace for the named collector: existing rows are deleted, then
the payload's rows are inserted. The Sheet is the source of truth.

Phase 4: chest_type_aliases.catalog_id is just a literal mapping target now — no resolution
of native-language text happens here (that was Phase 3a, removed). Per-clan self-service for
chest aliases now happens through the Web Dashboard (chest_dashboard.py); this endpoint stays
for Player Aliases sync and for the owner's own direct catalog_id entry if still useful.
"""
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ChestCollector, ChestTypeAlias, PlayerAlias

router = APIRouter(prefix="/api/v1/chests", tags=["chests"])

_bearer = HTTPBearer(auto_error=False)
_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not _ADMIN_TOKEN or creds is None or creds.credentials != _ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


class PlayerAliasIn(BaseModel):
    raw_name: str
    canonical_name: str


class ChestAliasIn(BaseModel):
    raw_type: str
    canonical_type: str


class AliasImportPayload(BaseModel):
    collector_slug: str
    player_aliases: List[PlayerAliasIn] = []
    chest_aliases: List[ChestAliasIn] = []
    pattern: Optional[str] = None
    language: Optional[str] = None


@router.post("/aliases/import", dependencies=[Depends(_require_auth)])
async def import_aliases(payload: AliasImportPayload, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == payload.collector_slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    collector_id = collector.id
    if payload.pattern is not None:
        collector.pattern = payload.pattern
    if payload.language is not None:
        collector.language = payload.language

    await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector_id))
    await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector_id))

    for item in payload.player_aliases:
        db.add(PlayerAlias(collector_id=collector_id, raw_name=item.raw_name,
                           canonical_name=item.canonical_name))
    for item in payload.chest_aliases:
        db.add(ChestTypeAlias(collector_id=collector_id, raw_type=item.raw_type,
                              catalog_id=item.canonical_type))

    await db.commit()
    return {
        "ok": True,
        "player_aliases": len(payload.player_aliases),
        "chest_aliases": len(payload.chest_aliases),
    }
```

Note: the wire field is still named `canonical_type` in `ChestAliasIn` (so
`sync_admin_sheet_to_db.py` keeps working with zero changes) — only the stored DB attribute
is `catalog_id`. The `enabled` field is gone from the payload; if the Sheet still sends it,
Pydantic silently ignores the unknown key (default `BaseModel` behavior, no `extra="forbid"`
set anywhere in this file).

- [ ] **Step 6: Fix test_chest_aliases.py**

Replace the full contents of `server/tests/test_chest_aliases.py` with:

```python
"""Tests for chest_aliases.py — admin endpoint for syncing alias dictionaries."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import ChestCollector, PlayerAlias, ChestTypeAlias, User

ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]


async def _create_collector(db, slug=None):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6))
    db.add(user)
    await db.flush()
    collector = ChestCollector(
        kingdom="K1", clan="ClanA", user_id=user.id,
        slug=slug or secrets.token_urlsafe(16),
    )
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_import_aliases_no_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/aliases/import", json={
            "collector_slug": "whatever", "player_aliases": [], "chest_aliases": [],
        })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_aliases_wrong_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": "whatever", "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": "Bearer not-the-real-token"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_aliases_unknown_slug_returns_404(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": "does-not-exist", "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_import_aliases_full_replace(db_session):
    collector = await _create_collector(db_session)
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="OldRawType",
                                  catalog_id="OldCatalogId"))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={
                "collector_slug": slug,
                "player_aliases": [{"raw_name": "Machet", "canonical_name": "MACHETE"}],
                "chest_aliases": [{"raw_type": "Эпический отр", "canonical_type": "Epic Arachne"}],
            },
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"ok": True, "player_aliases": 1, "chest_aliases": 1}

    player_rows = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(player_rows) == 1
    assert player_rows[0].raw_name == "Machet"
    assert player_rows[0].canonical_name == "MACHETE"

    type_rows = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(type_rows) == 1
    assert type_rows[0].raw_type == "Эпический отр"
    assert type_rows[0].catalog_id == "Epic Arachne"


@pytest.mark.asyncio
async def test_import_aliases_empty_lists_clear_existing(db_session):
    collector = await _create_collector(db_session)
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "player_aliases": 0, "chest_aliases": 0}

    remaining = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_import_aliases_sets_pattern_and_language(db_session):
    collector = await _create_collector(db_session)
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [], "chest_aliases": [],
                  "pattern": "T9", "language": "ru"},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.pattern == "T9"
    assert collector.language == "ru"


@pytest.mark.asyncio
async def test_import_aliases_omitted_pattern_leaves_existing_value(db_session):
    collector = await _create_collector(db_session)
    collector.pattern = "T9"
    collector.language = "ru"
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.pattern == "T9"
    assert collector.language == "ru"
```

This drops the two `chest_alias_defaults_to_enabled`/`chest_alias_can_be_disabled` tests
(the `enabled` field no longer exists on `ChestTypeAlias`) and the four Phase 3a resolution
tests (resolver code removed in Step 5) — all superseded by Task 2's dashboard tests, which
cover `is_in_pattern` instead.

- [ ] **Step 7: Run this file's tests**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chest_aliases.py -v`
Expected: all 7 tests PASS.

**Do not commit yet — `server/chests.py` still references the renamed/removed columns
(`ChestTypeAlias.canonical_type`, `ChestTypeAlias.enabled`, `ChestTypeCatalog`/`pattern`) and
won't even import cleanly until the remaining steps in this task fix it.** Continue directly
into rewriting `get_chest_summary` below before any commit — splitting here would leave a
broken intermediate state (`chests.py` raising `AttributeError` on the renamed column).

- [ ] **Step 8: Read the current `get_chest_summary` to confirm line numbers**

Run: `grep -n "_pivot_summary\|def get_chest_summary\|ChestTypeCatalog" C:\BattleBot\server\chests.py`
Use the printed line numbers to locate the exact block to replace in Step 3 (line numbers may
have shifted slightly since this plan was written if Task 1 touched this file — it didn't, so
they should match the plan's references above).

- [ ] **Step 9: Write the failing test**

Add to `server/tests/test_chests.py` (after the existing summary test block, before any
later non-summary tests in the file):

```python
@pytest.mark.asyncio
async def test_summary_uses_chest_configuration_points_and_custom_name(db_session):
    from models import ChestConfiguration, ChestTypeAlias, Chest

    user = await _create_user(db_session, hwid="hwid-cfg")
    collector = ChestCollector(kingdom="K1", clan="ClanCfg", user_id=user.id,
                               slug=secrets.token_urlsafe(16), language="ru")
    db_session.add(collector)
    await db_session.flush()

    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="RawX",
                                  catalog_id="Epic Arachne"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Epic Arachne",
                                      custom_name="Толстяк", points=40, is_in_pattern=True))
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1",
                         chest_type_raw="RawX", collected_at="2026-06-20T10:00:00"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == ["Толстяк"]
    assert body["totals"] == {"Толстяк": 1, "grand_total": 1, "total_points": 40}
    assert body["players"][0] == {"name": "P1", "counts": {"Толстяк": 1}, "total": 1,
                                  "points": 40}


@pytest.mark.asyncio
async def test_summary_excludes_chest_not_in_pattern(db_session):
    from models import ChestConfiguration, ChestTypeAlias, Chest

    user = await _create_user(db_session, hwid="hwid-cfg2")
    collector = ChestCollector(kingdom="K1", clan="ClanCfg2", user_id=user.id,
                               slug=secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.flush()

    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="RawY",
                                  catalog_id="Common Crypt 5"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common Crypt 5",
                                      points=5, is_in_pattern=False))
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1",
                         chest_type_raw="RawY", collected_at="2026-06-20T10:00:00"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == []
    assert body["totals"] == {"grand_total": 0, "total_points": 0}
    assert body["players"] == []


@pytest.mark.asyncio
async def test_summary_no_configuration_returns_empty(db_session):
    from models import Chest

    user = await _create_user(db_session, hwid="hwid-cfg3")
    collector = ChestCollector(kingdom="K1", clan="ClanCfg3", user_id=user.id,
                               slug=secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.flush()
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1",
                         chest_type_raw="Unconfigured", collected_at="2026-06-20T10:00:00"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    assert resp.json()["totals"] == {"grand_total": 0, "total_points": 0}
```

- [ ] **Step 10: Run to verify the new tests fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chests.py -v -k "chest_configuration or excludes_chest_not_in_pattern or no_configuration_returns_empty"`
Expected: FAIL (old code still joins `ChestTypeCatalog`/`pattern`, `ChestConfiguration` isn't
read at all yet).

- [ ] **Step 11: Replace get_chest_summary**

In `server/chests.py`, replace the entire `get_chest_summary` function (and remove the
`if not collector.pattern:` branch and its call to `_pivot_summary` — `_pivot_summary` the
unscored helper becomes dead code, delete it too; keep `_pivot_summary_scored`, renaming it
back to `_pivot_summary` since it's now the only path) with:

```python
@router.get("/summary/{slug}")
async def get_chest_summary(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    sender_expr = func.coalesce(PlayerAlias.canonical_name, Chest.sender_raw)
    chest_type_expr = func.coalesce(ChestTypeAlias.catalog_id, Chest.chest_type_raw)
    display_expr = func.coalesce(ChestConfiguration.custom_name,
                                 ChestLocalization.display_text, chest_type_expr)

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

    return _pivot_summary(collector.kingdom, collector.clan, rows)
```

Update the import line near the top of `server/chests.py` (currently `from models import
Chest, ChestCollector, ChestLocalization, ChestTypeAlias, ChestTypeCatalog, Hunt,
PlayerAlias, Transaction, User`) to:
```python
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestLocalization, ChestTypeAlias, Hunt,
    PlayerAlias, Transaction, User,
)
```
(`ChestTypeCatalog` import dropped — no longer referenced in this file.)

Note the old `_resolve_chest_aliases`-style `or_(ChestTypeAlias.id.is_(None),
ChestTypeAlias.enabled.is_(True))` filter is gone — `enabled` no longer exists; exclusion from
scoring is now entirely controlled by `is_in_pattern` on `ChestConfiguration`, enforced by the
`join` (not `outerjoin`) above.

- [ ] **Step 12: Run to verify the new tests pass, then check for regressions in the old summary tests**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chests.py -v`
Expected: the 3 new tests PASS. The pre-existing summary tests
(`test_summary_aggregates_players_and_chest_types`,
`test_summary_applies_alias_added_after_import_without_reimport`,
`test_summary_collapses_many_raw_senders_aliased_to_same_canonical`,
`test_summary_no_pattern_has_no_points_key`,
`test_summary_with_pattern_excludes_offcatalog_chests_entirely`,
`test_summary_player_with_only_offcatalog_chests_is_excluded`,
`test_summary_uses_localization_when_present`,
`test_summary_falls_back_to_english_when_no_localization`,
`test_summary_no_pattern_excludes_disabled_alias_type`,
`test_summary_with_pattern_excludes_disabled_alias_type`) FAIL — they were written against
the old `ChestTypeCatalog`/`pattern`/`enabled` design. This is expected; Step 13 fixes them.

- [ ] **Step 13: Fix the pre-existing summary tests**

Open `server/tests/test_chests.py`. For every summary test from line ~327 onward that
constructs a `ChestTypeCatalog` row or sets `collector.pattern`, replace that setup with a
`ChestConfiguration` row, and replace any `ChestTypeAlias(..., canonical_type=...)` or
`enabled=...` kwargs with `catalog_id=...` (drop `enabled` entirely). Concretely:

- `test_summary_aggregates_players_and_chest_types`, `test_summary_empty_collector_returns_empty_lists`,
  `test_summary_collector_with_zero_chests_returns_empty_lists`,
  `test_summary_applies_alias_added_after_import_without_reimport`,
  `test_summary_collapses_many_raw_senders_aliased_to_same_canonical` — these don't currently
  set a pattern/catalog at all (they exercise the old *unscored* branch). Since that branch is
  removed, each of these tests must now add a `ChestConfiguration(catalog_id=<the type used>,
  points=0, is_in_pattern=True)` row for every distinct chest type it expects to see in the
  output, matching whatever `canonical_type`/`chest_type_raw` value the test already uses.
  Rename any `ChestTypeAlias(canonical_type=...)` kwarg to `catalog_id=...`.
- `test_summary_no_pattern_has_no_points_key` — delete this test entirely; "no pattern" no
  longer exists as a distinct mode (every summary call is now the scored path; an unconfigured
  collector returns an empty summary, covered by `test_summary_no_configuration_returns_empty`
  added in Step 2).
- `test_summary_with_pattern_excludes_offcatalog_chests_entirely`,
  `test_summary_player_with_only_offcatalog_chests_is_excluded`,
  `test_summary_uses_localization_when_present`,
  `test_summary_falls_back_to_english_when_no_localization` — replace
  `collector.pattern = "T9"` + `ChestTypeCatalog(canonical_type=X, pattern="T9", points=N)`
  with `ChestConfiguration(catalog_id=X, points=N, is_in_pattern=True)` (drop the `pattern`
  field entirely — `ChestConfiguration` has no pattern column, it's per-clan already). For a
  chest type the test expects to be EXCLUDED from the summary, simply don't create a
  `ChestConfiguration` row for it (instead of relying on `pattern` mismatch) — same effect.
- `test_summary_no_pattern_excludes_disabled_alias_type` — delete this test; with no `pattern`
  concept and no `enabled` column, disabling now means "no `ChestConfiguration` row, or
  `is_in_pattern=False`", already covered by `test_summary_excludes_chest_not_in_pattern`
  (Step 9).
- `test_summary_with_pattern_excludes_disabled_alias_type` — same: delete, already covered.

After editing, every remaining test in the summary block should construct exactly the rows it
needs via `ChestTypeAlias(raw_type=..., catalog_id=...)` and, for any type expected to count,
`ChestConfiguration(collector_id=..., catalog_id=..., points=..., is_in_pattern=True)`.

- [ ] **Step 14: Run the full file again**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chests.py -v`
Expected: all tests PASS (the 3 new ones from Step 9, plus every pre-existing test either
fixed or deleted per Step 13 — none left failing).

- [ ] **Step 15: Run the full server suite for regressions**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest -v 2>&1 | tail -15`
Expected: only the 3 known pre-existing unrelated failures remain (`test_roy.py` x2,
`test_version_bump.py`) — confirm no new failures outside `test_chests.py`/`test_chest_aliases.py`.

- [ ] **Step 16: Commit**

```bash
cd C:\BattleBot
git add server/models.py server/alembic/versions/c4d5e6f7g8h9_chest_configuration.py server/chest_aliases.py server/tests/test_chest_aliases.py server/chests.py server/tests/test_chests.py
git commit -m "feat(chests): add per-collector ChestConfiguration, score summary from it

Points/pattern-membership move from the global ChestTypeCatalog to a new
per-clan table; ChestTypeAlias becomes a pure raw->catalog_id mapping.
Migration backfills existing T9 collector's current catalog points so
nothing is lost. chest_aliases.py drops the Phase 3a native-language
resolver entirely - the dashboard's explicit dropdown (Task 2) replaces
it. GET /summary/{slug} now INNER JOINs ChestConfiguration filtered by
is_in_pattern instead of the old global catalog+pattern match; an
unconfigured collector returns an empty summary instead of an unscored
dump of every collected chest."
```

---

### Task 2: Web Dashboard endpoints (`server/chest_dashboard.py`)

**Files:**
- Create: `server/chest_dashboard.py`
- Modify: `server/main.py` (register the new router)
- Test: `server/tests/test_chest_dashboard.py`

**Interfaces:**
- Consumes: `web_routes.get_web_user` (existing JWT auth dependency), `models.ChestCollector`,
  `ChestTypeAlias`, `ChestConfiguration`, `ChestTypeCatalog`, `ChestLocalization` (Task 1).
- Produces: `GET /api/v1/web/dashboard/chests`, `POST /api/v1/web/dashboard/chests/rows`,
  `POST /api/v1/web/dashboard/chests/management-token`,
  `POST /api/v1/web/dashboard/chests/claim`,
  `PATCH /api/v1/web/dashboard/chests/{slug}/language` — used by Task 3's frontend.

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_chest_dashboard.py`:

```python
"""Tests for chest_dashboard.py — self-service chest mapping for the logged-in user."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestLocalization, ChestTypeAlias,
    ChestTypeCatalog, User,
)
from web_routes import create_jwt


async def _create_user_with_token(db, email="owner@example.com"):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6),
               email=email)
    db.add(user)
    await db.flush()
    token = create_jwt(user.id, email)
    return user, token


async def _create_collector(db, user_id, slug=None, language=None):
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=user_id,
                               slug=slug or secrets.token_urlsafe(16), language=language)
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_get_chests_no_token_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/web/dashboard/chests")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_chests_returns_only_own_collectors(db_session):
    user, token = await _create_user_with_token(db_session)
    other_user, _ = await _create_user_with_token(db_session, email="other@example.com")
    mine = await _create_collector(db_session, user.id, slug="mine-slug")
    await _create_collector(db_session, other_user.id, slug="not-mine-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()["collectors"]]
    assert slugs == ["mine-slug"]


@pytest.mark.asyncio
async def test_get_chests_combines_alias_config_and_unmapped_raw(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="combo-slug", language="ru")
    # mapped + configured
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="Raw1",
                                  catalog_id="Epic Arachne"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Epic Arachne",
                                      custom_name="Толстяк", points=40, is_in_pattern=True))
    # configured but never seen by the bot (manually added)
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common Crypt 5",
                                      points=5, is_in_pattern=True))
    # seen by the bot, never mapped
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1", chest_type_raw="Raw2",
                         collected_at="2026-06-20T10:00:00"))
    db_session.add(ChestTypeCatalog(canonical_type="Epic Arachne", pattern="T9", points=40))
    db_session.add(ChestLocalization(canonical_type="Epic Arachne", language="ru",
                                     display_text="Эпическая Арахна"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    rows = {(r["raw_type"], r["catalog_id"]) for r in collector_data["rows"]}
    assert ("Raw1", "Epic Arachne") in rows
    assert (None, "Common Crypt 5") in rows
    assert ("Raw2", None) in rows

    options = {o["catalog_id"]: o["label"] for o in collector_data["catalog_options"]}
    assert options["Epic Arachne"] == "Эпическая Арахна"


@pytest.mark.asyncio
async def test_post_rows_rejects_unknown_catalog_id(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="bad-catalog-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/web/dashboard/chests/rows",
            json={"collector_slug": "bad-catalog-slug",
                 "rows": [{"raw_type": "X", "catalog_id": "Not A Real Chest",
                           "custom_name": None, "points": 5, "is_in_pattern": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_post_rows_rejects_other_users_collector(db_session):
    user, token = await _create_user_with_token(db_session)
    other_user, _ = await _create_user_with_token(db_session, email="other2@example.com")
    await _create_collector(db_session, other_user.id, slug="someone-elses-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/web/dashboard/chests/rows",
            json={"collector_slug": "someone-elses-slug", "rows": []},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_rows_upserts_alias_and_configuration(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="upsert-slug")
    db_session.add(ChestTypeCatalog(canonical_type="Epic Arachne", pattern="T9", points=40))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/web/dashboard/chests/rows",
            json={"collector_slug": "upsert-slug",
                 "rows": [{"raw_type": "RawAB", "catalog_id": "Epic Arachne",
                           "custom_name": "Толстяк", "points": 99, "is_in_pattern": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    alias = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert alias.raw_type == "RawAB" and alias.catalog_id == "Epic Arachne"

    config = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalar_one()
    assert config.points == 99 and config.is_in_pattern is True
    assert config.custom_name == "Толстяк"


@pytest.mark.asyncio
async def test_management_token_then_claim_transfers_ownership(db_session):
    owner, owner_token = await _create_user_with_token(db_session, email="a@example.com")
    claimant, claimant_token = await _create_user_with_token(db_session, email="b@example.com")
    collector = await _create_collector(db_session, owner.id, slug="transferable-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen_resp = await client.post(
            "/api/v1/web/dashboard/chests/management-token",
            json={"collector_slug": "transferable-slug"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert gen_resp.status_code == 200
        code = gen_resp.json()["code"]

        claim_resp = await client.post(
            "/api/v1/web/dashboard/chests/claim",
            json={"code": code},
            headers={"Authorization": f"Bearer {claimant_token}"},
        )
        assert claim_resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.user_id == claimant.id
    assert collector.management_token is None


@pytest.mark.asyncio
async def test_claim_unknown_code_returns_404(db_session):
    _, token = await _create_user_with_token(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/web/dashboard/chests/claim",
            json={"code": "does-not-exist"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_language_updates_own_collector(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="lang-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/api/v1/web/dashboard/chests/lang-slug/language",
            json={"language": "en"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    await db_session.refresh(collector)
    assert collector.language == "en"


@pytest.mark.asyncio
async def test_patch_language_rejects_other_users_collector(db_session):
    owner, _ = await _create_user_with_token(db_session, email="c@example.com")
    intruder, intruder_token = await _create_user_with_token(db_session, email="d@example.com")
    await _create_collector(db_session, owner.id, slug="protected-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/api/v1/web/dashboard/chests/protected-slug/language",
            json={"language": "en"},
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to verify failure**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chest_dashboard.py -v`
Expected: FAIL on collection (`ModuleNotFoundError: No module named 'chest_dashboard'` or
import error from `main.py` not having the router yet) — confirms the file doesn't exist.

- [ ] **Step 3: Check the User model has an `email` column**

Run: `grep -n "email" C:\BattleBot\server\models.py | head -5`
If `User` has no `email` column, the tests' `User(..., email=email)` kwarg will fail at
runtime with a `TypeError`. If that's the case, drop the `email=email` kwarg from
`_create_user_with_token` in the test file (Step 1) and call `create_jwt(user.id, email)`
with a literal placeholder string — `create_jwt` only encodes `email` into the JWT payload,
it doesn't need it to exist on the row for `get_web_user` (which only reads `sub`). Re-run
Step 1's file edit with that adjustment before proceeding if needed.

- [ ] **Step 4: Implement chest_dashboard.py**

Create `server/chest_dashboard.py`:

```python
"""
chest_dashboard.py — self-service Web Dashboard for chest mapping/scoring.

Auth: site session (JWT Bearer via get_web_user) — any logged-in user manages only their
own ChestCollector rows (collector.user_id == current_user.id), no ADMIN_TOKEN involved.

Phase 4: replaces the Google Sheets + ADMIN_TOKEN workflow for chest_type_aliases/
chest_configurations with a UI any clan can use without owner involvement. Player Aliases
and the global Chest Catalog/Localizations Sheets are untouched (see design doc).
"""
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestLocalization, ChestTypeAlias,
    ChestTypeCatalog, User,
)
from web_routes import get_web_user

router = APIRouter(prefix="/api/v1/web/dashboard/chests", tags=["chest-dashboard"])


async def _load_known_catalog_ids(db: AsyncSession) -> set:
    catalog_ids = (await db.execute(select(ChestTypeCatalog.canonical_type))).scalars().all()
    localization_ids = (await db.execute(select(ChestLocalization.canonical_type))).scalars().all()
    return set(catalog_ids) | set(localization_ids)


async def _load_catalog_options(db: AsyncSession, language: Optional[str]) -> list:
    known_ids = sorted(await _load_known_catalog_ids(db))
    labels = {}
    if language:
        rows = (await db.execute(
            select(ChestLocalization.canonical_type, ChestLocalization.display_text)
            .where(ChestLocalization.language == language)
        )).all()
        labels = dict(rows)
    options = [{"catalog_id": cid, "label": labels.get(cid, cid)} for cid in known_ids]
    options.sort(key=lambda o: o["label"])
    return options


async def _collector_rows(db: AsyncSession, collector: ChestCollector) -> list:
    aliases = (await db.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    configs = (await db.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalars().all()
    config_by_catalog_id = {c.catalog_id: c for c in configs}

    rows = []
    seen_catalog_ids = set()
    for alias in aliases:
        config = config_by_catalog_id.get(alias.catalog_id)
        seen_catalog_ids.add(alias.catalog_id)
        rows.append({
            "raw_type": alias.raw_type, "catalog_id": alias.catalog_id,
            "custom_name": config.custom_name if config else None,
            "points": config.points if config else 0,
            "is_in_pattern": config.is_in_pattern if config else False,
        })
    for config in configs:
        if config.catalog_id in seen_catalog_ids:
            continue
        rows.append({
            "raw_type": None, "catalog_id": config.catalog_id,
            "custom_name": config.custom_name, "points": config.points,
            "is_in_pattern": config.is_in_pattern,
        })

    mapped_raw_types = {a.raw_type for a in aliases}
    unmapped = (await db.execute(
        select(Chest.chest_type_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_type in unmapped:
        if raw_type in mapped_raw_types:
            continue
        rows.append({"raw_type": raw_type, "catalog_id": None, "custom_name": None,
                     "points": 0, "is_in_pattern": False})

    return rows


@router.get("")
async def get_dashboard_chests(user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.user_id == user.id)
    )).scalars().all()

    result = []
    for collector in collectors:
        result.append({
            "slug": collector.slug, "kingdom": collector.kingdom, "clan": collector.clan,
            "language": collector.language,
            "public_url": f"https://total-hunter.com/chests/{collector.slug}",
            "rows": await _collector_rows(db, collector),
            "catalog_options": await _load_catalog_options(db, collector.language),
        })
    return {"collectors": result}


class RowIn(BaseModel):
    raw_type: Optional[str] = None
    catalog_id: Optional[str] = None
    custom_name: Optional[str] = None
    points: int = 0
    is_in_pattern: bool = False


class RowsPayload(BaseModel):
    collector_slug: str
    rows: List[RowIn] = []


async def _get_own_collector(db: AsyncSession, slug: str, user: User) -> ChestCollector:
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    if collector.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your collector")
    return collector


@router.post("/rows")
async def post_dashboard_rows(payload: RowsPayload, user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)

    known_ids = await _load_known_catalog_ids(db)
    for row in payload.rows:
        if row.catalog_id is not None and row.catalog_id not in known_ids:
            raise HTTPException(status_code=400,
                                detail=f"Unknown catalog_id: {row.catalog_id!r}")

    for row in payload.rows:
        if row.raw_type is not None and row.catalog_id is not None:
            existing_alias = (await db.execute(
                select(ChestTypeAlias).where(
                    ChestTypeAlias.collector_id == collector.id,
                    ChestTypeAlias.raw_type == row.raw_type,
                )
            )).scalar_one_or_none()
            if existing_alias:
                existing_alias.catalog_id = row.catalog_id
            else:
                db.add(ChestTypeAlias(collector_id=collector.id, raw_type=row.raw_type,
                                      catalog_id=row.catalog_id))

        if row.catalog_id is not None:
            existing_config = (await db.execute(
                select(ChestConfiguration).where(
                    ChestConfiguration.collector_id == collector.id,
                    ChestConfiguration.catalog_id == row.catalog_id,
                )
            )).scalar_one_or_none()
            if existing_config:
                existing_config.custom_name = row.custom_name
                existing_config.points = row.points
                existing_config.is_in_pattern = row.is_in_pattern
            else:
                db.add(ChestConfiguration(collector_id=collector.id, catalog_id=row.catalog_id,
                                          custom_name=row.custom_name, points=row.points,
                                          is_in_pattern=row.is_in_pattern))

    await db.commit()
    return {"ok": True}


class CollectorSlugPayload(BaseModel):
    collector_slug: str


@router.post("/management-token")
async def create_management_token(payload: CollectorSlugPayload,
                                   user: User = Depends(get_web_user),
                                   db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)
    code = secrets.token_urlsafe(16)
    collector.management_token = code
    await db.commit()
    return {"code": code}


class ClaimPayload(BaseModel):
    code: str


@router.post("/claim")
async def claim_collector(payload: ClaimPayload, user: User = Depends(get_web_user),
                          db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.management_token == payload.code)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Invalid code")
    collector.user_id = user.id
    collector.management_token = None
    await db.commit()
    return {"ok": True, "slug": collector.slug}


class LanguagePayload(BaseModel):
    language: str


@router.patch("/{slug}/language")
async def update_language(slug: str, payload: LanguagePayload,
                          user: User = Depends(get_web_user),
                          db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    collector.language = payload.language
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 5: Register the router**

In `server/main.py`, find the line `from chest_catalog import router as chest_catalog_router`
and add immediately after it:
```python
from chest_dashboard import router as chest_dashboard_router
```
Find the line `app.include_router(chest_catalog_router)` and add immediately after it:
```python
app.include_router(chest_dashboard_router)
```

- [ ] **Step 6: Run the dashboard test file**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chest_dashboard.py -v`
Expected: all tests PASS. If `test_get_chests_returns_only_own_collectors` or similar fails
on the `User(..., email=...)` kwarg (per Step 3's check), apply that adjustment now.

- [ ] **Step 7: Run the full suite for regressions**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest -v 2>&1 | tail -15`
Expected: only the 3 known pre-existing unrelated failures remain.

- [ ] **Step 8: Commit**

```bash
cd C:\BattleBot
git add server/chest_dashboard.py server/main.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): add self-service Web Dashboard for chest mapping

GET/POST /api/v1/web/dashboard/chests* lets any logged-in user manage
their own collector's raw->catalog_id mapping, per-clan points, and
pattern membership directly - no Google Sheets, no ADMIN_TOKEN. Includes
one-time management-token transfer of collector ownership and per-clan
language selection."
```

---

### Task 3: Dashboard frontend — `/dashboard/chests`

**Files:**
- Create: `web/src/pages/ChestsPage.jsx`
- Modify: `web/src/api.js` (add dashboard chest methods)
- Modify: `web/src/App.jsx` (add route)
- Modify: `web/src/components/Layout.jsx` (add nav entry)
- Modify: `web/src/dashboard_content.js`, `web/src/dashboard_content.en.js` (add `chests` nav
  label + page strings)

**Interfaces:**
- Consumes: `GET /api/v1/web/dashboard/chests`, `POST .../rows`, `POST
  .../management-token`, `POST .../claim`, `PATCH .../{slug}/language` (Task 2).

- [ ] **Step 1: Add api.js methods**

In `web/src/api.js`, inside the `export const api = { ... }` object, add:
```js
  dashboardChests:      ()              => request('GET',   '/web/dashboard/chests'),
  dashboardChestsSave:  (slug, rows)    => request('POST',  '/web/dashboard/chests/rows', { collector_slug: slug, rows }),
  dashboardChestsToken: (slug)          => request('POST',  '/web/dashboard/chests/management-token', { collector_slug: slug }),
  dashboardChestsClaim: (code)          => request('POST',  '/web/dashboard/chests/claim', { code }),
  dashboardChestsLang:  (slug, language) => request('PATCH', `/web/dashboard/chests/${slug}/language`, { language }),
```
(Match the existing alignment style in the file — see `linkVerify`/`hwidReset` nearby.)

- [ ] **Step 2: Add nav label content**

In `web/src/dashboard_content.js`, inside the `nav: { ... }` object (near `devices:
'Устройства'`), add:
```js
    chests:       'Сундуки',
```
In `web/src/dashboard_content.en.js`, find the matching `nav: { ... }` object and add:
```js
    chests:       'Chests',
```

- [ ] **Step 3: Add the page-level content block**

In `web/src/dashboard_content.js`, after the `devices: { ... }` block, add:
```js
  chests: {
    title: 'Сундуки',
    rawCol: 'Сырой OCR',
    catalogCol: 'Официальный сундук',
    customNameCol: 'Своё название',
    pointsCol: 'Очки',
    inPatternCol: 'В паттерне',
    addRow: 'Добавить сундук вручную',
    save: 'Сохранить',
    saved: 'Сохранено',
    publicLink: 'Публичная страница клана',
    generateToken: 'Сгенерировать код передачи',
    claimPlaceholder: 'Код передачи',
    claimBtn: 'Принять управление',
    noCatalog: '— выбрать —',
    language: 'Язык клана',
  },
```
In `web/src/dashboard_content.en.js`, add the matching English block:
```js
  chests: {
    title: 'Chests',
    rawCol: 'Raw OCR',
    catalogCol: 'Official Chest',
    customNameCol: 'Custom Name',
    pointsCol: 'Points',
    inPatternCol: 'In Pattern',
    addRow: 'Add chest manually',
    save: 'Save',
    saved: 'Saved',
    publicLink: 'Clan public page',
    generateToken: 'Generate transfer code',
    claimPlaceholder: 'Transfer code',
    claimBtn: 'Claim management',
    noCatalog: '— select —',
    language: 'Clan language',
  },
```

- [ ] **Step 4: Write ChestsPage.jsx**

Create `web/src/pages/ChestsPage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

export default function ChestsPage() {
  const [collectors, setCollectors] = useState(null)
  const [rowsByCollector, setRowsByCollector] = useState({})
  const [msg, setMsg] = useState('')
  const [claimCode, setClaimCode] = useState('')
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.chests
  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Сундуки' : 'Total Hunter — Chests',
    description: lang === 'ru' ? 'Настройка сундуков клана.' : 'Configure your clan chests.',
  })

  async function refresh() {
    const data = await api.dashboardChests()
    setCollectors(data.collectors)
    const next = {}
    for (const c of data.collectors) next[c.slug] = c.rows
    setRowsByCollector(next)
  }
  useEffect(() => { refresh() }, [])

  function updateRow(slug, index, field, value) {
    setRowsByCollector(prev => {
      const rows = [...prev[slug]]
      rows[index] = { ...rows[index], [field]: value }
      return { ...prev, [slug]: rows }
    })
  }

  function addRow(slug) {
    setRowsByCollector(prev => ({
      ...prev,
      [slug]: [...prev[slug], { raw_type: null, catalog_id: null, custom_name: null,
                                points: 0, is_in_pattern: false }],
    }))
  }

  async function save(slug) {
    await api.dashboardChestsSave(slug, rowsByCollector[slug])
    setMsg(cx.saved)
    await refresh()
  }

  async function genToken(slug) {
    const res = await api.dashboardChestsToken(slug)
    setMsg(res.code)
  }

  async function claim() {
    try {
      await api.dashboardChestsClaim(claimCode)
      setClaimCode('')
      await refresh()
    } catch (e) { setMsg(e.message) }
  }

  async function changeLanguage(slug, language) {
    await api.dashboardChestsLang(slug, language)
    await refresh()
  }

  if (!collectors) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>{cx.title}</h2>

      <div className="card" style={{ marginBottom: 16, maxWidth: 480 }}>
        <input
          value={claimCode}
          onChange={e => setClaimCode(e.target.value)}
          placeholder={cx.claimPlaceholder}
          style={{ marginRight: 8 }}
        />
        <button className="btn-secondary" onClick={claim}>{cx.claimBtn}</button>
      </div>

      {collectors.map(collector => (
        <div className="card" key={collector.slug} style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>{collector.kingdom} / {collector.clan}</div>
            <a href={collector.public_url} target="_blank" rel="noreferrer">{cx.publicLink}</a>
          </div>

          <div style={{ marginBottom: 12 }}>
            {cx.language}:
            <select
              value={collector.language || ''}
              onChange={e => changeLanguage(collector.slug, e.target.value)}
            >
              <option value="ru">ru</option>
              <option value="en">en</option>
            </select>
            <button className="btn-secondary" onClick={() => genToken(collector.slug)}>
              {cx.generateToken}
            </button>
          </div>

          <table style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>{cx.rawCol}</th>
                <th>{cx.catalogCol}</th>
                <th>{cx.customNameCol}</th>
                <th>{cx.pointsCol}</th>
                <th>{cx.inPatternCol}</th>
              </tr>
            </thead>
            <tbody>
              {rowsByCollector[collector.slug]?.map((row, i) => (
                <tr key={i}>
                  <td>{row.raw_type || '—'}</td>
                  <td>
                    <select
                      value={row.catalog_id || ''}
                      onChange={e => updateRow(collector.slug, i, 'catalog_id', e.target.value || null)}
                    >
                      <option value="">{cx.noCatalog}</option>
                      {collector.catalog_options.map(o => (
                        <option key={o.catalog_id} value={o.catalog_id}>{o.label}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      value={row.custom_name || ''}
                      onChange={e => updateRow(collector.slug, i, 'custom_name', e.target.value || null)}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.points}
                      onChange={e => updateRow(collector.slug, i, 'points', parseInt(e.target.value, 10) || 0)}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={row.is_in_pattern}
                      onChange={e => updateRow(collector.slug, i, 'is_in_pattern', e.target.checked)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <button className="btn-secondary" onClick={() => addRow(collector.slug)} style={{ marginTop: 12 }}>
            {cx.addRow}
          </button>
          <button className="btn-primary" onClick={() => save(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
            {cx.save}
          </button>
        </div>
      ))}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
```

- [ ] **Step 5: Register the route and nav entry**

In `web/src/App.jsx`, add the import near the other page imports:
```jsx
import ChestsPage from './pages/ChestsPage.jsx'
```
Add the route inside the `/dashboard` route block, after `<Route path="devices"
element={<DevicesPage />} />`:
```jsx
        <Route path="chests"       element={<ChestsPage />} />
```

In `web/src/components/Layout.jsx`, add to `NAV_KEYS` (after the `devices` entry):
```jsx
  { to: '/dashboard/chests',       icon: '⛁', key: 'chests' },
```

- [ ] **Step 6: Manual verification**

Run the dev server (`cd C:\BattleBot\web && npm run dev`), log in, navigate to
`/dashboard/chests`, confirm the page loads without console errors and the "Сундуки" nav
item appears. Full data verification happens after Task 2 is deployed to a server the
frontend can reach — note any blockers rather than guessing.

- [ ] **Step 7: Commit**

```bash
cd C:\BattleBot
git add web/src/pages/ChestsPage.jsx web/src/api.js web/src/App.jsx web/src/components/Layout.jsx web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "feat(web): add self-service Chests dashboard page

/dashboard/chests lets the logged-in user map raw OCR to official chest
types, set their own points/custom names, toggle pattern membership,
transfer collector ownership via a one-time code, and change clan
language - all without Google Sheets."
```

---

### Task 4: Public summary page — `/chests/:slug`

**Files:**
- Create: `web/src/pages/ChestSummaryPage.jsx`
- Modify: `web/src/App.jsx` (public route, no `PrivateRoute`)
- Modify: `web/src/api.js` (add public summary fetch — note: this one is unauthenticated and
  takes a slug, not the logged-in user's own data)

**Interfaces:**
- Consumes: existing `GET /api/v1/chests/summary/{slug}` (already public, untouched by this
  plan — see `server/chests.py`, unchanged response shape `{kingdom, clan, chest_types,
  players, totals}`).

- [ ] **Step 1: Add the api.js method**

In `web/src/api.js`, add (this one does NOT use `request()` since it must skip the JWT
Authorization header and the 401-redirect-to-login behavior — it's a public, unauthenticated
endpoint):
```js
export async function fetchChestSummary(slug) {
  const res = await fetch(`${BASE}/chests/summary/${slug}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}
```
(Add this as a standalone exported function in the same file, near the bottom, after the
`export const api = { ... }` block closes — not as a method inside `api`, since it
deliberately bypasses `request()`'s auth header logic.)

- [ ] **Step 2: Write ChestSummaryPage.jsx**

Create `web/src/pages/ChestSummaryPage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary } from '../api.js'

export default function ChestSummaryPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchChestSummary(slug).then(setData).catch(() => setError('not found'))
  }, [slug])

  if (error) return <div className="page-content">404</div>
  if (!data) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h2>{data.kingdom} / {data.clan}</h2>
      <table style={{ width: '100%' }}>
        <thead>
          <tr>
            <th>Player</th>
            {data.chest_types.map(t => <th key={t}>{t}</th>)}
            <th>Total</th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          {data.players.map(p => (
            <tr key={p.name}>
              <td>{p.name}</td>
              {data.chest_types.map(t => <td key={t}>{p.counts[t] || 0}</td>)}
              <td>{p.total}</td>
              <td>{p.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 3: Register the public route**

In `web/src/App.jsx`, add the import:
```jsx
import ChestSummaryPage from './pages/ChestSummaryPage.jsx'
```
Add a public route (NOT inside `/dashboard`, NOT wrapped in `PrivateRoute`) — place it near
the other public routes at the top of the `<Routes>` block:
```jsx
      <Route path="/chests/:slug" element={<ChestSummaryPage />} />
```

- [ ] **Step 4: Manual verification**

Run the dev server, navigate directly to `/chests/<a real slug, e.g.
m00bqgjcl1xqUHRDvEa8bQ>` without logging in, confirm the table renders. Try a fake slug,
confirm "404" renders instead of a crash.

- [ ] **Step 5: Commit**

```bash
cd C:\BattleBot
git add web/src/pages/ChestSummaryPage.jsx web/src/api.js web/src/App.jsx
git commit -m "feat(web): add public no-login chest summary page /chests/:slug

Replaces the planned Google-Sheet-auto-creation showcase (blocked by
zero service-account Drive quota) with a plain public React route
backed by the existing GET /api/v1/chests/summary/{slug}."
```

---

## After implementation

Deploy `server/` to GCP per the standard flow (`git pull` + `alembic upgrade head` +
`systemctl restart totalhunter`) — this plan includes a real schema migration with a data
backfill, run it carefully and verify the backfill produced rows for collector
`m00bqgjcl1xqUHRDvEa8bQ` (`SELECT * FROM chest_configurations WHERE collector_id = (SELECT id
FROM chest_collectors WHERE slug = 'm00bqgjcl1xqUHRDvEa8bQ')` should return 18 rows matching
the current T9 catalog points) before declaring done. Deploy `web/` to Vercel per the
standard 3-step flow (push + hook + alias) once Task 3/4 are merged.
