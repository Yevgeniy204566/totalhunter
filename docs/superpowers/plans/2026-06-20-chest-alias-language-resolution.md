# Chest Alias Language Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let admins write chest-type aliases in their clan's native language; the
`POST /api/v1/chests/aliases/import` endpoint resolves that text to the global English
`canonical_type` ID itself, instead of requiring the admin to know the English name.

**Architecture:** No DB schema change. `chest_aliases.py` gains a resolution step that runs
before the existing full-replace delete/insert: for each submitted `chest_aliases` row,
look up its `canonical_type` text either (a) directly against the set of already-known
English IDs (`chest_type_catalog` ∪ `chest_localizations.canonical_type`), or (b) by
reverse lookup in `chest_localizations` keyed on `(language=collector.language,
display_text=submitted text)`. Any unresolved row aborts the whole import with a `400`
naming every failing row, before any `DELETE`/`INSERT` runs.

**Tech Stack:** FastAPI, SQLAlchemy async, pytest + httpx (existing test stack, no new
dependencies).

## Global Constraints

- Resolution happens at import time, inside `POST /api/v1/chests/aliases/import` — not at
  summary-read time.
- Exact-match only after `.strip()` — no fuzzy/AI matching.
- If any `chest_aliases` row fails to resolve, the entire import is rejected (`400`); no
  partial writes. The error names every failing row (`raw_type` + submitted text) in one
  response, not just the first.
- If the collector has no `language` set, the literal-English fallback is the only path
  available; if a row still fails, the error explicitly says the collector has no language
  configured.
- `sync_admin_sheet_to_db.py` needs no code changes — it already just forwards the Sheet's
  column B text as `canonical_type`; only the meaning of that text changes (native language
  instead of English).

---

### Task 1: Resolve chest-alias canonical_type from native text at import time

**Files:**
- Modify: `server/chest_aliases.py`
- Test: `server/tests/test_chest_aliases.py`

**Interfaces:**
- Consumes: existing `models.ChestTypeCatalog` (`canonical_type`, `pattern`, `points`),
  `models.ChestLocalization` (`canonical_type`, `language`, `display_text`) — both already
  defined in `server/models.py`.
- Produces: `_resolve_chest_aliases(items: List[ChestAliasIn], language: Optional[str], db: AsyncSession) -> List[ChestAliasIn]`
  — used by `import_aliases`. Raises `HTTPException(400, ...)` if any item is unresolved.

- [ ] **Step 1: Write the failing tests**

Open `server/tests/test_chest_aliases.py`. Change the import line at the top from:

```python
from models import ChestCollector, PlayerAlias, ChestTypeAlias, User
```

to:

```python
from models import ChestCollector, PlayerAlias, ChestTypeAlias, ChestTypeCatalog, ChestLocalization, User
```

Append these four test functions at the end of the file:

```python
@pytest.mark.asyncio
async def test_import_aliases_resolves_native_text_via_localizations(db_session):
    collector = await _create_collector(db_session)
    collector.language = "ru"
    db_session.add(ChestLocalization(canonical_type="Yogwai", language="ru",
                                     display_text="Ёкай"))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Exon", "canonical_type": "Ёкай"}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert row.raw_type == "Exon"
    assert row.canonical_type == "Yogwai"


@pytest.mark.asyncio
async def test_import_aliases_accepts_known_english_literal_without_language(db_session):
    collector = await _create_collector(db_session)
    db_session.add(ChestTypeCatalog(canonical_type="Epic Crypt 25", pattern="T9", points=45))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Crpt25", "canonical_type": "Epic Crypt 25"}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert row.canonical_type == "Epic Crypt 25"


@pytest.mark.asyncio
async def test_import_aliases_unresolved_text_returns_400_naming_rows(db_session):
    collector = await _create_collector(db_session)
    collector.language = "ru"
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [
                      {"raw_type": "Exon", "canonical_type": "Ёкай"},
                      {"raw_type": "Zzz", "canonical_type": "Незнакомый сундук"},
                  ]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Exon" in detail and "Ёкай" in detail
    assert "Zzz" in detail and "Незнакомый сундук" in detail

    rows = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_import_aliases_unresolved_text_no_collector_language_returns_400(db_session):
    collector = await _create_collector(db_session)
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Exon", "canonical_type": "Ёкай"}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "не задан язык" in detail
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\BattleBot\server && python -m pytest tests/test_chest_aliases.py -v -k "resolves_native_text or known_english_literal or unresolved_text"`

Expected: `test_import_aliases_resolves_native_text_via_localizations` FAILS (assertion
`row.canonical_type == "Yogwai"` — actual value is `"Ёкай"`, since the endpoint currently
stores the submitted text unchanged). The two `unresolved_text` tests FAIL because the
endpoint currently returns `200` (no validation), not `400`. The
`known_english_literal_without_language` test PASSES already (current code passes the
literal through unchanged) — that's expected, it locks in the no-regression case.

- [ ] **Step 3: Implement the resolver and wire it into the endpoint**

Replace the full contents of `server/chest_aliases.py` with:

```python
"""
chest_aliases.py — admin endpoint for syncing alias dictionaries from the
"Admin Sheet" (Google Sheets) into player_aliases / chest_type_aliases.

Auth: Bearer $ADMIN_TOKEN (same pattern as clan.py) — this is an owner/admin action,
not something the bot calls on a user's behalf.

Each sync is a full replace for the named collector: existing rows are deleted, then
the payload's rows are inserted. The Sheet is the source of truth.

chest_aliases entries are submitted in the collector's own language (e.g. raw OCR text
fixed to clean Russian), not English. _resolve_chest_aliases translates each row's
canonical_type to the global English ID before it's stored, so chest_type_aliases.
canonical_type always stays an English ID — nothing downstream (catalog join, summary)
needs to know about this translation step.
"""
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ChestCollector, ChestLocalization, ChestTypeAlias, ChestTypeCatalog, PlayerAlias

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
    enabled: bool = True


class AliasImportPayload(BaseModel):
    collector_slug: str
    player_aliases: List[PlayerAliasIn] = []
    chest_aliases: List[ChestAliasIn] = []
    pattern: Optional[str] = None
    language: Optional[str] = None


async def _load_known_english_ids(db: AsyncSession) -> set:
    """Every canonical_type already known to the system, from either global table —
    used so admins who already type the literal English ID keep working unchanged."""
    catalog_ids = (await db.execute(select(ChestTypeCatalog.canonical_type))).scalars().all()
    localization_ids = (await db.execute(select(ChestLocalization.canonical_type))).scalars().all()
    return set(catalog_ids) | set(localization_ids)


async def _load_localization_map(db: AsyncSession, language: str) -> dict:
    """display_text -> canonical_type for one language, loaded once per import instead
    of one query per row."""
    rows = (await db.execute(
        select(ChestLocalization.display_text, ChestLocalization.canonical_type)
        .where(ChestLocalization.language == language)
    )).all()
    return {display_text: canonical_type for display_text, canonical_type in rows}


def _resolve_one(submitted: str, known_ids: set, localization_map: dict) -> Optional[str]:
    submitted = submitted.strip()
    if submitted in known_ids:
        return submitted
    return localization_map.get(submitted)


async def _resolve_chest_aliases(items: List[ChestAliasIn], language: Optional[str],
                                  db: AsyncSession) -> List[ChestAliasIn]:
    known_ids = await _load_known_english_ids(db)
    localization_map = await _load_localization_map(db, language) if language else {}

    resolved = []
    errors = []
    for item in items:
        canonical = _resolve_one(item.canonical_type, known_ids, localization_map)
        if canonical is None:
            errors.append((item.raw_type, item.canonical_type))
        else:
            resolved.append(ChestAliasIn(raw_type=item.raw_type, canonical_type=canonical,
                                         enabled=item.enabled))

    if errors:
        rows = "; ".join(f"raw={r!r}, clean={c!r}" for r, c in errors)
        detail = (f"Chest Aliases: не найден перевод для следующих строк — {rows}. "
                  "Добавьте перевод в Localizations (язык клана) или впишите английское "
                  "название напрямую.")
        if not language:
            detail += (" У коллектора не задан язык (Collector Settings), поэтому "
                       "обратный перевод недоступен.")
        raise HTTPException(status_code=400, detail=detail)

    return resolved


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

    resolved_chest_aliases = await _resolve_chest_aliases(
        payload.chest_aliases, collector.language, db)

    await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector_id))
    await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector_id))

    for item in payload.player_aliases:
        db.add(PlayerAlias(collector_id=collector_id, raw_name=item.raw_name,
                           canonical_name=item.canonical_name))
    for item in resolved_chest_aliases:
        db.add(ChestTypeAlias(collector_id=collector_id, raw_type=item.raw_type,
                              canonical_type=item.canonical_type, enabled=item.enabled))

    await db.commit()
    return {
        "ok": True,
        "player_aliases": len(payload.player_aliases),
        "chest_aliases": len(resolved_chest_aliases),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\BattleBot\server && python -m pytest tests/test_chest_aliases.py -v`

Expected: all tests in the file PASS, including the 4 new ones and the pre-existing ones
(`full_replace`, `empty_lists_clear_existing`, `sets_pattern_and_language`,
`chest_alias_defaults_to_enabled`, `chest_alias_can_be_disabled`,
`omitted_pattern_leaves_existing_value`) — **wait, do not expect this yet**: the three
tests `test_import_aliases_full_replace`, `test_import_aliases_chest_alias_defaults_to_enabled`,
and `test_import_aliases_chest_alias_can_be_disabled` will now FAIL with `400`, because they
submit `canonical_type` literals (`"Эпический отряд"`, `"Epic X"`, `"Y"`) that aren't yet
registered as known English IDs anywhere. This is expected — Task 2 fixes exactly these
three tests. Confirm only the 4 new tests plus the 3 untouched ones
(`no_token`, `wrong_token`, `unknown_slug`, `empty_lists_clear_existing`,
`sets_pattern_and_language`, `omitted_pattern_leaves_existing_value`) pass; the 3 named
above are allowed to fail at this checkpoint.

- [ ] **Step 5: Commit**

```bash
cd C:\BattleBot
git add server/chest_aliases.py server/tests/test_chest_aliases.py
git commit -m "feat(chests): resolve chest-alias canonical_type from clan's native language

Admin Sheet 'Chest Aliases' column B now holds clean native-language text
instead of a hand-looked-up English ID; the import endpoint resolves it
via the global Localizations table (or a literal-English fallback) and
rejects the whole sync with a 400 naming every unresolved row otherwise."
```

---

### Task 2: Fix pre-existing tests broken by the new validation

**Files:**
- Modify: `server/tests/test_chest_aliases.py`

**Interfaces:**
- Consumes: `models.ChestTypeCatalog` (already imported in Task 1).
- Produces: nothing new — this task only adds fixture rows so three existing tests keep
  their original pass-through assertions under the new validation.

These three tests use arbitrary placeholder strings as `canonical_type`
(`"Эпический отряд"`, `"Epic X"`, `"Y"`) to test full-replace/enabled-flag mechanics
unrelated to translation. Under the new validation those strings are now unresolved unless
registered as a known English ID. Register them via a `ChestTypeCatalog` fixture row so the
literal-fallback path (Task 1, Step 3) accepts them unchanged — this preserves every
existing assertion in these tests untouched.

- [ ] **Step 1: Confirm current failures**

Run: `cd C:\BattleBot\server && python -m pytest tests/test_chest_aliases.py -v -k "full_replace or defaults_to_enabled or can_be_disabled"`

Expected: all 3 FAIL with `400` (per Task 1 Step 4's note).

- [ ] **Step 2: Add fixture rows**

In `server/tests/test_chest_aliases.py`, find `test_import_aliases_full_replace` and change:

```python
    collector = await _create_collector(db_session)
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="OldRawType",
                                  canonical_type="OldCanonType"))
    await db_session.commit()
    slug = collector.slug
```

to:

```python
    collector = await _create_collector(db_session)
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="OldRawType",
                                  canonical_type="OldCanonType"))
    db_session.add(ChestTypeCatalog(canonical_type="Эпический отряд", pattern="T9", points=1))
    await db_session.commit()
    slug = collector.slug
```

Find `test_import_aliases_chest_alias_defaults_to_enabled` and change:

```python
    collector = await _create_collector(db_session)
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "X", "canonical_type": "Epic X"}]},
```

to:

```python
    collector = await _create_collector(db_session)
    db_session.add(ChestTypeCatalog(canonical_type="Epic X", pattern="T9", points=1))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "X", "canonical_type": "Epic X"}]},
```

Find `test_import_aliases_chest_alias_can_be_disabled` and change:

```python
    collector = await _create_collector(db_session)
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Y", "canonical_type": "Y", "enabled": False}]},
```

to:

```python
    collector = await _create_collector(db_session)
    db_session.add(ChestTypeCatalog(canonical_type="Y", pattern="T9", points=1))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Y", "canonical_type": "Y", "enabled": False}]},
```

- [ ] **Step 3: Run the full test file to verify everything passes**

Run: `cd C:\BattleBot\server && python -m pytest tests/test_chest_aliases.py -v`

Expected: all 13 tests PASS (6 pre-existing untouched + 3 fixed + 4 new from Task 1).

- [ ] **Step 4: Run the full server test suite to check for regressions elsewhere**

Run: `cd C:\BattleBot\server && python -m pytest -v`

Expected: all tests PASS, including `test_chests.py` and `test_chest_catalog.py` (unaffected
by this change — they don't call `/aliases/import`).

- [ ] **Step 5: Commit**

```bash
cd C:\BattleBot
git add server/tests/test_chest_aliases.py
git commit -m "test(chests): seed known-English fixtures for pre-existing alias tests

These tests use placeholder canonical_type strings unrelated to translation
(full-replace/enabled-flag mechanics); register them as known English IDs
so the new resolution validation accepts them unchanged."
```

---

## After implementation

Deploy to GCP per the existing chests deploy flow (`server/` → `git pull` + `alembic
upgrade head` if needed — no migration in this plan, so just `git pull` + `systemctl
restart totalhunter`), then the owner fills in `Yogwai → Ёкай` in the Localizations Sheet
row 19 (already noted in the design spec) and runs `sync_catalog_to_db.py` +
`sync_admin_sheet_to_db.py` to verify the real `Ёкай` chest resolves end-to-end.
