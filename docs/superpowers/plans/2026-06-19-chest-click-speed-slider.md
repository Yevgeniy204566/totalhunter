# Сундуки — ползунок скорости клика Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded anti-detect click pause in chest collection with a GUI slider
(0.1–1.0s) that the owner can tune live, persisted across restarts.

**Architecture:** `chest_reader.py` gains an explicit `pause_range` parameter (threaded through
`click_open_button` and `collect_chests`, defaulting to the existing module constant so nothing
breaks if the caller passes nothing). `main.py` adds a `CTkSlider` above the START button in the
СУНДУКИ tab; its value is persisted to `gui_config.json` and converted to a `(lower, upper)` pair
via a fixed formula before each collection run starts.

**Tech Stack:** Python 3.13, customtkinter, pytest, unittest.mock.

## Global Constraints

- Range formula (owner-confirmed, exact verbatim): `lower = max(0.1, slider_value - 0.1)`,
  `upper = lower + 0.2`. Verified examples: `0.3 -> (0.2, 0.4)`, `0.1 -> (0.1, 0.3)`.
- Slider range: `0.1` to `1.0`, step `0.01`.
- Default value before the user ever touches the slider: `0.22`.
- The pause must never be allowed to go below `0.1` seconds — this is a hard anti-bot floor,
  not just a UX default. The formula's `max(0.1, ...)` is what enforces this; do not remove it.
- The upper bound is NOT clamped at the slider's max (`1.0`) — at `slider=1.0` the real range is
  `(0.9, 1.1)`, intentionally left as-is per owner decision.
- Persisted to `gui_config.json` under key `chest_click_pause`, saved immediately on every slider
  move (same pattern as `chest_kingdom`/`chest_clan` — no separate "Save" button).
- Slider placed above `chest_start_btn` in the СУНДУКИ tab.
- `chest_reader.py`'s existing module constant `ANTI_DETECT_PAUSE_RANGE` stays as the default
  fallback — do not delete it, do not mutate it at runtime. The GUI passes its own computed
  tuple as an explicit argument instead.
- Comments in code: WHY only, not WHAT (per project convention).

---

### Task 1: `chest_reader.py` — explicit `pause_range` parameter

**Files:**
- Modify: `chest_reader.py:192-197` (`click_open_button`)
- Modify: `chest_reader.py:200-240` (`collect_chests`)
- Test: `test_chest_reader.py` (add tests near the existing `test_find_open_button_region_is_top_row_right_side` / `test_collect_chests_*` tests)

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: `click_open_button(pos, pause_range=ANTI_DETECT_PAUSE_RANGE)` and
  `collect_chests(stop_flag, on_update=None, db_path=DB_PATH, pause_range=ANTI_DETECT_PAUSE_RANGE)`
  — Task 2 (`main.py`) calls `collect_chests(..., pause_range=computed_tuple)`.

- [ ] **Step 1: Write the failing tests**

Add to `test_chest_reader.py` (check the top of the file for how `chest_reader` is imported —
match the existing alias, e.g. `import chest_reader as cr`, used by the other tests in this file):

```python
def test_click_open_button_uses_passed_pause_range(monkeypatch):
    captured = {}

    def fake_uniform(lo, hi):
        captured["range"] = (lo, hi)
        return 0.0

    monkeypatch.setattr(cr.random, "uniform", fake_uniform)
    monkeypatch.setattr(cr.pyautogui, "click", lambda *a, **k: None)
    monkeypatch.setattr(cr.time, "sleep", lambda *a, **k: None)

    cr.click_open_button((10, 10), pause_range=(0.5, 0.6))

    assert captured["range"] == (0.5, 0.6)


def test_click_open_button_defaults_to_module_constant(monkeypatch):
    captured = {}

    def fake_uniform(lo, hi):
        captured["range"] = (lo, hi)
        return 0.0

    monkeypatch.setattr(cr.random, "uniform", fake_uniform)
    monkeypatch.setattr(cr.pyautogui, "click", lambda *a, **k: None)
    monkeypatch.setattr(cr.time, "sleep", lambda *a, **k: None)

    cr.click_open_button((10, 10))

    assert captured["range"] == cr.ANTI_DETECT_PAUSE_RANGE
```

Also add this test for `collect_chests` forwarding the argument through to every click in a
session (follow the exact monkeypatch style used by the existing
`test_collect_chests_counts_are_cumulative_from_db` test in this same file — read it first,
match its fakes for `grab_fullscreen`/`detect_dialog_bbox`/`find_open_button`/`read_top_row`,
don't reinvent them):

```python
def test_collect_chests_forwards_pause_range_to_click(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    captured_ranges = []

    def fake_grab_fullscreen():
        return object()

    def fake_detect_dialog_bbox(frame):
        return (0, 0, 300, 300)

    calls = {"n": 0}

    def fake_find_open_button(bbox):
        calls["n"] += 1
        return (10, 10) if calls["n"] <= 1 else None

    def fake_read_top_row(frame):
        return ("Сундук Эпического Монстра", "Игрок")

    def fake_click_open_button(pos, pause_range=cr.ANTI_DETECT_PAUSE_RANGE):
        captured_ranges.append(pause_range)

    monkeypatch.setattr(cr, "grab_fullscreen", fake_grab_fullscreen)
    monkeypatch.setattr(cr, "detect_dialog_bbox", fake_detect_dialog_bbox)
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", fake_click_open_button)

    cr.collect_chests(lambda: False, db_path=db_path, pause_range=(0.5, 0.6))

    assert captured_ranges == [(0.5, 0.6)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -k "pause_range" -v`
Expected: FAIL — `click_open_button() got an unexpected keyword argument 'pause_range'` (first
two tests), and the third fails because `collect_chests` doesn't accept `pause_range` either.

- [ ] **Step 3: Implement**

In `chest_reader.py`, replace `click_open_button` (currently lines 192-197):

```python
def click_open_button(pos, pause_range=ANTI_DETECT_PAUSE_RANGE):
    cx, cy = pos
    click_x = cx + random.randint(-ANTI_DETECT_OFFSET_PX, ANTI_DETECT_OFFSET_PX)
    click_y = cy + random.randint(-5, 5)
    pyautogui.click(click_x, click_y)
    time.sleep(random.uniform(*pause_range))
```

In `collect_chests` (currently lines 200-240), change the signature and the one call site:

```python
def collect_chests(stop_flag, on_update=None, db_path=DB_PATH, pause_range=ANTI_DETECT_PAUSE_RANGE):
    """Reads and opens chests from the top of the «Мой клан → Подарки» list
    until the list is empty (no «Открыть» button found) or stop_flag()
    returns True. Every chest is persisted to SQLite as it's read.
    Returns {'counts': {chest_type: n}, 'items': [{'chest_type', 'sender',
    'timestamp'}, ...]} for this session. 'counts' is sourced from the DB
    (get_unsynced_counts), not a session-local tally, so it always reflects
    the full unsynced backlog — not just what this call found. pause_range
    overrides the module's anti-detect click-pause default for this call,
    so the GUI's speed slider can control it without mutating global state."""
```
(keep the rest of the function body unchanged except the one line calling `click_open_button`,
currently `click_open_button(pos)`, which becomes:)
```python
            click_open_button(pos, pause_range)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: all tests pass, including the new ones and every pre-existing test (25 total after
this task — 21 from before plus these 3 new... wait: 2 click_open_button tests + 1 collect_chests
test = 3 new, 21 existing = 24 total).

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest_reader): accept explicit pause_range, default unchanged"
```

---

### Task 2: `main.py` — speed slider, persistence, wiring

**Files:**
- Modify: `main.py:3899-3998` (`setup_chest_tab` — add slider above `chest_start_btn`, load saved value, add a handler that saves + updates the label)
- Modify: `main.py:2406-2438` (`toggle_chest_bot` — compute `pause_range` from the saved slider value, pass it to `chest_reader.collect_chests`)

**Interfaces:**
- Consumes: `chest_reader.collect_chests(stop_flag, on_update=None, db_path=DB_PATH, pause_range=ANTI_DETECT_PAUSE_RANGE)` (Task 1).
- Produces: nothing consumed by later tasks — this is the last task in the plan.

This task is GUI-only (customtkinter) and is not covered by automated tests, per the design
spec — the formula itself (`_chest_pause_range`) is pure arithmetic and gets a quick manual
check in Step 4, the full slider gets a live check in Step 5.

- [ ] **Step 1: Add the pause-range formula and a label-formatting helper**

In `main.py`, find `setup_chest_tab` (starts at line 3899). Immediately before it, add a new
method on the same class:

```python
    def _chest_pause_range(self, slider_value: float) -> tuple:
        """Owner-confirmed formula (verified examples: 0.3 -> (0.2, 0.4),
        0.1 -> (0.1, 0.3)) — the 0.1 floor on the lower bound is a hard
        anti-bot minimum, not just a UX default; never remove it."""
        lower = max(0.1, slider_value - 0.1)
        return (lower, lower + 0.2)
```

- [ ] **Step 2: Add the slider widget above `chest_start_btn`**

In `setup_chest_tab`, find the block that creates `self.chest_start_btn` (search for
`command=self.toggle_chest_bot` — it currently looks like this, right after the `counts_card`
block):

```python
        # ── Старт/Стоп — внизу, всегда после счётчика ────────────────────
        self.chest_start_btn = ctk.CTkButton(
            self.tab_chest, text=L["chest_start_btn"],
            height=42, corner_radius=10,
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self.toggle_chest_bot)
        self.chest_start_btn.pack(padx=20, pady=(4, 14), fill="x")
        self._i18n_labels.append((self.chest_start_btn, "chest_start_btn"))
```

Insert the slider block immediately before it (so the slider ends up above the button in the
packed layout):

```python
        # ── Скорость клика — ползунок анти-детект паузы, над СТАРТ ───────
        saved_pause = self._load_gui_config().get("chest_click_pause", 0.22)
        self.chest_speed_label = ctk.CTkLabel(
            self.tab_chest, text=f"{L['chest_speed_lb']} {saved_pause:.2f} {L['sec']}",
            font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"])
        self.chest_speed_label.pack(padx=20, pady=(0, 2))
        self.chest_speed_slider = ctk.CTkSlider(
            self.tab_chest, from_=0.1, to=1.0, number_of_steps=90,
            command=self._on_chest_speed_change)
        self.chest_speed_slider.set(saved_pause)
        self.chest_speed_slider.pack(padx=20, pady=(0, 8), fill="x")
```

- [ ] **Step 3: Add the slider's change handler**

In `main.py`, find `_on_chest_clan_change` (the method right after `_on_chest_kingdom_change`,
near the top of the chest-tab methods — currently around line 3995):

```python
    def _on_chest_clan_change(self, event=None):
        self._save_gui_config_key("chest_clan", self.chest_clan_entry.get().strip())
```

Add this new method immediately after it:

```python
    def _on_chest_speed_change(self, value):
        L = LANGS[self.current_lang]
        self._save_gui_config_key("chest_click_pause", round(float(value), 2))
        self.chest_speed_label.configure(text=f"{L['chest_speed_lb']} {float(value):.2f} {L['sec']}")
```

- [ ] **Step 4: Add the `chest_speed_lb` translation key to all 19 languages**

The label needs a translated prefix (e.g. Russian "Скорость клика:", English "Click speed:").
Open `main.py` and find the 19 `"tab_chest":` lines you edited earlier this session (one per
language block — `RU`, `EN`, `DE`, `ES`, `FR`, `IT`, `NL`, `NO`, `PL`, `PT`, `SV`, `TR`, `AR`,
`JA`, `ZH`, `ZH_TW`, `KO`, `UK`, `ID`). In each language's block, add one new key right after
`"chest_total_lb"` (it's the last chest_* key in each block, e.g. for RU:
`"chest_total_lb": "Всего открыто:",`). Add immediately after that line, in the same block, for
each language respectively:

- RU: `"chest_speed_lb": "Скорость клика:",`
- EN: `"chest_speed_lb": "Click speed:",`
- DE: `"chest_speed_lb": "Klickgeschwindigkeit:",`
- ES: `"chest_speed_lb": "Velocidad de clic:",`
- FR: `"chest_speed_lb": "Vitesse de clic :",`
- IT: `"chest_speed_lb": "Velocità di clic:",`
- NL: `"chest_speed_lb": "Kliksnelheid:",`
- NO: `"chest_speed_lb": "Klikkhastighet:",`
- PL: `"chest_speed_lb": "Szybkość kliknięcia:",`
- PT: `"chest_speed_lb": "Velocidade de clique:",`
- SV: `"chest_speed_lb": "Klickhastighet:",`
- TR: `"chest_speed_lb": "Tıklama hızı:",`
- AR: `"chest_speed_lb": "سرعة النقر:",`
- JA: `"chest_speed_lb": "クリック速度:",`
- ZH: `"chest_speed_lb": "点击速度:",`
- ZH_TW: `"chest_speed_lb": "點擊速度:",`
- KO: `"chest_speed_lb": "클릭 속도:",`
- UK: `"chest_speed_lb": "Швидкість кліку:",`
- ID: `"chest_speed_lb": "Kecepatan klik:",`

Every language block already has a `"sec"` key used elsewhere in the file (Russian: `"sec": "сек."`)
— the label re-uses that existing key, no need to add it.

- [ ] **Step 5: Wire the slider value into `toggle_chest_bot`**

In `main.py`, find `toggle_chest_bot` (starts at line 2406). It currently has, right after the
`import chest_reader` / dialog-detection guard:

```python
        self._chest_running = True
        self._chest_stop_event = threading.Event()
        import chest_reader
        _conn = chest_reader.init_db()
        self._update_chest_counts_display(chest_reader.get_unsynced_counts(_conn))
        _conn.close()
```

Immediately after that block (still inside `toggle_chest_bot`, before the `stop_event = ...`
line), add:

```python
        pause_range = self._chest_pause_range(self.chest_speed_slider.get())
```

Then find the `_worker` closure a few lines further down — currently:

```python
        def _worker():
            result = chest_reader.collect_chests(stop_event.is_set, on_update=_on_update)
            self.after(0, lambda: self._on_chest_collection_done(result))
```

Change the `collect_chests` call to pass the computed range:

```python
        def _worker():
            result = chest_reader.collect_chests(stop_event.is_set, on_update=_on_update,
                                                  pause_range=pause_range)
            self.after(0, lambda: self._on_chest_collection_done(result))
```

- [ ] **Step 6: Static sanity check**

Run: `python -c "import ast; ast.parse(open('main.py', encoding='utf-8').read())"`
Expected: no output, exit code 0.

- [ ] **Step 7: Run the chest_reader regression suite**

Run: `python -m pytest test_chest_reader.py -v`
Expected: all tests pass (this task doesn't touch `chest_reader.py`, this just confirms nothing
regressed before the manual GUI pass).

- [ ] **Step 8: Manual live verification**

Start the bot (`python main.py`), open the СУНДУКИ tab, and confirm by eye:
- A slider labeled with the current speed value (e.g. "Скорость клика: 0.22 сек") appears
  directly above the СТАРТ button.
- Dragging the slider updates the label live, in real time, to two decimal places.
- Drag the slider to its minimum (leftmost) — label should read `0.10`. Drag to maximum
  (rightmost) — label should read `1.00`.
- Restart the bot (`python main.py` again) — the slider should come back at whatever value you
  last left it at (not reset to `0.22`), confirming `gui_config.json` persistence.
- With the in-game «Мой клан → Подарки» dialog open, set the slider to a low value (e.g. `0.1`)
  and click СТАРТ — clicks between chests should feel noticeably faster than at a high slider
  value (e.g. `0.8`). Stop and try the high value to compare.
- Switch the GUI language (any language picker already in the app) and confirm the slider's
  label prefix translates (e.g. switches between "Скорость клика:" and "Click speed:").

Report the outcome of this manual pass back before considering the plan done.

- [ ] **Step 9: Commit**

```bash
git add main.py
git commit -m "feat(main): chest click-speed slider, persisted, wired into collect_chests"
```
