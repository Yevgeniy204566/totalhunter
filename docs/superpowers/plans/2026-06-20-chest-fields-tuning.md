# Тюнинг полей распознавания сундуков Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the owner micro-tune the two chest OCR read-regions (player name, chest source) via
the existing D-Pad "Тюнинг кликов" widget, with a live rectangle overlay over the game showing the
exact crop area.

**Architecture:** `coord_manager.py` gains two more named offsets (`chest_sender`, `chest_type`) in
its existing `ui_offsets` mechanism — no new storage concept. `chest_reader.py`'s
`read_fixed_field` applies that named offset on top of the calibrated rect before cropping for OCR.
`main.py`'s existing D-Pad tuning panel (Калибровка tab) gets two more selectable targets in its
dropdown, and a rectangle-shaped live overlay (reusing the `Toplevel`/`after`-timer pattern already
used by `_show_calibration_dot`) instead of a dot, sized to the real OCR crop dimensions.

**Tech Stack:** Python 3.13, customtkinter, pytest, unittest.mock (monkeypatch).

## Global Constraints

- New `ui_offsets` keys: exactly `"chest_sender"` and `"chest_type"` (chosen to match
  `chest_reader.py`'s existing `read_sender_name`/`read_chest_type` naming).
- Default offset for both new keys is `(0, 0)` — behavior must be unchanged for every existing
  caller until the owner manually nudges the D-Pad at least once.
- Storage/persistence (`save()`, `load()`, JSON shape) is NOT modified — it's already generic over
  whatever keys exist in `ui_offsets`.
- The overlay rectangle is shown only when one of the two new targets is selected in the D-Pad
  dropdown — the 4 pre-existing targets (`wt_icon`, `carter`, `top_accel`, `march_accel`) get no
  visual change.
- Overlay `Toplevel` must use `attributes('-topmost', True)` (so it renders above the game window)
  and auto-hide after 3 seconds after the last D-Pad press, matching `_show_calibration_dot`'s
  existing timer pattern.
- Comments in code: WHY only, not WHAT (per project convention).

---

### Task 1: `coord_manager.py` — register the two new tunable names

**Files:**
- Modify: `coord_manager.py:41` (`_UI_BUTTON_NAMES` tuple)
- Test: `test_ui_tuning.py:10` (`KNOWN_BUTTONS` constant) and `test_ui_tuning.py:14-16`
  (rename for clarity, two more buttons)

**Interfaces:**
- Consumes: nothing new.
- Produces: `coord_manager.get_ui_offset("chest_sender")` / `coord_manager.get_ui_offset("chest_type")`
  — Task 2 (`chest_reader.py`) and Task 3 (`main.py`) both call these by name.

- [ ] **Step 1: Write the failing test**

In `test_ui_tuning.py`, change line 10 from:
```python
KNOWN_BUTTONS = {"wt_icon", "carter", "top_accel", "march_accel"}
```
to:
```python
KNOWN_BUTTONS = {"wt_icon", "carter", "top_accel", "march_accel", "chest_sender", "chest_type"}
```
Then rename the test on line 14 (it now covers six names, not four) — change:
```python
    def test_all_four_buttons_present_after_init(self):
```
to:
```python
    def test_all_known_buttons_present_after_init(self):
```
No other line in the file needs to change — every other test already iterates `KNOWN_BUTTONS` or
calls `get_ui_offset`/`set_ui_offset` by name generically.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_ui_tuning.py -v`
Expected: FAIL on `test_all_known_buttons_present_after_init` —
`AssertionError: {'wt_icon', 'carter', 'top_accel', 'march_accel', 'chest_sender', 'chest_type'} != {'wt_icon', 'carter', 'top_accel', 'march_accel'}`

- [ ] **Step 3: Implement**

In `coord_manager.py`, change line 41 from:
```python
    _UI_BUTTON_NAMES = ("wt_icon", "carter", "top_accel", "march_accel")
```
to:
```python
    _UI_BUTTON_NAMES = ("wt_icon", "carter", "top_accel", "march_accel", "chest_sender", "chest_type")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_ui_tuning.py -v`
Expected: all tests pass (the suite is generic over `_UI_BUTTON_NAMES`, no other code changes needed).

- [ ] **Step 5: Commit**

```bash
git add coord_manager.py test_ui_tuning.py
git commit -m "feat(coord_manager): add chest_sender/chest_type tunable offsets"
```

---

### Task 2: `chest_reader.py` — apply the named offset when cropping

**Files:**
- Modify: `chest_reader.py:115-132` (`read_fixed_field`, `read_sender_name`, `read_chest_type`)
- Test: `test_chest_reader.py` (add tests near the existing `test_read_chest_type_uses_fixed_calibrated_region` / `test_read_sender_name_uses_fixed_calibrated_region` tests)

**Interfaces:**
- Consumes: `coord_manager.get_ui_offset(name: str) -> tuple[int, int]` (Task 1).
- Produces: nothing new consumed by Task 3 — `main.py` computes the overlay rectangle independently
  using the same `coord_manager.to_region_dialog` + `coord_manager.get_ui_offset` building blocks,
  not by calling into `chest_reader.py`.

- [ ] **Step 1: Write the failing tests**

Add to `test_chest_reader.py` (after the existing `test_read_sender_name_applies_clean_name_artifact_stripping`
test, i.e. after line 79):

```python
def test_read_fixed_field_applies_named_offset(monkeypatch):
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (10, 10, 3, 3))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: (2, -1))
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: "")

    frame = np.arange(1200).reshape(20, 20, 3).astype(np.uint8)
    captured = {}
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: captured.setdefault("roi", roi.copy()) and "")

    cr.read_fixed_field(frame, (1, 2, 3, 4), offset_name="chest_type")

    expected = frame[9:12, 12:15]
    assert np.array_equal(captured["roi"], expected)


def test_read_fixed_field_without_offset_name_uses_zero_offset(monkeypatch):
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (10, 10, 3, 3))

    def fail_if_called(name):
        raise AssertionError("get_ui_offset should not be called when offset_name is None")
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", fail_if_called)

    captured = {}
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: captured.setdefault("roi", roi.copy()) and "")

    frame = np.arange(1200).reshape(20, 20, 3).astype(np.uint8)
    cr.read_fixed_field(frame, (1, 2, 3, 4))

    expected = frame[10:13, 10:13]
    assert np.array_equal(captured["roi"], expected)


def test_read_chest_type_passes_chest_type_offset_name(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: captured.setdefault("name", name) and (0, 0))
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: "")

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_chest_type(frame)

    assert captured["name"] == "chest_type"


def test_read_sender_name_passes_chest_sender_offset_name(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))
    monkeypatch.setattr(cr.coord_manager, "get_ui_offset", lambda name: captured.setdefault("name", name) and (0, 0))
    monkeypatch.setattr(cr, "ocr_text", lambda roi, **kwargs: "")

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame)

    assert captured["name"] == "chest_sender"
```

Note: `dict.setdefault(...) and ""` is a compact way to both record a value and return `""` from a
one-line lambda — `setdefault` returns the value just stored (truthy here, a numpy array, so `and`
falls through to `""`). This matches the file's existing lambda-heavy monkeypatch style.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -k "offset_name or applies_named_offset or zero_offset" -v`
Expected: FAIL — `TypeError: read_fixed_field() got an unexpected keyword argument 'offset_name'`
(first two new tests), and `AssertionError: 'name' not in {}` or similar for the last two (since
`read_chest_type`/`read_sender_name` don't call `get_ui_offset` at all yet).

- [ ] **Step 3: Implement**

In `chest_reader.py`, replace the three functions (currently lines 115-132):
```python
def read_fixed_field(frame, ref_rect):
    x, y, w, h = coord_manager.to_region_dialog(*ref_rect)
    roi = frame[y:y + h, x:x + w]
    return clean_name(ocr_text(roi))


def read_sender_name(frame):
    return read_fixed_field(frame, SENDER_REF_RECT)


def read_chest_type(frame):
    return read_fixed_field(frame, SOURCE_REF_RECT)
```
with:
```python
def read_fixed_field(frame, ref_rect, offset_name=None):
    x, y, w, h = coord_manager.to_region_dialog(*ref_rect)
    if offset_name is not None:
        dx, dy = coord_manager.get_ui_offset(offset_name)
        x, y = x + dx, y + dy
    roi = frame[y:y + h, x:x + w]
    return clean_name(ocr_text(roi))


def read_sender_name(frame):
    return read_fixed_field(frame, SENDER_REF_RECT, "chest_sender")


def read_chest_type(frame):
    return read_fixed_field(frame, SOURCE_REF_RECT, "chest_type")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: all tests pass (24 existing + 4 new = 28 total). The pre-existing
`test_read_chest_type_uses_fixed_calibrated_region` and
`test_read_sender_name_uses_fixed_calibrated_region` tests still pass unchanged — they don't mock
`get_ui_offset`, so the real `coord_manager` singleton's offset for `chest_sender`/`chest_type`
defaults to `(0, 0)` (per Task 1, fresh `_UI_BUTTON_NAMES` entries default to `[0, 0]`), so the
crop position is unaffected by the new code path in this test run.

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest_reader): apply tunable chest_sender/chest_type offset before crop"
```

---

### Task 3: `main.py` — D-Pad dropdown entries + live rectangle overlay

**Files:**
- Modify: `main.py:184-1245` (19 language blocks — add `cal_tune_chest_sender` / `cal_tune_chest_type` keys)
- Modify: `main.py:4288` (`_TUNE_INTERNAL` tuple)
- Modify: `main.py:4307-4339` (`_tune_on_select`, `_tune_apply` — trigger the overlay)
- Modify: `main.py:3012-3035` (add a sibling to `_show_calibration_dot` for the rectangle overlay)

**Interfaces:**
- Consumes: `coord_manager.get_ui_offset(name)` / `coord_manager.to_region_dialog(*rect)` (Task 1),
  `chest_reader.SENDER_REF_RECT` / `chest_reader.SOURCE_REF_RECT` (already exist, unchanged).
- Produces: nothing — last task in the plan.

This task is GUI-only (customtkinter + a `Toplevel` overlay) and is not covered by automated tests,
per the design spec — same precedent as the chest click-speed slider task. Manual verification is
Step 6 below.

- [ ] **Step 1: Add the two translation keys to all 19 language blocks**

For each of the 19 lines listed below, insert `"cal_tune_chest_sender": "...", "cal_tune_chest_type": "...",`
immediately after the `"cal_tune_reset"` entry on that same line (every block is a single line, so
this is an in-place edit of that one line, not a new line). Exact line numbers and the text to
insert for each:

| Line | Insert after `"cal_tune_reset": "..."` |
|---|---|
| 184 (RU) | `"cal_tune_chest_sender": "Имя игрока (сундуки)", "cal_tune_chest_type": "Источник (сундуки)",` |
| 256 (EN) | `"cal_tune_chest_sender": "Player Name (Chests)", "cal_tune_chest_type": "Source (Chests)",` |
| 317 (DE) | `"cal_tune_chest_sender": "Spielername (Truhen)", "cal_tune_chest_type": "Quelle (Truhen)",` |
| 375 (ES) | `"cal_tune_chest_sender": "Nombre del jugador (Cofres)", "cal_tune_chest_type": "Fuente (Cofres)",` |
| 433 (FR) | `"cal_tune_chest_sender": "Nom du joueur (Coffres)", "cal_tune_chest_type": "Source (Coffres)",` |
| 491 (IT) | `"cal_tune_chest_sender": "Nome giocatore (Forzieri)", "cal_tune_chest_type": "Fonte (Forzieri)",` |
| 549 (NL) | `"cal_tune_chest_sender": "Spelersnaam (Kisten)", "cal_tune_chest_type": "Bron (Kisten)",` |
| 607 (NO) | `"cal_tune_chest_sender": "Spillernavn (Kister)", "cal_tune_chest_type": "Kilde (Kister)",` |
| 665 (PL) | `"cal_tune_chest_sender": "Nazwa gracza (Skrzynie)", "cal_tune_chest_type": "Źródło (Skrzynie)",` |
| 723 (PT) | `"cal_tune_chest_sender": "Nome do jogador (Baús)", "cal_tune_chest_type": "Fonte (Baús)",` |
| 781 (SV) | `"cal_tune_chest_sender": "Spelarnamn (Kistor)", "cal_tune_chest_type": "Källa (Kistor)",` |
| 839 (TR) | `"cal_tune_chest_sender": "Oyuncu adı (Sandıklar)", "cal_tune_chest_type": "Kaynak (Sandıklar)",` |
| 897 (AR) | `"cal_tune_chest_sender": "اسم اللاعب (الصناديق)", "cal_tune_chest_type": "المصدر (الصناديق)",` |
| 955 (JA) | `"cal_tune_chest_sender": "プレイヤー名（チェスト）", "cal_tune_chest_type": "ソース（チェスト）",` |
| 1013 (ZH) | `"cal_tune_chest_sender": "玩家名称（宝箱）", "cal_tune_chest_type": "来源（宝箱）",` |
| 1071 (ZH_TW) | `"cal_tune_chest_sender": "玩家名稱（寶箱）", "cal_tune_chest_type": "來源（寶箱）",` |
| 1129 (KO) | `"cal_tune_chest_sender": "플레이어 이름(상자)", "cal_tune_chest_type": "출처(상자)",` |
| 1187 (UK) | `"cal_tune_chest_sender": "Ім'я гравця (скрині)", "cal_tune_chest_type": "Джерело (скрині)",` |
| 1245 (ID) | `"cal_tune_chest_sender": "Nama pemain (Peti)", "cal_tune_chest_type": "Sumber (Peti)",` |

Example for line 184 — before:
```python
        "cal_tune_title": "Тюнинг кликов", "cal_tune_wt_icon": "Дозорная башня", "cal_tune_carter": "Отправка Картера", "cal_tune_top_accel": "Ускорить (Картер)", "cal_tune_march_accel": "Использовать ускорение", "cal_tune_reset": "Сброс",
```
after:
```python
        "cal_tune_title": "Тюнинг кликов", "cal_tune_wt_icon": "Дозорная башня", "cal_tune_carter": "Отправка Картера", "cal_tune_top_accel": "Ускорить (Картер)", "cal_tune_march_accel": "Использовать ускорение", "cal_tune_reset": "Сброс", "cal_tune_chest_sender": "Имя игрока (сундуки)", "cal_tune_chest_type": "Источник (сундуки)",
```
Apply the same pattern (append after the `"cal_tune_reset": "...",` segment, same line) for all 19
lines using the table above.

- [ ] **Step 2: Static sanity check**

Run: `python -c "import ast; ast.parse(open('main.py', encoding='utf-8').read())"`
Expected: no output, exit code 0.

- [ ] **Step 3: Extend `_TUNE_INTERNAL` with the two new targets**

In `main.py`, find (currently line 4288):
```python
        _TUNE_INTERNAL = ("wt_icon", "carter", "top_accel", "march_accel")
```
Change to:
```python
        _TUNE_INTERNAL = ("wt_icon", "carter", "top_accel", "march_accel", "chest_sender", "chest_type")
```

- [ ] **Step 4: Add the rectangle-overlay helper**

In `main.py`, find `_show_calibration_dot` (currently lines 3012-3035). Immediately after that
method's closing line (after the `self._dot_after = self.after(...)` line, i.e. after line 3035),
add a new method on the same class:

```python
    def _show_chest_rect_overlay(self, ref_rect, offset_name):
        """Draw a topmost border-only rectangle over the game at the OCR crop
        position for the given chest field, so the owner can see exactly what
        will be read while nudging the D-Pad — mirrors _show_calibration_dot's
        Toplevel/after pattern but sized to the real crop, not a fixed dot."""
        import tkinter as tk
        x, y, w, h = coord_manager.to_region_dialog(*ref_rect)
        dx, dy = coord_manager.get_ui_offset(offset_name)
        x, y = x + dx, y + dy

        if not hasattr(self, '_chest_rect_win') or not self._chest_rect_win.winfo_exists():
            self._chest_rect_win = tk.Toplevel(self)
            self._chest_rect_win.overrideredirect(True)
            self._chest_rect_win.attributes('-topmost', True)
            self._chest_rect_win.attributes('-transparentcolor', 'black')
            self._chest_rect_canvas = tk.Canvas(self._chest_rect_win, bg='black',
                                                 highlightthickness=0)
            self._chest_rect_canvas.pack(fill="both", expand=True)

        self._chest_rect_win.geometry(f'{w}x{h}+{x}+{y}')
        self._chest_rect_canvas.delete("all")
        self._chest_rect_canvas.config(width=w, height=h)
        self._chest_rect_canvas.create_rectangle(1, 1, w - 1, h - 1, outline='red', width=2)
        self._chest_rect_win.deiconify()

        if hasattr(self, '_chest_rect_after'):
            self.after_cancel(self._chest_rect_after)
        self._chest_rect_after = self.after(3000, lambda: self._chest_rect_win.withdraw())
```

- [ ] **Step 5: Wire the overlay into dropdown selection and D-Pad presses**

In `main.py`, find `_tune_get_key` / `_tune_refresh_display` / `_tune_apply` (currently lines
4328-4339):
```python
        def _tune_get_key():
            return _TUNE_INTERNAL[self._tune_idx]

        def _tune_refresh_display():
            ox, oy = coord_manager.get_ui_offset(_tune_get_key())
            self._tune_display_lb.configure(text=f"X: {ox:+d}px   Y: {oy:+d}px")

        def _tune_apply(dx, dy):
            key = _tune_get_key()
            ox, oy = coord_manager.get_ui_offset(key)
            coord_manager.set_ui_offset(key, ox + dx, oy + dy)
            _tune_refresh_display()
```
Replace with (adds a lookup table from tuning key to its chest `REF_RECT`, and shows the overlay
whenever the active key is one of the two chest targets):
```python
        _CHEST_TUNE_RECTS = {
            "chest_sender": chest_reader.SENDER_REF_RECT,
            "chest_type": chest_reader.SOURCE_REF_RECT,
        }

        def _tune_get_key():
            return _TUNE_INTERNAL[self._tune_idx]

        def _tune_show_chest_overlay_if_relevant():
            key = _tune_get_key()
            if key in _CHEST_TUNE_RECTS:
                self._show_chest_rect_overlay(_CHEST_TUNE_RECTS[key], key)

        def _tune_refresh_display():
            ox, oy = coord_manager.get_ui_offset(_tune_get_key())
            self._tune_display_lb.configure(text=f"X: {ox:+d}px   Y: {oy:+d}px")
            _tune_show_chest_overlay_if_relevant()

        def _tune_apply(dx, dy):
            key = _tune_get_key()
            ox, oy = coord_manager.get_ui_offset(key)
            coord_manager.set_ui_offset(key, ox + dx, oy + dy)
            _tune_refresh_display()
```
`_tune_refresh_display()` is already called by `_tune_on_select` (dropdown change) and by
`_tune_apply` (every D-Pad press) and once at setup — so folding the overlay trigger into it covers
both "select a chest target" and "press an arrow" without touching those call sites.

`chest_reader` is currently only imported lazily, inside four different methods (`import
chest_reader` at lines 2431, 2441, 2484, 4025) — none of those run at class-definition time, so
`_CHEST_TUNE_RECTS` above would raise `NameError` if `chest_reader` isn't already imported when
`setup_calibration_tab` (or wherever this D-Pad block lives) executes. Add a top-level import
instead: find the existing top-of-file import block (near the other project module imports, e.g.
`from coord_manager import coord_manager`) and add:
```python
import chest_reader
```
Leave the four existing lazy `import chest_reader` lines exactly as they are — they become harmless
no-ops (Python caches modules), and removing them is unrelated cleanup outside this task's scope.

- [ ] **Step 6: Manual live verification**

Start the bot (`python main.py`), open the «Мой клан → Подарки» dialog in-game, go to Калибровка
tab, and confirm by eye:
- The D-Pad target dropdown now lists 6 items including «Имя игрока (сундуки)» and «Источник
  (сундуки)» (or their translated equivalents in the active language).
- Selecting «Источник (сундуки)» shows a red-bordered rectangle on top of the game, positioned over
  the «Источник:» line of the top gift card.
- Pressing any D-Pad arrow nudges the rectangle visibly and the X/Y label updates.
- The rectangle disappears after ~3 seconds of no input.
- Selecting one of the original 4 targets (e.g. «Отправка Картера») shows no rectangle (unchanged
  behavior).
- Open the СУНДУКИ tab and run one collection cycle — confirm the read chest type now matches the
  «Источник:» line, not the title line.
- Restart the bot — confirm the chest_sender/chest_type offsets persisted (X/Y label on reselecting
  the target shows the same non-zero values as before restart, if any were set).

Report the outcome of this manual pass back before considering the plan done.

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat(main): D-Pad tuning + live rect overlay for chest OCR fields"
```
