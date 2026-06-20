# Сундуки — GET /summary/{slug} + Google Sheets export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public `GET /api/v1/chests/summary/{slug}` endpoint that returns an
aggregated player × chest-type table for a chest collector, and a local script that
exports that data into a Google Sheet, fully overwriting it on each run.

**Architecture:** One new read-only route in `server/chests.py` does a single
`GROUP BY sender_canonical, chest_type_canonical` SQL query against the existing `Chest`
table, pivots the rows in Python into `{chest_types, players, totals}`, and returns it as
JSON. A standalone root-level script (`export_chests_to_sheet.py`, no server dependency)
calls that endpoint over HTTPS and writes the result into a Google Sheet via the Sheets
API, reusing the existing `service_account.json` service-account credentials already used
by `sync_to_gemini.py`.

**Tech Stack:** FastAPI, SQLAlchemy async (`server/chests.py`, `server/models.py`),
pytest + httpx (`server/tests/test_chests.py`), `google-api-python-client` +
`google-auth` (already installed locally, see `sync_to_gemini.py` pattern) for the export
script, `requests` for the HTTP call to the API.

## Global Constraints

- Source spec: `docs/superpowers/specs/2026-06-20-chests-summary-export-design.md`.
- The `summary` endpoint is public (no `hwid`/Bearer auth) — the unpredictable `slug` itself
  is the access control, per `models.py:382`. Unknown slug → `404`.
- Aggregation happens in the SQL query (`GROUP BY`), not by pulling all rows and counting
  in Python.
- `chests` is read as-is — no date filtering. Per project memory, `chests` is designed to
  hold only the active sprint going forward (`chest_history` split is a separate, not-yet-
  built subsystem); this endpoint reads the table exactly as it exists today.
- The export script lives in the repo root (matches `sync_to_gemini.py` placement), is run
  manually and locally by the project owner, and is **not** part of `server/` (no GCP
  deploy, no `server/requirements.txt` change).
- Each run of the export script fully overwrites the target Sheet (`clear()` then
  `update()`) — no appending, no dedup logic needed.
- Test additions go in the existing `server/tests/test_chests.py` file (don't create a
  parallel test file).

---

### Task 1: `GET /api/v1/chests/summary/{slug}` endpoint

**Files:**
- Modify: `server/chests.py` (add route + helper functions, after `import_chests`)
- Test: `server/tests/test_chests.py` (add tests at the end of the file)

**Interfaces:**
- Consumes: `ChestCollector` (`id`, `slug`, `kingdom`, `clan`), `Chest`
  (`collector_id`, `sender_canonical`, `chest_type_canonical`) from `server/models.py`
  (unchanged, already exist).
- Produces: `GET /api/v1/chests/summary/{slug}` → `200` with body
  `{"kingdom": str, "clan": str, "chest_types": list[str],
  "players": [{"name": str, "counts": dict[str, int], "total": int}],
  "totals": dict[str, int]}` (the `totals` dict has one key per chest type plus
  `"grand_total"`), sorted by `players[i]["total"]` descending. `404` with
  `{"detail": "Collector not found"}` for an unknown slug.

- [ ] **Step 1: Write the failing tests**

  Add to `server/tests/test_chests.py` (uses the existing `_create_user` / `_payload`
  helpers already in the file, and the existing `db_session` fixture):

  ```python
  @pytest.mark.asyncio
  async def test_summary_unknown_slug_returns_404():
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
          resp = await client.get("/api/v1/chests/summary/does-not-exist")
      assert resp.status_code == 404


  @pytest.mark.asyncio
  async def test_summary_aggregates_players_and_chest_types(db_session):
      user = await _create_user(db_session, "summarytest00a")
      await db_session.commit()
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
          import_resp = await client.post("/api/v1/chests/import", json=_payload(
              user.hwid, kingdom="K9", clan="ClanSummary",
              items=[
                  {"chest_type": "Сундук Эпического Монстра", "sender": "Игрок1",
                   "timestamp": "2026-06-18T11:00:00"},
                  {"chest_type": "Сундук Эпического Монстра", "sender": "Игрок1",
                   "timestamp": "2026-06-18T11:05:00"},
                  {"chest_type": "Малый Сундук", "sender": "Игрок1",
                   "timestamp": "2026-06-18T11:10:00"},
                  {"chest_type": "Сундук Эпического Монстра", "sender": "Игрок2",
                   "timestamp": "2026-06-18T11:15:00"},
              ],
          ))
          assert import_resp.status_code == 200
          slug = import_resp.json()["collector_slug"]

          resp = await client.get(f"/api/v1/chests/summary/{slug}")
      assert resp.status_code == 200
      body = resp.json()
      assert body["kingdom"] == "K9"
      assert body["clan"] == "ClanSummary"
      assert sorted(body["chest_types"]) == ["Малый Сундук", "Сундук Эпического Монстра"]

      players_by_name = {p["name"]: p for p in body["players"]}
      assert players_by_name["Игрок1"]["counts"]["Сундук Эпического Монстра"] == 2
      assert players_by_name["Игрок1"]["counts"]["Малый Сундук"] == 1
      assert players_by_name["Игрок1"]["total"] == 3
      assert players_by_name["Игрок2"]["counts"]["Сундук Эпического Монстра"] == 1
      assert players_by_name["Игрок2"]["total"] == 1

      # sorted by total descending
      assert body["players"][0]["name"] == "Игрок1"

      assert body["totals"]["Сундук Эпического Монстра"] == 3
      assert body["totals"]["Малый Сундук"] == 1
      assert body["totals"]["grand_total"] == 4


  @pytest.mark.asyncio
  async def test_summary_empty_collector_returns_empty_lists(db_session):
      user = await _create_user(db_session, "emptysummary0a")
      await db_session.commit()
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
          import_resp = await client.post("/api/v1/chests/import", json=_payload(
              user.hwid, kingdom="K10", clan="EmptyClan",
              items=[{"chest_type": "Малый Сундук", "sender": "Соло",
                      "timestamp": "2026-06-18T12:00:00"}],
          ))
          slug = import_resp.json()["collector_slug"]
          # re-send the same item to confirm idempotency doesn't break the empty-delta path,
          # then check a *different*, genuinely empty collector via direct DB insert instead:
          resp = await client.get(f"/api/v1/chests/summary/{slug}")
      assert resp.status_code == 200
      body = resp.json()
      assert body["chest_types"] == ["Малый Сундук"]
      assert body["players"][0]["total"] == 1
  ```

  Note: the third test exercises the "collector exists but has rows" path again rather
  than a literally zero-row collector, because creating a `ChestCollector` row with zero
  `Chest` rows requires reaching into the DB directly. Add one more test for the true
  zero-row case using direct model creation:

  ```python
  @pytest.mark.asyncio
  async def test_summary_collector_with_zero_chests_returns_empty_lists(db_session):
      import secrets as _secrets
      user = await _create_user(db_session, "zerochests000a")
      collector = ChestCollector(kingdom="K11", clan="ZeroClan", user_id=user.id,
                                 slug=_secrets.token_urlsafe(16))
      db_session.add(collector)
      await db_session.commit()
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
          resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
      assert resp.status_code == 200
      body = resp.json()
      assert body["chest_types"] == []
      assert body["players"] == []
      assert body["totals"] == {"grand_total": 0}
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run: `cd server && pytest tests/test_chests.py -k summary -v`
  Expected: FAIL with `404` for all of them (no route exists yet — FastAPI returns 404 for
  unmatched routes too, so check the failure is "route not found" by confirming the test
  for `test_summary_collector_with_zero_chests_returns_empty_lists` fails on
  `body["chest_types"] == []` with a `KeyError`/`JSONDecodeError`, not a real 200).

- [ ] **Step 3: Implement the endpoint**

  In `server/chests.py`, add `func` to the existing `sqlalchemy` import line:

  ```python
  from sqlalchemy import func, select, update
  ```

  Then append after `import_chests`:

  ```python
  def _pivot_summary(kingdom: str, clan: str, rows) -> dict:
      """rows: iterable of (sender_canonical, chest_type_canonical, count)."""
      chest_types: list[str] = []
      seen_types = set()
      per_player: dict[str, dict[str, int]] = {}
      totals: dict[str, int] = {}
      grand_total = 0

      for sender, chest_type, count in rows:
          if chest_type not in seen_types:
              seen_types.add(chest_type)
              chest_types.append(chest_type)
          per_player.setdefault(sender, {})[chest_type] = count
          totals[chest_type] = totals.get(chest_type, 0) + count
          grand_total += count

      players = [
          {"name": name, "counts": counts, "total": sum(counts.values())}
          for name, counts in per_player.items()
      ]
      players.sort(key=lambda p: p["total"], reverse=True)
      totals["grand_total"] = grand_total

      return {
          "kingdom": kingdom,
          "clan": clan,
          "chest_types": chest_types,
          "players": players,
          "totals": totals,
      }


  @router.get("/summary/{slug}")
  async def get_chest_summary(slug: str, db: AsyncSession = Depends(get_db)):
      collector = (await db.execute(
          select(ChestCollector).where(ChestCollector.slug == slug)
      )).scalar_one_or_none()
      if not collector:
          raise HTTPException(status_code=404, detail="Collector not found")

      rows = (await db.execute(
          select(Chest.sender_canonical, Chest.chest_type_canonical, func.count())
          .where(Chest.collector_id == collector.id)
          .group_by(Chest.sender_canonical, Chest.chest_type_canonical)
      )).all()

      return _pivot_summary(collector.kingdom, collector.clan, rows)
  ```

  Add `ChestCollector` import already present (`from models import Chest, ChestCollector, ...`
  — already imported, no change needed there).

- [ ] **Step 4: Run tests to verify they pass**

  Run: `cd server && pytest tests/test_chests.py -v`
  Expected: PASS, all tests in the file (existing + new) green.

- [ ] **Step 5: Commit**

  ```bash
  git add server/chests.py server/tests/test_chests.py
  git commit -m "feat(chests): add public GET /summary/{slug} aggregation endpoint"
  ```

---

### Task 2: Deploy to GCP

**Files:** none (deploy-only task, no local file changes)

**Interfaces:**
- Consumes: Task 1's committed and pushed code.
- Produces: live `GET https://api.total-hunter.com/api/v1/chests/summary/{slug}` endpoint,
  required by Task 3's script.

- [ ] **Step 1: Push to main**

  ```bash
  git push origin main
  ```

- [ ] **Step 2: Deploy on GCP**

  Per `CLAUDE.md` section "Карта деплоя" — run on the GCP box:

  ```bash
  cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter
  ```

  No new dependencies and no migration in this change (no schema change — read-only
  endpoint over existing tables), so no `alembic upgrade head` is needed here.

- [ ] **Step 3: Verify it's live**

  Pick an existing test/staging slug or use one created during manual testing, then:

  ```bash
  curl -s https://api.total-hunter.com/api/v1/chests/summary/<a-real-slug> | head -c 500
  ```

  Expected: a JSON body with `kingdom`/`clan`/`chest_types`/`players`/`totals`, not a 502/404.

---

### Task 3: `export_chests_to_sheet.py` — local export script

**Files:**
- Create: `export_chests_to_sheet.py` (repo root)

**Interfaces:**
- Consumes: `GET https://api.total-hunter.com/api/v1/chests/summary/{SLUG}` from Task 1/2
  (exact response shape: `{"kingdom", "clan", "chest_types", "players": [{"name", "counts",
  "total"}], "totals"}`), and `service_account.json` (already exists at
  `C:\BattleBot\service_account.json`, same file `sync_to_gemini.py` uses).
- Produces: a fully-overwritten tab in the target Google Sheet — no other task depends on
  this script's internals.

- [ ] **Step 1: Write the script**

  ```python
  """
  export_chests_to_sheet.py — pulls the chest summary for one collector from the live API
  and writes it into a Google Sheet, fully overwriting the target tab on every run.

  Run manually: python export_chests_to_sheet.py
  """
  import requests
  from google.oauth2.service_account import Credentials
  from googleapiclient.discovery import build

  API_BASE = "https://api.total-hunter.com"
  SLUG = "PUT_COLLECTOR_SLUG_HERE"
  SHEET_ID = "PUT_GOOGLE_SHEET_ID_HERE"
  SHEET_RANGE = "Sheet1"

  SA_PATH = r"C:\BattleBot\service_account.json"
  SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


  def fetch_summary(slug: str) -> dict:
      resp = requests.get(f"{API_BASE}/api/v1/chests/summary/{slug}", timeout=15)
      resp.raise_for_status()
      return resp.json()


  def build_rows(summary: dict) -> list[list]:
      header = ["Игрок"] + summary["chest_types"] + ["Итого"]
      rows = [header]
      for player in summary["players"]:
          row = [player["name"]]
          row += [player["counts"].get(t, 0) for t in summary["chest_types"]]
          row.append(player["total"])
          rows.append(row)
      totals_row = ["ВСЕГО"]
      totals_row += [summary["totals"].get(t, 0) for t in summary["chest_types"]]
      totals_row.append(summary["totals"].get("grand_total", 0))
      rows.append(totals_row)
      return rows


  def build_sheets_service():
      creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
      return build("sheets", "v4", credentials=creds)


  def write_to_sheet(service, rows: list[list]):
      sheets = service.spreadsheets().values()
      sheets.clear(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
      sheets.update(
          spreadsheetId=SHEET_ID,
          range=f"{SHEET_RANGE}!A1",
          valueInputOption="RAW",
          body={"values": rows},
      ).execute()


  if __name__ == "__main__":
      print(f"=== Экспорт сундуков {SLUG} в Google Sheet ===\n")
      summary = fetch_summary(SLUG)
      rows = build_rows(summary)
      service = build_sheets_service()
      write_to_sheet(service, rows)
      print(f"  Готово: {len(rows) - 2} игроков, "
            f"{summary['totals'].get('grand_total', 0)} сундуков всего")
      print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}")
  ```

- [ ] **Step 2: Manual verification (owner action required — not automatable)**

  This step cannot be completed by an automated worker: it requires the project owner to
  create a Google Sheet, share it with the service account's email (same email already
  used in `share_docs_with_sa.py` — `gemini-sync@digital-arcade-274010.iam.gserviceaccount.com`,
  with **Editor** access, not just the `Viewer` access used for the Docs case), and supply
  a real `SLUG` from the production database. Report back to the owner:

  > "Script written to `export_chests_to_sheet.py`. Before it can run, I need: (1) a Google
  > Sheet ID, shared as Editor with `gemini-sync@digital-arcade-274010.iam.gserviceaccount.com`,
  > and (2) a real collector slug from `chest_collectors.slug` to fill in `SLUG`. Once I
  > have both I'll fill them into the script and do a live run to confirm the sheet
  > populates correctly."

  Do not mark this task complete until the owner has provided both values and a live run
  has been confirmed to write real data into the real sheet.

- [ ] **Step 3: Commit**

  ```bash
  git add export_chests_to_sheet.py
  git commit -m "feat(chests): add local Google Sheets export script for chest summaries"
  ```

  (Commit the script with its placeholder `SLUG`/`SHEET_ID` constants — do not commit the
  real values if they differ between owner runs; if the owner wants a fixed default
  collector baked in, ask before committing real production identifiers into git history.)
