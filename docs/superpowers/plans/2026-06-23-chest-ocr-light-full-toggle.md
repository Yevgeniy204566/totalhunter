# Chest OCR Light/Full Language Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the owner/clan-admin choose between a fast 3-language ("Light") and a slow 8-language ("Full", all 19 bot-supported languages) OCR config for reading player nicknames in the chest-collection feature, since the full config measured ~2.5× slower (0.39s → 1.0s per chest) with no benefit for clans that only have Latin/Cyrillic names.

**Architecture:** A `full_lang: bool` parameter threaded explicitly through the existing call chain `collect_chests()` → `read_top_row()` → `read_sender_name()` in `chest_reader.py` — the same pattern already used for `pause_range` (the click-speed slider). A new `CTkSwitch` in `main.py`'s СУНДУКИ tab (mirroring the existing `_roy_switch` pattern), persisted to `gui_config.json["chest_full_lang_ocr"]`, read once at collection-start time and passed into `collect_chests()`.

**Tech Stack:** Python 3.13, pytest, pytesseract, CustomTkinter — client bot (not web/server).

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-06-23-chest-ocr-light-full-toggle-design.md`
- `LIGHT_SENDER_OCR_LANG = 'rus+eng+script/Latin'` (exact value — this is the OLD `SENDER_OCR_LANG` value, unchanged in content, just renamed).
- `FULL_SENDER_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'` (exact value — this is the new 19-language value from the prior, not-yet-released plan).
- `SENDER_OCR_CONFIG` is unchanged.
- `read_chest_type()` is unchanged — out of scope.
- The GUI switch's text labels must be the literal English words `"Light"` / `"Full"` — not translated, not localized via the `LANGS` dict.
- Default persisted value (first run after this ships) is `False` (Light).

---

### Task 1: `chest_reader.py` — thread `full_lang` through the call chain

**Files:**
- Modify: `chest_reader.py:122-143` (`SENDER_OCR_LANG`/`SENDER_OCR_CONFIG` constants, `read_sender_name`, `read_top_row`), `chest_reader.py:211-247` (`collect_chests`)
- Test: `test_chest_reader.py` (new tests + 3 existing fakes that need a signature update)

**Interfaces:**
- Produces: `read_sender_name(frame, full_lang=False)`, `read_top_row(frame, full_lang=False)`, `collect_chests(stop_flag, on_update=None, db_path=DB_PATH, pause_range=ANTI_DETECT_PAUSE_RANGE, full_lang=False)`. All four new/changed signatures default `full_lang=False`, so every existing caller (including `main.py`, which Task 2 updates separately) keeps working unchanged unless it opts in.

- [ ] **Step 1: Write the failing tests**

Add to `test_chest_reader.py`:

```python
def test_read_sender_name_light_lang_by_default(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame)

    assert captured["lang"] == "rus+eng+script/Latin"


def test_read_sender_name_full_lang_when_requested(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame, full_lang=True)

    assert captured["lang"] == "eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor"


def test_read_top_row_forwards_full_lang_to_sender(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr, "read_chest_type", lambda frame: "Сундук")

    def fake_read_sender_name(frame, full_lang=False):
        captured["full_lang"] = full_lang
        return "Player"
    monkeypatch.setattr(cr, "read_sender_name", fake_read_sender_name)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_top_row(frame, full_lang=True)

    assert captured["full_lang"] is True


def test_collect_chests_forwards_full_lang_to_read_top_row(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chest_buffer.db")
    captured = {}

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 300, 300))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((300, 300, 3), dtype=np.uint8))

    calls = {"n": 0}

    def fake_find_open_button(bbox):
        calls["n"] += 1
        return (10, 10) if calls["n"] <= 1 else None
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)

    def fake_read_top_row(frame, full_lang=False):
        captured["full_lang"] = full_lang
        return ("Сундук", "Player")
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", lambda pos, pause_range=cr.ANTI_DETECT_PAUSE_RANGE: None)

    cr.collect_chests(lambda: False, db_path=db_path, full_lang=True)

    assert captured["full_lang"] is True
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -k "light_lang_by_default or full_lang_when_requested or forwards_full_lang" -v`
Expected: FAIL — `read_sender_name`/`read_top_row`/`collect_chests` don't accept `full_lang` yet (`TypeError: unexpected keyword argument 'full_lang'`).

- [ ] **Step 3: Split the OCR-language constant and update `read_sender_name`/`read_top_row`**

Replace `chest_reader.py:122-138` (the comment block, `SENDER_OCR_LANG`/`SENDER_OCR_CONFIG`,
`read_sender_name`, and `read_top_row` — check exact current line numbers before editing, this
range may have shifted slightly since the last commit, but the content below is the full
replacement target):

```python
# Player name: stylized/unpredictable — dictionaries only hurt here (they force
# Tesseract to "correct" unfamiliar glyph shapes into known dictionary words, which is
# exactly what splits a name like "Marisha" into single dictionary-shaped letters).
# Disabling DAWG + full coverage of the bot's 19 supported languages (Latin diacritics,
# Cyrillic, Arabic, Japanese, Chinese x2, Korean) reads any script literally instead.
SENDER_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'
SENDER_OCR_CONFIG = '-c load_system_dawg=0 -c load_freq_dawg=0'


def read_sender_name(frame):
    return read_fixed_field(frame, SENDER_REF_RECT, "chest_sender",
                            lang=SENDER_OCR_LANG, extra_config=SENDER_OCR_CONFIG)


def read_chest_type(frame):
    return read_fixed_field(frame, SOURCE_REF_RECT, "chest_type")
```

with:

```python
# Player name: stylized/unpredictable — dictionaries only hurt here (they force
# Tesseract to "correct" unfamiliar glyph shapes into known dictionary words, which is
# exactly what splits a name like "Marisha" into single dictionary-shaped letters).
# Disabling DAWG reads any script literally instead. Two language sets: LIGHT (fast,
# Latin+Cyrillic, ~0.39s/call) covers most clans; FULL (all 19 bot-supported languages,
# ~1.0s/call — measured live on the real SENDER_REF_RECT crop size) adds Arabic/Japanese/
# Chinese/Korean for clans that actually need it. GUI lets the owner pick — most clans
# never need the 2.5x-slower FULL set.
LIGHT_SENDER_OCR_LANG = 'rus+eng+script/Latin'
FULL_SENDER_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'
SENDER_OCR_CONFIG = '-c load_system_dawg=0 -c load_freq_dawg=0'


def read_sender_name(frame, full_lang=False):
    lang = FULL_SENDER_OCR_LANG if full_lang else LIGHT_SENDER_OCR_LANG
    return read_fixed_field(frame, SENDER_REF_RECT, "chest_sender",
                            lang=lang, extra_config=SENDER_OCR_CONFIG)


def read_chest_type(frame):
    return read_fixed_field(frame, SOURCE_REF_RECT, "chest_type")
```

Then find `read_top_row` (currently `chest_reader.py:140-143`):

```python
def read_top_row(frame):
    chest_type = read_chest_type(frame)
    sender = read_sender_name(frame)
    return chest_type, sender
```

Replace with:

```python
def read_top_row(frame, full_lang=False):
    chest_type = read_chest_type(frame)
    sender = read_sender_name(frame, full_lang=full_lang)
    return chest_type, sender
```

- [ ] **Step 4: Update `collect_chests`'s signature and call site**

Find `collect_chests` (currently `chest_reader.py:211-247`). Replace its signature line:

```python
def collect_chests(stop_flag, on_update=None, db_path=DB_PATH, pause_range=ANTI_DETECT_PAUSE_RANGE):
```

with:

```python
def collect_chests(stop_flag, on_update=None, db_path=DB_PATH,
                   pause_range=ANTI_DETECT_PAUSE_RANGE, full_lang=False):
```

Update its docstring's last sentence (currently ends "...so the GUI's speed slider can control it
without mutating global state.") by appending:

```
 full_lang likewise overrides the OCR language set for read_top_row's
    sender-name field — see LIGHT_SENDER_OCR_LANG/FULL_SENDER_OCR_LANG.
```

And replace the call inside the loop:

```python
            chest_type, sender = read_top_row(frame)
```

with:

```python
            chest_type, sender = read_top_row(frame, full_lang=full_lang)
```

- [ ] **Step 5: Fix the 3 existing test fakes that monkeypatch `read_top_row` with a too-narrow signature**

In `test_chest_reader.py`, there are three occurrences of the exact line:

```python
    def fake_read_top_row(frame):
```

Each must become:

```python
    def fake_read_top_row(frame, **kwargs):
```

Use a find-and-replace-all for this exact line across the file (it appears identically at three
call sites — inside `test_collect_chests_counts_and_persists`,
`test_collect_chests_counts_are_cumulative_from_db`, and
`test_collect_chests_forwards_pause_range_to_click`). Without this fix, `collect_chests`'s new
`read_top_row(frame, full_lang=full_lang)` call would raise
`TypeError: fake_read_top_row() got an unexpected keyword argument 'full_lang'` in those three
existing tests once Step 4 lands.

- [ ] **Step 6: Run the new tests to verify they pass**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -k "light_lang_by_default or full_lang_when_requested or forwards_full_lang" -v`
Expected: PASS (4/4)

- [ ] **Step 7: Run the full `test_chest_reader.py` file to check no regressions**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -v`
Expected: all PASS, including the three fakes fixed in Step 5 and the live
`test_read_top_row_on_fixture` (calls `cr.read_top_row(frame)` with no `full_lang` — defaults to
`False`/Light, same `LIGHT_SENDER_OCR_LANG` value as before this plan, so the fixture's expected
`"Gray Cardinal"` result is unaffected).

- [ ] **Step 8: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chests): add full_lang toggle to thread Light/Full OCR language sets through collect_chests->read_top_row->read_sender_name"
```

---

### Task 2: `main.py` — Light/Full switch in the СУНДУКИ tab

**Files:**
- Modify: `main.py` (chest tab build section, around `chest_speed_slider`; `toggle_chest_bot`'s start branch)

**Interfaces:**
- Consumes: `chest_reader.collect_chests(..., full_lang=...)` from Task 1 (already merged).
- Produces: no new interfaces consumed elsewhere — this is the GUI leaf.

There is no automated test suite for `main.py`'s GUI code (consistent with the rest of this
project) — verification is a careful diff self-review plus, if a real Windows display is
available, a manual launch-and-click check. If not available, say so plainly in the report.

- [ ] **Step 1: Add the switch next to the speed slider**

Find this block in `main.py` (currently around line 4033-4043):

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

Add immediately after it (still before the "Старт/Стоп" block):

```python
        # ── Light/Full — переключатель набора языков OCR имени игрока ────
        saved_full_lang = self._load_gui_config().get("chest_full_lang_ocr", False)
        self.chest_full_lang_var = ctk.BooleanVar(value=saved_full_lang)
        lang_toggle_row = ctk.CTkFrame(self.tab_chest, fg_color="transparent")
        lang_toggle_row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(lang_toggle_row, text="Light", font=ctk.CTkFont(size=12)).pack(side="left")
        self.chest_full_lang_switch = ctk.CTkSwitch(
            lang_toggle_row, text="Full", variable=self.chest_full_lang_var,
            onvalue=True, offvalue=False,
            command=self._on_chest_full_lang_change,
            fg_color=MD3["outline"], progress_color=MD3["primary"],
        )
        self.chest_full_lang_switch.pack(side="right")
```

- [ ] **Step 2: Add the persistence handler**

Find `_on_chest_speed_change` (currently `main.py:4071-4074`):

```python
    def _on_chest_speed_change(self, value):
        L = LANGS[self.current_lang]
        self._save_gui_config_key("chest_click_pause", round(float(value), 2))
        self.chest_speed_label.configure(text=f"{L['chest_speed_lb']} {float(value):.2f} {L['sec']}")
```

Add immediately after it:

```python
    def _on_chest_full_lang_change(self):
        self._save_gui_config_key("chest_full_lang_ocr", bool(self.chest_full_lang_var.get()))
```

- [ ] **Step 3: Read the setting when starting collection**

Find `toggle_chest_bot`'s start branch (currently `main.py:2443-2466`). The line:

```python
        pause_range = self._chest_pause_range(self.chest_speed_slider.get())
```

stays as-is; add immediately after it:

```python
        full_lang = bool(self.chest_full_lang_var.get())
```

Then find the worker call:

```python
        def _worker():
            result = chest_reader.collect_chests(stop_event.is_set, on_update=_on_update,
                                                  pause_range=pause_range)
            self.after(0, lambda: self._on_chest_collection_done(result))
```

Replace with:

```python
        def _worker():
            result = chest_reader.collect_chests(stop_event.is_set, on_update=_on_update,
                                                  pause_range=pause_range, full_lang=full_lang)
            self.after(0, lambda: self._on_chest_collection_done(result))
```

- [ ] **Step 4: Self-review the diff**

Read back the three edited regions in `main.py` and confirm: `chest_full_lang_var`/
`chest_full_lang_switch` are defined before `toggle_chest_bot` could possibly run (they're set up
during tab construction, which always happens before the user can click Start — same lifecycle as
`chest_speed_slider`); the switch's `text="Full"` and the adjacent label's `text="Light"` are the
literal English words, not pulled from `L[...]`/`LANGS`.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat(chests): add Light/Full OCR language switch to chest tab GUI, wired to collect_chests(full_lang=...)"
```

---

## Self-Review Notes

- Spec coverage: spec's `chest_reader.py` architecture section → Task 1; spec's `main.py` GUI
  section → Task 2; spec's testing section → Task 1 Steps 1-7 (GUI explicitly has no automated
  tests, matching the spec's own testing section which says so).
- Placeholder scan: none — every step has literal code, exact line ranges, exact commands.
- Type/signature consistency: `full_lang` is a plain `bool` everywhere (`read_sender_name`,
  `read_top_row`, `collect_chests`, the GUI's `BooleanVar`) — no int/string mismatches across the
  chain. `LIGHT_SENDER_OCR_LANG`/`FULL_SENDER_OCR_LANG` string values are identical between Task
  1's test assertions and its implementation.

## Deployment

This is a client-bot change. Per `CLAUDE.md`, building and releasing a new ZIP happens **only on
the owner's explicit instruction** — do not build or release automatically after these tasks land.
This plan was specifically requested to land BEFORE the already-prepared v1.8.3 build (full
19-language OCR, not yet released) — once both this plan and that release are ready together, ask
the owner before building.
