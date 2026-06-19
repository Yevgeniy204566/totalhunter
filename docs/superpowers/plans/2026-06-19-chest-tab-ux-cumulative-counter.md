# Сундуки — UX-фиксы вкладки + накопительный счётчик невыгруженного Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three UX problems in the СУНДУКИ (Chests) tab: unbounded type-list pushing the
buttons off-screen, wrong button order, and a session-only counter that doesn't reflect the
real unsynced backlog after stop/restart.

**Architecture:** A single new DB query function (`get_unsynced_counts`) becomes the one
source of truth for "how many chests are waiting to be uploaded", read by three call sites
in `main.py` (collection start, live updates, post-stop) and re-read as `{}` after a
successful upload. The chest type list moves from an unbounded `CTkFrame` to a
fixed-height `CTkScrollableFrame`.

**Tech Stack:** Python 3.13, sqlite3 (stdlib), customtkinter, pytest.

## Global Constraints

- No new tables/migrations — `local_chests` (SQLite, `chest_buffer.db`) already has
  `chest_type` + `is_synced`; this is a query-layer change only.
- `get_unsynced_counts` groups `WHERE is_synced = 0`, ignores `is_synced = 1`.
- Existing tests `test_collect_chests_counts_and_persists` and
  `test_collect_chests_stops_immediately_when_flag_already_set` must stay green unmodified.
- Button order target (top to bottom): Kingdom/Clan card → `chest_send_btn` →
  `chest_status_label` → `counts_card` (scrollable list + total) → `chest_start_btn`.
- `chest_counts_frame` becomes a `CTkScrollableFrame` with fixed height `260`.
- Comments in code: WHY only, not WHAT (per project convention).

---

### Task 1: `get_unsynced_counts` — DB-backed counter, source of truth

**Files:**
- Modify: `chest_reader.py` (add function after `get_unsynced`, around line 164)
- Test: `test_chest_reader.py` (add tests after `test_insert_and_get_unsynced`, around line 118)

**Interfaces:**
- Consumes: `chest_reader.init_db(path)` (existing), `chest_reader.insert_chest(conn, chest_type, raw_player_name, timestamp)` (existing), `chest_reader.mark_synced(conn, ids)` (existing).
- Produces: `get_unsynced_counts(conn) -> dict[str, int]` — `{chest_type: count}` for all
  `is_synced = 0` rows. Used by Task 2 (`collect_chests`) and by `main.py` (Task 3).

- [ ] **Step 1: Write the failing tests**

Add to `test_chest_reader.py` (after the existing `test_insert_and_get_unsynced` test, which
ends at line 118):

```python
def test_get_unsynced_counts_groups_by_type(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Игрок1", "2026-06-19T10:00:00")
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Игрок2", "2026-06-19T10:00:05")
    cr.insert_chest(conn, "Редкий склеп 25", "Игрок1", "2026-06-19T10:00:10")
    conn.close()

    conn = cr.init_db(db_path)
    counts = cr.get_unsynced_counts(conn)
    conn.close()

    assert counts == {"Сундук Эпического Монстра": 2, "Редкий склеп 25": 1}


def test_get_unsynced_counts_ignores_synced_rows(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Тип А", "Игрок1", "2026-06-19T10:00:00")
    cr.insert_chest(conn, "Тип Б", "Игрок1", "2026-06-19T10:00:05")
    rows = cr.get_unsynced(conn)
    ids_type_a = [r[0] for r in rows if r[2] == "Тип А"]
    cr.mark_synced(conn, ids_type_a)
    conn.close()

    conn = cr.init_db(db_path)
    counts = cr.get_unsynced_counts(conn)
    conn.close()

    assert counts == {"Тип Б": 1}


def test_get_unsynced_counts_empty_after_full_sync(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Тип А", "Игрок1", "2026-06-19T10:00:00")
    rows = cr.get_unsynced(conn)
    cr.mark_synced(conn, [r[0] for r in rows])
    conn.close()

    conn = cr.init_db(db_path)
    counts = cr.get_unsynced_counts(conn)
    conn.close()

    assert counts == {}
```

Check the top of `test_chest_reader.py` for how the module is imported (it should already do
`import chest_reader as cr` or similar — match the existing import alias used by
`test_insert_and_get_unsynced` so the new tests use the same name).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -k get_unsynced_counts -v`
Expected: FAIL with `AttributeError: module 'chest_reader' has no attribute 'get_unsynced_counts'`

- [ ] **Step 3: Implement `get_unsynced_counts`**

In `chest_reader.py`, add immediately after the existing `get_unsynced` function (after line 164,
before `mark_synced`):

```python
def get_unsynced_counts(conn):
    """{chest_type: count} for is_synced=0 rows — single source of truth for the
    displayed unsynced backlog (live ticker, post-stop display, tab-open display)."""
    cur = conn.execute(
        'SELECT chest_type, COUNT(*) FROM local_chests WHERE is_synced = 0 '
        'GROUP BY chest_type'
    )
    return {chest_type: n for chest_type, n in cur.fetchall()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -k get_unsynced_counts -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest_reader): add get_unsynced_counts as source of truth for backlog display"
```

---

### Task 2: `collect_chests` reads counts from DB, not from a session-local Counter

**Files:**
- Modify: `chest_reader.py:191-229` (`collect_chests`)
- Test: `test_chest_reader.py` (add test after Task 1's tests)

**Interfaces:**
- Consumes: `get_unsynced_counts(conn)` (Task 1).
- Produces: `collect_chests(stop_flag, on_update=None, db_path=DB_PATH) -> {"counts": dict[str,int], "items": list[dict]}` — same signature as before, but `counts` (both the value passed to `on_update` and the final return) now reflects the full DB backlog, not just this call's session. `items` is unchanged (session-only, still used by tests, not read by `main.py`).

- [ ] **Step 1: Write the failing test**

Add to `test_chest_reader.py`, after the Task 1 tests:

```python
def test_collect_chests_counts_are_cumulative_from_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Старый", "2026-06-19T09:00:00")
    conn.close()

    frames = [object(), object()]
    bboxes = [(0, 0, 300, 300), (0, 0, 300, 300)]
    calls = {"n": 0}

    def fake_grab_fullscreen():
        return frames[min(calls["n"], len(frames) - 1)]

    def fake_detect_dialog_bbox(frame):
        return bboxes[min(calls["n"], len(bboxes) - 1)]

    def fake_find_open_button(bbox):
        calls["n"] += 1
        return (10, 10) if calls["n"] <= 1 else None

    def fake_read_top_row(frame):
        return ("Сундук Эпического Монстра", "Новый")

    def fake_click_open_button(pos):
        pass

    monkeypatch.setattr(cr, "grab_fullscreen", fake_grab_fullscreen)
    monkeypatch.setattr(cr, "detect_dialog_bbox", fake_detect_dialog_bbox)
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", fake_click_open_button)

    result = cr.collect_chests(lambda: False, db_path=db_path)

    assert result["counts"] == {"Сундук Эпического Монстра": 2}
```

This test follows the same monkeypatch pattern as the existing
`test_collect_chests_counts_and_persists` (check that test's fakes around line 149-180 of
`test_chest_reader.py` to match the exact function names being patched — copy its fake
style, don't reinvent it).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest test_chest_reader.py -k cumulative_from_db -v`
Expected: FAIL with `assert {'Сундук Эпического Монстра': 1} == {'Сундук Эпического Монстра': 2}`
(it currently only counts the 1 new chest from this session, missing the pre-existing 1)

- [ ] **Step 3: Implement — source counts from DB**

In `chest_reader.py`, modify `collect_chests` (currently lines 191-229):

```python
def collect_chests(stop_flag, on_update=None, db_path=DB_PATH):
    """Reads and opens chests from the top of the «Мой клан → Подарки» list
    until the list is empty (no «Открыть» button found) or stop_flag()
    returns True. Every chest is persisted to SQLite as it's read.
    Returns {'counts': {chest_type: n}, 'items': [{'chest_type', 'sender',
    'timestamp'}, ...]} for this session. 'counts' is sourced from the DB
    (get_unsynced_counts), not a session-local tally, so it always reflects
    the full unsynced backlog — not just what this call found."""
    conn = init_db(db_path)
    items = []
    try:
        while not stop_flag():
            frame = grab_fullscreen()
            bbox = detect_dialog_bbox(frame)
            if bbox is None:
                time.sleep(0.2)
                continue
            dialog = crop_dialog(frame, bbox)
            if dialog.shape[0] < MIN_DIALOG_DIM or dialog.shape[1] < MIN_DIALOG_DIM:
                time.sleep(0.2)
                continue

            pos = find_open_button(bbox)
            if pos is None:
                break

            chest_type, sender = read_top_row(frame)
            timestamp = datetime.datetime.now().isoformat(timespec='seconds')
            insert_chest(conn, chest_type, sender, timestamp)
            items.append({'chest_type': chest_type, 'sender': sender, 'timestamp': timestamp})

            if on_update:
                on_update(get_unsynced_counts(conn))

            click_open_button(pos)

        final_counts = get_unsynced_counts(conn)
    finally:
        conn.close()

    return {'counts': final_counts, 'items': items}
```

Note: when `stop_flag()` is already `True` before the loop runs even once, `final_counts` is
still computed via `get_unsynced_counts(conn)` on the (possibly non-empty, if a prior session
left a backlog) DB — this is correct per the spec, and the existing
`test_collect_chests_stops_immediately_when_flag_already_set` test uses a fresh empty
`tmp_path` DB, so it still gets back `{}` and stays green unmodified.

- [ ] **Step 4: Run all chest_reader tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: all tests pass, including the pre-existing
`test_collect_chests_counts_and_persists` and
`test_collect_chests_stops_immediately_when_flag_already_set` (unmodified, still green).

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest_reader): collect_chests counts come from DB, accumulate across sessions"
```

---

### Task 3: `main.py` — scrollable list, button swap, three display call sites

**Files:**
- Modify: `main.py:3931-3967` (`setup_chest_tab` — button order + scrollable frame)
- Modify: `main.py:2406-2438` (`toggle_chest_bot` — show existing backlog on start)
- Modify: `main.py:2450-2489` (`send_chests_to_server` — clear display after successful upload)

**Interfaces:**
- Consumes: `chest_reader.get_unsynced_counts(conn)` (Task 1), `chest_reader.init_db()` (existing), `self._update_chest_counts_display(counts: dict[str, int])` (existing, unchanged signature).
- Produces: nothing consumed by later tasks — this is the last task in the plan.

This task is GUI-only (customtkinter) and is not covered by automated tests, per the design
spec — verify by running the app after implementing (Step 6).

- [ ] **Step 1: Reorder widgets and make the type list scrollable in `setup_chest_tab`**

In `main.py`, replace the block from the `# ── Старт/Стоп + статус` comment (currently line
3931) through the end of `setup_chest_tab` (currently line 3967) with:

```python
        # ── Отправить на сервер ──────────────────────────────────────────
        self.chest_send_btn = ctk.CTkButton(
            self.tab_chest, text=L["chest_send_btn"],
            height=38, corner_radius=10,
            fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=13, weight="bold"),
            command=self.send_chests_to_server)
        self.chest_send_btn.pack(padx=20, pady=(4, 4), fill="x")
        self._i18n_labels.append((self.chest_send_btn, "chest_send_btn"))

        self.chest_status_label = ctk.CTkLabel(self.tab_chest, text=L["chest_status_ready"],
                                               font=ctk.CTkFont(size=12),
                                               text_color=MD3["on_surface2"])
        self.chest_status_label.pack(pady=(0, 8))
        self._i18n_labels.append((self.chest_status_label, "chest_status_ready"))

        # ── Live-счётчик по типам — фиксированная высота, список скроллится
        # внутри своих границ и не выталкивает СТАРТ ниже ──────────────────
        counts_card = ctk.CTkFrame(self.tab_chest, fg_color=MD3["elevated"],
                                   corner_radius=12, border_width=1,
                                   border_color=MD3["outline"])
        counts_card.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        self.chest_counts_frame = ctk.CTkScrollableFrame(
            counts_card, fg_color="transparent", height=260)
        self.chest_counts_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.chest_total_label = ctk.CTkLabel(counts_card, text=f"{L['chest_total_lb']} 0",
                                              font=ctk.CTkFont(size=13, weight="bold"),
                                              text_color=MD3["value_text"])
        self.chest_total_label.pack(pady=(0, 10))

        # ── Старт/Стоп — внизу, всегда после счётчика ────────────────────
        self.chest_start_btn = ctk.CTkButton(
            self.tab_chest, text=L["chest_start_btn"],
            height=42, corner_radius=10,
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self.toggle_chest_bot)
        self.chest_start_btn.pack(padx=20, pady=(4, 14), fill="x")
        self._i18n_labels.append((self.chest_start_btn, "chest_start_btn"))

        # ── Показать текущий невыгруженный остаток сразу при открытии вкладки,
        # без этого счётчик после перезапуска бота врал бы нулём ───────────
        try:
            import chest_reader
            conn = chest_reader.init_db()
            self._update_chest_counts_display(chest_reader.get_unsynced_counts(conn))
            conn.close()
        except Exception:
            pass
```

This replaces the old order (СТАРТ → статус → counts_card[`CTkFrame`, unbounded] → ОТПРАВИТЬ)
with (ОТПРАВИТЬ → статус → counts_card[`CTkScrollableFrame`, height=260] → СТАРТ), and adds
the initial-backlog display at the end.

- [ ] **Step 2: Show existing backlog (not a blank `{}`) when starting collection**

In `main.py`, in `toggle_chest_bot` (currently lines 2406-2438), replace this line (currently
line 2422):

```python
        self._update_chest_counts_display({})
```

with:

```python
        import chest_reader
        _conn = chest_reader.init_db()
        self._update_chest_counts_display(chest_reader.get_unsynced_counts(_conn))
        _conn.close()
```

(`import chest_reader` already happens a few lines above this point in the same function, at
line 2412 — keep both imports; Python caches the module so this is cheap and matches the
existing local-import style used throughout this function.)

- [ ] **Step 3: Clear the display after a successful upload**

In `main.py`, in `send_chests_to_server`'s inner `_update` function (currently lines 2476-2486),
change:

```python
            def _update():
                if result.get("success"):
                    self.chest_status_label.configure(text=L["chest_send_success"],
                                                       text_color=MD3["secondary"])
                elif result.get("low_credits"):
```

to:

```python
            def _update():
                if result.get("success"):
                    self.chest_status_label.configure(text=L["chest_send_success"],
                                                       text_color=MD3["secondary"])
                    self._update_chest_counts_display({})
                elif result.get("low_credits"):
```

- [ ] **Step 4: Static sanity check — confirm the file still parses**

Run: `python -c "import ast; ast.parse(open('main.py', encoding='utf-8').read())"`
Expected: no output, exit code 0 (syntax is valid — this does not execute the GUI).

- [ ] **Step 5: Run the full chest_reader test suite once more (regression safety net)**

Run: `python -m pytest test_chest_reader.py -v`
Expected: all tests pass (Task 3 doesn't touch `chest_reader.py`, this just confirms nothing
in Tasks 1-2 regressed before the manual GUI pass).

- [ ] **Step 6: Manual live verification**

Start the bot (`python main.py`), open the СУНДУКИ tab, and confirm by eye:
- Order top to bottom is: Королевство/Клан → ОТПРАВИТЬ НА СЕРВЕР → статус → счётчик по
  типам (scrollable) → «Всего» → СТАРТ.
- With the in-game «Мой клан → Подарки» dialog open, click СТАРТ, let it collect a few
  chests, click СТОП (same button, now showing «СТОП» while running) — confirm the type
  list and «Всего» reflect what was just collected.
- Click СТАРТ again, collect more, click СТОП — confirm «Всего» is the **sum** of both runs,
  not just the second run.
- Click ОТПРАВИТЬ НА СЕРВЕР — on success, confirm the type list clears and «Всего» returns
  to 0.
- Resize the window smaller / collect enough chest types to overflow the list — confirm the
  list scrolls internally and СТАРТ stays visible and clickable.

Report the outcome of this manual pass back before considering the plan done — this is the
only verification step for the GUI changes in this plan.

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat(main): chest tab — scrollable type list, button swap, DB-backed backlog counter"
```
