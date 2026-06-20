# Chest Aliases Admin Sheet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the project owner fix OCR-garbled player names and chest-type names by
editing two Google Sheet tabs, syncing them to the server, and have `GET
/api/v1/chests/summary/{slug}` apply those corrections retroactively to the entire
existing history — no re-import needed.

**Architecture:** A new admin-only endpoint (`POST /api/v1/chests/aliases/import`, Bearer
`$ADMIN_TOKEN`, same auth pattern as `server/clan.py`) does a full replace of a
collector's `PlayerAlias`/`ChestTypeAlias` rows. The existing `GET
/api/v1/chests/summary/{slug}` (`server/chests.py`) switches from reading the
already-baked `chests.sender_canonical`/`chest_type_canonical` columns to a `LEFT JOIN`
against the alias tables with `COALESCE`, computed fresh on every request — so editing an
alias instantly corrects all historical rows. A local script
(`sync_admin_sheet_to_db.py`) reads two new tabs ("Player Aliases", "Chest Aliases") from
the already-existing Google Sheet and POSTs them to the new endpoint.

**Tech Stack:** FastAPI, SQLAlchemy async (`server/chest_aliases.py` new,
`server/chests.py` modified), pytest + httpx (`server/tests/test_chest_aliases.py` new,
`server/tests/test_chests.py` modified), `google-api-python-client` + `requests` for the
sync script (same pattern as `export_chests_to_sheet.py`).

## Global Constraints

- Source spec: `docs/superpowers/specs/2026-06-20-chest-aliases-admin-sheet-design.md`.
- Auth for the new endpoint is `Authorization: Bearer $ADMIN_TOKEN`, identical pattern to
  `server/clan.py:_require_auth` (`HTTPBearer` + `os.getenv("ADMIN_TOKEN", "")` compared
  with `==`, `403` on mismatch/empty).
- Collector is identified by `collector_slug` in the request body, not
  `hwid`/`kingdom`/`clan`.
- Each sync is a **full replace**: existing `PlayerAlias`/`ChestTypeAlias` rows for that
  collector are deleted, then the payload's rows are inserted. No incremental upsert, no
  delete-tracking.
- `import_chests` (`server/chests.py`) is **not modified** — it keeps writing
  `chest_type_canonical`/`sender_canonical` exactly as today; those columns simply become
  unused by the summary endpoint after this plan.
- The alias JOIN in `summary` must keep aggregation in SQL (`GROUP BY` with the
  `COALESCE` expressions), not a Python-side dict lookup — same constraint as the
  original summary endpoint.
- The new admin Sheet tabs live in the existing Google Sheet
  (`1EjUF5TIj3gAD4kv-XYYoQMKTHqOVn7OySYumAtNukug`), reusing the same
  `C:\BattleBot\service_account.json` credentials already used by
  `export_chests_to_sheet.py`.
- Test commands in this plan require both `JWT_SECRET_KEY` and `ADMIN_TOKEN` set as env
  vars before importing the app (matches the project's existing test convention — both
  routers read their tokens at module import time).

---

### Task 1: `POST /api/v1/chests/aliases/import` admin endpoint

**Files:**
- Create: `server/chest_aliases.py`
- Modify: `server/main.py` (add import + `include_router`)
- Test: `server/tests/test_chest_aliases.py`

**Interfaces:**
- Consumes: `ChestCollector`, `PlayerAlias`, `ChestTypeAlias` from `server/models.py`
  (unchanged, already exist — `PlayerAlias` has `collector_id`, `raw_name`,
  `canonical_name`; `ChestTypeAlias` has `collector_id`, `raw_type`, `canonical_type`).
  `get_db` from `server/database.py`.
- Produces: `POST /api/v1/chests/aliases/import` → `200`
  `{"ok": true, "player_aliases": <int>, "chest_aliases": <int>}` on success; `403` if the
  `Authorization: Bearer` header is missing or wrong; `404`
  `{"detail": "Collector not found"}` for an unknown `collector_slug`. This is the only
  thing Task 3's sync script depends on.

- [ ] **Step 1: Write the failing tests**

  Create `server/tests/test_chest_aliases.py`:

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
                                    canonical_type="OldCanonType"))
      await db_session.commit()
      slug = collector.slug

      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
          resp = await client.post(
              "/api/v1/chests/aliases/import",
              json={
                  "collector_slug": slug,
                  "player_aliases": [{"raw_name": "Machet", "canonical_name": "MACHETE"}],
                  "chest_aliases": [{"raw_type": "Эпический отр", "canonical_type": "Эпический отряд"}],
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
      assert type_rows[0].canonical_type == "Эпический отряд"


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
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run (from `server/`):
  `JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chest_aliases.py -v`
  Expected: FAIL — `ModuleNotFoundError`/404s, since `server/chest_aliases.py` doesn't
  exist and the route isn't mounted.

- [ ] **Step 3: Implement the endpoint**

  Create `server/chest_aliases.py`:

  ```python
  """
  chest_aliases.py — admin endpoint for syncing alias dictionaries from the
  "Admin Sheet" (Google Sheets) into player_aliases / chest_type_aliases.

  Auth: Bearer $ADMIN_TOKEN (same pattern as clan.py) — this is an owner/admin action,
  not something the bot calls on a user's behalf.

  Each sync is a full replace for the named collector: existing rows are deleted, then
  the payload's rows are inserted. The Sheet is the source of truth.
  """
  import os
  from typing import List

  from fastapi import APIRouter, Depends, HTTPException, status
  from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
  from pydantic import BaseModel
  from sqlalchemy import delete, select
  from sqlalchemy.ext.asyncio import AsyncSession

  from database import get_db
  from models import ChestCollector, ChestTypeAlias, PlayerAlias

  router = APIRouter(prefix="/api/v1/chests", tags=["chests"])

  _bearer = HTTPBearer()
  _ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


  def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
      if not _ADMIN_TOKEN or creds.credentials != _ADMIN_TOKEN:
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


  @router.post("/aliases/import", dependencies=[Depends(_require_auth)])
  async def import_aliases(payload: AliasImportPayload, db: AsyncSession = Depends(get_db)):
      collector = (await db.execute(
          select(ChestCollector).where(ChestCollector.slug == payload.collector_slug)
      )).scalar_one_or_none()
      if not collector:
          raise HTTPException(status_code=404, detail="Collector not found")
      collector_id = collector.id

      await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector_id))
      await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector_id))

      for item in payload.player_aliases:
          db.add(PlayerAlias(collector_id=collector_id, raw_name=item.raw_name,
                             canonical_name=item.canonical_name))
      for item in payload.chest_aliases:
          db.add(ChestTypeAlias(collector_id=collector_id, raw_type=item.raw_type,
                                canonical_type=item.canonical_type))

      await db.commit()
      return {
          "ok": True,
          "player_aliases": len(payload.player_aliases),
          "chest_aliases": len(payload.chest_aliases),
      }
  ```

  In `server/main.py`, find this line:
  ```python
  from chests import router as chests_router
  ```
  Add directly after it:
  ```python
  from chest_aliases import router as chest_aliases_router
  ```
  Find this line:
  ```python
  app.include_router(chests_router)
  ```
  Add directly after it:
  ```python
  app.include_router(chest_aliases_router)
  ```

- [ ] **Step 4: Run tests to verify they pass**

  Run: `JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chest_aliases.py -v`
  Expected: PASS, all 5 tests green.

- [ ] **Step 5: Commit**

  ```bash
  git add server/chest_aliases.py server/main.py server/tests/test_chest_aliases.py
  git commit -m "feat(chests): add admin endpoint for full-replace alias sync"
  ```

---

### Task 2: `GET /summary/{slug}` applies aliases on read (retroactive correction)

**Files:**
- Modify: `server/chests.py:230-244` (the `get_chest_summary` route; `_pivot_summary` at
  `server/chests.py:198-227` is unchanged — it already accepts arbitrary
  `(name, type, count)` tuples)
- Test: `server/tests/test_chests.py` (add at the end)

**Interfaces:**
- Consumes: `PlayerAlias`, `ChestTypeAlias` (already imported in `server/chests.py:24`,
  no import line changes needed there), Task 1's `PlayerAlias`/`ChestTypeAlias` rows (no
  direct dependency — this task reads the same tables Task 1 writes, but is testable
  independently by inserting alias rows directly via `db_session`).
- Produces: no change to `GET /summary/{slug}`'s response shape — same
  `{kingdom, clan, chest_types, players, totals}` as before. Only the *values* change
  when aliases exist.

- [ ] **Step 1: Write the failing test**

  Add to `server/tests/test_chests.py` (reuses existing `_create_user`/`_payload` helpers
  already in the file):

  ```python
  @pytest.mark.asyncio
  async def test_summary_applies_alias_added_after_import_without_reimport(db_session):
      from models import PlayerAlias, ChestTypeAlias

      user = await _create_user(db_session, "aliasafterimp0a")
      await db_session.commit()
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
          import_resp = await client.post("/api/v1/chests/import", json=_payload(
              user.hwid, kingdom="K12", clan="AliasClan",
              items=[
                  {"chest_type": "Эпический отр", "sender": "Machet",
                   "timestamp": "2026-06-18T13:00:00"},
                  {"chest_type": "Эпический отр", "sender": "Machet",
                   "timestamp": "2026-06-18T13:05:00"},
              ],
          ))
          assert import_resp.status_code == 200
          slug = import_resp.json()["collector_slug"]

          collector_id = (await db_session.execute(
              select(ChestCollector).where(ChestCollector.slug == slug)
          )).scalar_one().id

          # Alias added AFTER the import already happened — no re-import follows.
          db_session.add(PlayerAlias(collector_id=collector_id, raw_name="Machet",
                                     canonical_name="MACHETE"))
          db_session.add(ChestTypeAlias(collector_id=collector_id, raw_type="Эпический отр",
                                        canonical_type="Эпический отряд"))
          await db_session.commit()

          resp = await client.get(f"/api/v1/chests/summary/{slug}")
      assert resp.status_code == 200
      body = resp.json()
      assert body["chest_types"] == ["Эпический отряд"]
      assert body["players"][0]["name"] == "MACHETE"
      assert body["players"][0]["counts"]["Эпический отряд"] == 2
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chests.py -k alias_added_after -v`
  Expected: FAIL — current query reads `Chest.sender_canonical`/`chest_type_canonical`
  (computed at import time, before the alias existed), so `players[0]["name"]` is
  `"Machet"`, not `"MACHETE"`.

- [ ] **Step 3: Implement the read-time join**

  In `server/chests.py`, change the import line at the top:
  ```python
  from sqlalchemy import func, select, update
  ```
  to:
  ```python
  from sqlalchemy import and_, func, select, update
  ```

  Then replace `get_chest_summary` (currently `server/chests.py:230-244`):
  ```python
  @router.get("/summary/{slug}")
  async def get_chest_summary(slug: str, db: AsyncSession = Depends(get_db)):
      collector = (await db.execute(
          select(ChestCollector).where(ChestCollector.slug == slug)
      )).scalar_one_or_none()
      if not collector:
          raise HTTPException(status_code=404, detail="Collector not found")

      sender_expr = func.coalesce(PlayerAlias.canonical_name, Chest.sender_raw)
      chest_type_expr = func.coalesce(ChestTypeAlias.canonical_type, Chest.chest_type_raw)

      rows = (await db.execute(
          select(sender_expr, chest_type_expr, func.count())
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
          .where(Chest.collector_id == collector.id)
          .group_by(sender_expr, chest_type_expr)
      )).all()

      return _pivot_summary(collector.kingdom, collector.clan, rows)
  ```

  `PlayerAlias` and `ChestTypeAlias` are already imported at `server/chests.py:24` (used by
  `_load_aliases` for the import path) — no new import needed beyond the `and_` added
  above.

- [ ] **Step 4: Run tests to verify they pass**

  Run: `JWT_SECRET_KEY=test-secret ADMIN_TOKEN=test-admin python -m pytest tests/test_chests.py -v`
  Expected: PASS, all tests in the file (existing + new) green.

- [ ] **Step 5: Commit**

  ```bash
  git add server/chests.py server/tests/test_chests.py
  git commit -m "feat(chests): apply player/chest-type aliases on read, not just at import"
  ```

---

### Task 3: `sync_admin_sheet_to_db.py` + live verification

**Files:**
- Create: `sync_admin_sheet_to_db.py` (repo root)

**Interfaces:**
- Consumes: `POST /api/v1/chests/aliases/import` from Task 1 (exact payload shape:
  `{"collector_slug": str, "player_aliases": [{"raw_name", "canonical_name"}],
  "chest_aliases": [{"raw_type", "canonical_type"}]}`, `Authorization: Bearer
  $ADMIN_TOKEN` header), and two Google Sheet tabs ("Player Aliases", "Chest Aliases")
  read via `service_account.json` (same file `export_chests_to_sheet.py` already uses,
  same `spreadsheets` scope — read access, no new scope needed since the service account
  already has Editor on this Sheet from the prior plan's setup).
- Produces: nothing further depends on this script's internals — it's the last task.

- [ ] **Step 1: Write the script**

  ```python
  """
  sync_admin_sheet_to_db.py — reads the "Player Aliases" and "Chest Aliases" tabs from
  the Admin Sheet and pushes them to the server as a full-replace sync for one collector.

  Run manually: ADMIN_TOKEN=... python sync_admin_sheet_to_db.py
  """
  import os
  import requests
  from google.oauth2.service_account import Credentials
  from googleapiclient.discovery import build

  API_BASE = "https://api.total-hunter.com"
  SLUG = "m00bqgjcl1xqUHRDvEa8bQ"
  SHEET_ID = "1EjUF5TIj3gAD4kv-XYYoQMKTHqOVn7OySYumAtNukug"

  SA_PATH = r"C:\BattleBot\service_account.json"
  SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


  def build_sheets_service():
      creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
      return build("sheets", "v4", credentials=creds)


  def read_tab_rows(service, tab_name: str) -> list[list]:
      result = service.spreadsheets().values().get(
          spreadsheetId=SHEET_ID, range=f"{tab_name}!A2:B",
      ).execute()
      return result.get("values", [])


  def build_payload(service) -> dict:
      player_rows = read_tab_rows(service, "Player Aliases")
      chest_rows = read_tab_rows(service, "Chest Aliases")
      return {
          "collector_slug": SLUG,
          "player_aliases": [
              {"raw_name": row[0], "canonical_name": row[1]}
              for row in player_rows if len(row) >= 2 and row[0] and row[1]
          ],
          "chest_aliases": [
              {"raw_type": row[0], "canonical_type": row[1]}
              for row in chest_rows if len(row) >= 2 and row[0] and row[1]
          ],
      }


  def push_to_server(payload: dict, admin_token: str) -> dict:
      resp = requests.post(
          f"{API_BASE}/api/v1/chests/aliases/import",
          json=payload,
          headers={"Authorization": f"Bearer {admin_token}"},
          timeout=15,
      )
      resp.raise_for_status()
      return resp.json()


  if __name__ == "__main__":
      admin_token = os.environ["ADMIN_TOKEN"]
      print(f"=== Синхронизация алиасов {SLUG} из Admin Sheet ===\n")
      service = build_sheets_service()
      payload = build_payload(service)
      result = push_to_server(payload, admin_token)
      print(f"  Игроков: {result['player_aliases']}, типов сундуков: {result['chest_aliases']}")
  ```

- [ ] **Step 2: Add the two tabs to the existing Sheet and verify end-to-end**

  This step is doable now without owner action, because the service account already has
  Editor access to Sheet `1EjUF5TIj3gAD4kv-XYYoQMKTHqOVn7OySYumAtNukug` (granted while
  building `export_chests_to_sheet.py`). Run this one-off snippet to create the two tabs
  with header rows (adjust the path to wherever you run it from):

  ```python
  from google.oauth2.service_account import Credentials
  from googleapiclient.discovery import build

  creds = Credentials.from_service_account_file(
      r"C:\BattleBot\service_account.json",
      scopes=["https://www.googleapis.com/auth/spreadsheets"],
  )
  service = build("sheets", "v4", credentials=creds)
  sheet_id = "1EjUF5TIj3gAD4kv-XYYoQMKTHqOVn7OySYumAtNukug"

  service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={
      "requests": [
          {"addSheet": {"properties": {"title": "Player Aliases"}}},
          {"addSheet": {"properties": {"title": "Chest Aliases"}}},
      ]
  }).execute()

  service.spreadsheets().values().update(
      spreadsheetId=sheet_id, range="Player Aliases!A1",
      valueInputOption="RAW",
      body={"values": [["Raw Name", "Canonical Name"], ["Machet", "MACHETE"]]},
  ).execute()
  service.spreadsheets().values().update(
      spreadsheetId=sheet_id, range="Chest Aliases!A1",
      valueInputOption="RAW",
      body={"values": [["Raw Type", "Canonical Type"],
                       ["Эпический отр", "Эпический отряд"]]},
  ).execute()
  ```

  Then run the real script against production and confirm it reports the row it just
  wrote:

  ```bash
  ADMIN_TOKEN=<the real production ADMIN_TOKEN from .claude/settings.local.json> python sync_admin_sheet_to_db.py
  ```
  Expected output: `Игроков: 1, типов сундуков: 1`.

  Then confirm the live `summary` endpoint reflects it without any re-import:
  ```bash
  curl -s https://api.total-hunter.com/api/v1/chests/summary/m00bqgjcl1xqUHRDvEa8bQ | python -c "import json,sys; d=json.load(sys.stdin); print([p for p in d['players'] if p['name']=='MACHETE'])"
  ```
  Expected: a non-empty list (the row that used to show as raw OCR text under whatever
  name contained "Machet" now shows merged into `"MACHETE"`).

  If no row in the live data actually has raw sender "Machet" or raw chest type "Эпический
  отр", this verification step only proves the sync pipeline works, not that real data
  changed — that's fine, it's still a true end-to-end check of Task 1+2+3 wired together.

- [ ] **Step 3: Commit**

  ```bash
  git add sync_admin_sheet_to_db.py
  git commit -m "feat(chests): add local sync script for alias admin Sheet"
  ```
