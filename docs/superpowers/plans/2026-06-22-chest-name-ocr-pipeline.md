# Chest Sender-Name OCR Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the client bot's player-name OCR so stylized/diacritic nicknames (e.g. "Marisha"-type names) survive intact instead of being eaten down to a single letter or misread as dictionary-corrected garbage, and make the fix actually reach packaged client builds (not just the dev machine).

**Architecture:** Three independent, sequential fixes to the same OCR pipeline in `chest_reader.py`: (1) a new shared `tesseract_setup.py` module replaces the dev-machine-only hardcoded Tesseract path in `chest_reader.py`/`navigator.py` with proper frozen/dev resolution (mirroring the already-correct `roy/exchange_reader.py` pattern); (2) `clean_name()` stops its destructive letter-eating trailing-strip loop, keeping only safe digit-group stripping; (3) `read_sender_name()` gets its own literal-reading OCR config (dictionaries off, extra script coverage) via new optional parameters threaded through `ocr_text()`/`read_fixed_field()` — `read_chest_type()` is explicitly left untouched. A final task adds the new language data files to the distributed `tesseract_bin/` and updates the locked-composition checklist in `CLAUDE.md`.

**Tech Stack:** Python 3.13, pytest, pytesseract/Tesseract OCR, OpenCV — client bot (not the web/server side).

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-06-22-chest-name-ocr-pipeline-design.md`
- The crop zones `SENDER_REF_RECT`/`SOURCE_REF_RECT` are calibrated and **must not be touched** by this plan.
- `read_chest_type()` keeps its current defaults (`lang='rus+eng'`, no extra dictionary-disabling config) — only `read_sender_name()` gets the new literal-reading treatment.
- `tournament_reader.py` and `roy/exchange_reader.py` are explicitly out of scope — do not modify them.
- `script/Latin.traineddata` must be downloaded from `https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/script/Latin.traineddata` and placed at `tesseract_bin/tessdata/script/Latin.traineddata` (the `script/` subdirectory is required — Tesseract resolves the language code `script/Latin` by that exact path).
- `rus.traineddata` must be copied from `C:\Program Files\Tesseract-OCR\tessdata\rus.traineddata` (the dev machine's existing install) to `tesseract_bin/tessdata/rus.traineddata` — same file already used at runtime via `lang='rus+eng'`, just never previously included in the distributed package.

---

### Task 1: Shared portable-Tesseract-path resolver

**Files:**
- Create: `tesseract_setup.py` (project root)
- Modify: `chest_reader.py:27` (replace the hardcoded `tesseract_cmd` line)
- Modify: `navigator.py:21-22` (replace the hardcoded `tesseract_cmd` line)
- Test: `test_tesseract_setup.py` (new file, project root)

**Interfaces:**
- Produces: `tesseract_setup.find_tesseract() -> str | None` and
  `tesseract_setup.configure_pytesseract(pytesseract_module, log=print) -> bool`. Task 3 does not
  depend on this task's interfaces (different concern), but both land in the same files so this
  task must be committed first to avoid `chest_reader.py` edit conflicts.

- [ ] **Step 1: Write the failing tests**

Create `test_tesseract_setup.py`:

```python
import os
import sys
import tesseract_setup as ts


def test_find_tesseract_frozen_returns_bundled_path_when_present(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    exe_dir = tmp_path
    bin_dir = exe_dir / "tesseract_bin"
    bin_dir.mkdir()
    bundled = bin_dir / "tesseract.exe"
    bundled.write_text("fake exe")
    monkeypatch.setattr(sys, 'executable', str(exe_dir / "TotalHunter.exe"))

    result = ts.find_tesseract()
    assert result == str(bundled)


def test_find_tesseract_frozen_returns_none_when_bundled_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / "TotalHunter.exe"))

    assert ts.find_tesseract() is None


def test_find_tesseract_dev_uses_shutil_which_first(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(ts.shutil, 'which', lambda name: r'C:\PATH\tesseract.exe')

    assert ts.find_tesseract() == r'C:\PATH\tesseract.exe'


def test_find_tesseract_dev_falls_back_to_standard_paths(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(ts.shutil, 'which', lambda name: None)
    monkeypatch.setattr(ts.os.path, 'isfile',
                        lambda p: p == r'C:\Program Files\Tesseract-OCR\tesseract.exe')

    assert ts.find_tesseract() == r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def test_find_tesseract_dev_returns_none_when_nothing_found(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(ts.shutil, 'which', lambda name: None)
    monkeypatch.setattr(ts.os.path, 'isfile', lambda p: False)

    assert ts.find_tesseract() is None


class _FakePytesseractModule:
    class pytesseract:
        tesseract_cmd = None


def test_configure_pytesseract_sets_cmd_when_found(monkeypatch):
    monkeypatch.setattr(ts, 'find_tesseract', lambda: r'C:\found\tesseract.exe')
    fake = _FakePytesseractModule()

    result = ts.configure_pytesseract(fake)

    assert result is True
    assert fake.pytesseract.tesseract_cmd == r'C:\found\tesseract.exe'


def test_configure_pytesseract_logs_and_returns_false_when_not_found(monkeypatch):
    monkeypatch.setattr(ts, 'find_tesseract', lambda: None)
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    fake = _FakePytesseractModule()
    logged = []

    result = ts.configure_pytesseract(fake, log=logged.append)

    assert result is False
    assert fake.pytesseract.tesseract_cmd is None
    assert len(logged) == 1
    assert "Tesseract OCR не найден" in logged[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\BattleBot && python -m pytest test_tesseract_setup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tesseract_setup'`

- [ ] **Step 3: Create `tesseract_setup.py`**

```python
"""tesseract_setup.py — resolves the Tesseract binary path: portable tesseract_bin/
next to the EXE in a frozen build, system PATH/standard install dirs in dev mode.

Single source of truth — before this module existed, chest_reader.py and navigator.py
hardcoded the dev-machine path directly (C:\\Program Files\\Tesseract-OCR\\...), which
meant the portable tesseract_bin shipped to clients was never actually used by either
module's OCR calls.
"""
import os
import shutil
import sys


def find_tesseract():
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(os.path.dirname(sys.executable), "tesseract_bin", "tesseract.exe")
        return bundled if os.path.isfile(bundled) else None

    found = shutil.which("tesseract")
    if found:
        return found
    for path in [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]:
        if os.path.isfile(path):
            return path
    return None


def configure_pytesseract(pytesseract_module, log=print):
    path = find_tesseract()
    if path:
        pytesseract_module.pytesseract.tesseract_cmd = path
        return True
    if getattr(sys, 'frozen', False):
        log("КРИТИЧЕСКАЯ ОШИБКА: tesseract_bin не найден рядом с TotalHunter.exe. "
            "Проверьте целостность сборки — папка tesseract_bin должна быть рядом с EXE.")
    else:
        log("КРИТИЧЕСКАЯ ОШИБКА: Tesseract OCR не найден на ПК. "
            "Установите Tesseract для работы бота. "
            "Скачайте: https://github.com/UB-Mannheim/tesseract/wiki")
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\BattleBot && python -m pytest test_tesseract_setup.py -v`
Expected: PASS (7/7)

- [ ] **Step 5: Wire it into `chest_reader.py`**

Replace line 27:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```
with:
```python
from tesseract_setup import configure_pytesseract
configure_pytesseract(pytesseract)
```

- [ ] **Step 6: Wire it into `navigator.py`**

Replace lines 21-22:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```
with:
```python
import pytesseract
from tesseract_setup import configure_pytesseract
configure_pytesseract(pytesseract)
```

- [ ] **Step 7: Run the existing chest_reader + navigator test suites to check no regressions**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py test_coastal_snake.py -v`
Expected: all PASS — these tests run on the dev machine where Tesseract is on a standard install
path, so `configure_pytesseract` resolves the same `C:\Program Files\Tesseract-OCR\tesseract.exe`
it did before, just via the new resolver instead of a hardcoded literal.

- [ ] **Step 8: Commit**

```bash
git add tesseract_setup.py test_tesseract_setup.py chest_reader.py navigator.py
git commit -m "feat(ocr): portable Tesseract path resolution for chest_reader/navigator (frozen->tesseract_bin, dev->autodetect)"
```

---

### Task 2: Safe `clean_name()` — stop eating letters of space-separated names

**Files:**
- Modify: `chest_reader.py:100-112` (`clean_name`)
- Test: `test_chest_reader.py`

**Interfaces:**
- Produces: `clean_name(text: str) -> str` — same signature as before, new behavior. Used by
  `read_fixed_field()` (unchanged call site, `chest_reader.py:121`).

- [ ] **Step 1: Write the failing tests**

Add to `test_chest_reader.py`:

```python
def test_clean_name_preserves_space_separated_stylized_name():
    assert cr.clean_name("M A R I S H A") == "M A R I S H A"


def test_clean_name_strips_trailing_digit_group():
    assert cr.clean_name("PlayerName 123") == "PlayerName"


def test_clean_name_strips_multiple_trailing_digit_groups():
    assert cr.clean_name("PlayerName 12 3") == "PlayerName"


def test_clean_name_strips_trailing_punctuation():
    assert cr.clean_name("Tess'") == "Tess"


def test_clean_name_strips_leading_clan_tag():
    assert cr.clean_name("[ABC] Niduel") == "Niduel"
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -k clean_name -v`
Expected: `test_clean_name_preserves_space_separated_stylized_name` and
`test_clean_name_strips_multiple_trailing_digit_groups` FAIL (current code collapses the stylized
name down to `"M"` and only strips one digit group, not chained ones); the other three already pass
with the old implementation.

- [ ] **Step 3: Rewrite `clean_name()`**

Replace `chest_reader.py:100-112`:

```python
def clean_name(text):
    """Strip OCR artifacts from a player name. Same 4-stage cleanup as
    tournament_reader.clean_name — duplicated here to keep this module
    self-contained, per the existing reader-module convention."""
    text = re.sub(r'^\[.*?\]\s*', '', text)
    text = re.sub(r'\s+\S{1,3}$', '', text)
    while True:
        stripped = re.sub(r'\s+(?:\d{1,3}|\S{1})$', '', text)
        if stripped == text:
            break
        text = stripped
    text = re.sub(r'[^\w]+$', '', text, flags=re.UNICODE)
    return text.strip()
```

with:

```python
def clean_name(text):
    """Strip OCR artifacts from a player name. Only strips a leading [clan tag]
    prefix and trailing digit groups (power-level/tag noise) — never strips trailing
    letters, since stylized space-separated names (e.g. "M A R I S H A") must survive
    intact rather than being eaten down to a single character by an overly aggressive
    trailing-token strip."""
    text = re.sub(r'^\[.*?\]\s*', '', text)
    text = re.sub(r'(?:\s+\d{1,3})+$', '', text)
    text = re.sub(r'[^\w]+$', '', text, flags=re.UNICODE)
    return text.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -k clean_name -v`
Expected: PASS (5/5)

- [ ] **Step 5: Run the full `test_chest_reader.py` file to check no regressions**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -v`
Expected: all PASS, including `test_read_sender_name_applies_clean_name_artifact_stripping` and
the live-fixture `test_read_top_row_on_fixture` (expects sender `"Gray Cardinal"` — plain ASCII,
unaffected by this change).

- [ ] **Step 6: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "fix(chests): clean_name no longer eats letters of space-separated stylized names, only strips trailing digit groups"
```

---

### Task 3: Literal diacritic reading for `read_sender_name` only

**Files:**
- Modify: `chest_reader.py:94-130` (`ocr_text`, `read_fixed_field`, `read_sender_name`)
- Test: `test_chest_reader.py`

**Interfaces:**
- Consumes: `clean_name()` from Task 2 (unchanged call site).
- Produces: `ocr_text(roi, psm=7, lang='rus+eng', extra_config='')`,
  `read_fixed_field(frame, ref_rect, offset_name=None, lang='rus+eng', extra_config='')` — both
  gain new optional keyword parameters with backward-compatible defaults, so `read_chest_type()`
  needs no changes at all to keep its current behavior.

This task assumes Task 1 has already landed (the `tesseract_setup` import sits above the functions
this task edits, no line-number conflict) and Task 2 has already landed (`clean_name` body is
already the new 3-line version — this task does not touch `clean_name`, just calls it the same way).

- [ ] **Step 1: Write the failing tests**

Add to `test_chest_reader.py`:

```python
def test_read_sender_name_uses_literal_diacritic_config(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_sender_name(frame)

    assert captured["lang"] == "rus+eng+script/Latin"
    assert captured["extra_config"] == "-c load_system_dawg=0 -c load_freq_dawg=0"


def test_read_chest_type_keeps_default_ocr_config(monkeypatch):
    captured = {}
    monkeypatch.setattr(cr.coord_manager, "to_region_dialog", lambda x, y, w, h: (0, 0, 5, 5))

    def fake_ocr_text(roi, **kwargs):
        captured.update(kwargs)
        return ""
    monkeypatch.setattr(cr, "ocr_text", fake_ocr_text)

    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.read_chest_type(frame)

    assert captured["lang"] == "rus+eng"
    assert captured["extra_config"] == ""


def test_ocr_text_appends_extra_config_to_psm_flag(monkeypatch):
    captured = {}

    def fake_image_to_string(image, config, lang, timeout):
        captured["config"] = config
        captured["lang"] = lang
        return ""
    monkeypatch.setattr(cr.pytesseract, "image_to_string", fake_image_to_string)

    roi = np.zeros((10, 10, 3), dtype=np.uint8)
    cr.ocr_text(roi, lang="rus+eng+script/Latin", extra_config="-c load_system_dawg=0")

    assert captured["config"] == "--psm 7 -c load_system_dawg=0"
    assert captured["lang"] == "rus+eng+script/Latin"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -k "literal_diacritic or default_ocr_config or appends_extra_config" -v`
Expected: FAIL — `read_sender_name`/`read_fixed_field`/`ocr_text` don't accept/forward `lang`/`extra_config` yet (`captured` will be missing the keys, or `ocr_text` raises `TypeError` on the unexpected `extra_config` kwarg).

- [ ] **Step 3: Update `ocr_text`, `read_fixed_field`, `read_sender_name`**

Replace `chest_reader.py:94-97`:

```python
def ocr_text(roi, psm=7, lang='rus+eng'):
    processed = preprocess_for_ocr(roi)
    config = f'--psm {psm}'
    return pytesseract.image_to_string(processed, config=config, lang=lang, timeout=5).strip()
```

with:

```python
def ocr_text(roi, psm=7, lang='rus+eng', extra_config=''):
    processed = preprocess_for_ocr(roi)
    config = f'--psm {psm} {extra_config}'.strip()
    return pytesseract.image_to_string(processed, config=config, lang=lang, timeout=5).strip()
```

Replace `chest_reader.py:115-129`:

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

with:

```python
def read_fixed_field(frame, ref_rect, offset_name=None, lang='rus+eng', extra_config=''):
    x, y, w, h = coord_manager.to_region_dialog(*ref_rect)
    if offset_name is not None:
        dx, dy = coord_manager.get_ui_offset(offset_name)
        x, y = x + dx, y + dy
    roi = frame[y:y + h, x:x + w]
    return clean_name(ocr_text(roi, lang=lang, extra_config=extra_config))


# Player name: stylized/unpredictable — dictionaries only hurt here (they force
# Tesseract to "correct" unfamiliar glyph shapes into known dictionary words, which is
# exactly what splits a name like "Marisha" into single dictionary-shaped letters).
# Disabling DAWG + the broad script/Latin coverage reads diacritics literally instead.
SENDER_OCR_LANG = 'rus+eng+script/Latin'
SENDER_OCR_CONFIG = '-c load_system_dawg=0 -c load_freq_dawg=0'


def read_sender_name(frame):
    return read_fixed_field(frame, SENDER_REF_RECT, "chest_sender",
                            lang=SENDER_OCR_LANG, extra_config=SENDER_OCR_CONFIG)


def read_chest_type(frame):
    return read_fixed_field(frame, SOURCE_REF_RECT, "chest_type")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -k "literal_diacritic or default_ocr_config or appends_extra_config" -v`
Expected: PASS (3/3)

- [ ] **Step 5: Run the full `test_chest_reader.py` file to check no regressions**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -v`
Expected: all PASS, including `test_read_top_row_on_fixture` — this one calls the REAL Tesseract
(no monkeypatch on `ocr_text` in that test) with the new `SENDER_OCR_LANG`/`SENDER_OCR_CONFIG`. If
it fails because `script/Latin` isn't available yet on this dev machine's system Tesseract
install, that's expected until Task 4 makes the language data available — note this in your task
report rather than treating it as a regression; re-run this specific test after Task 4 lands to
confirm it then passes.

- [ ] **Step 6: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chests): literal diacritic OCR (script/Latin + disabled dictionaries) for player names only, chest-type OCR unchanged"
```

---

### Task 4: Add language data to distributed `tesseract_bin` + update the locked-composition checklist

**Files:**
- Add (not git-tracked — `tesseract_bin/` is in `.gitignore`): `tesseract_bin/tessdata/rus.traineddata`, `tesseract_bin/tessdata/script/Latin.traineddata`
- Modify: `CLAUDE.md` (the tesseract_bin checklist in section "0. ПРОТОКОЛ", the line listing the reference composition)

**Interfaces:** None — this task is files-on-disk + one doc edit, no code.

- [ ] **Step 1: Copy `rus.traineddata` into the portable bundle**

Run:
```bash
cp "C:\Program Files\Tesseract-OCR\tessdata\rus.traineddata" "C:\BattleBot\tesseract_bin\tessdata\rus.traineddata"
```
Expected: file appears at `C:\BattleBot\tesseract_bin\tessdata\rus.traineddata`, size 3 861 738 bytes.

- [ ] **Step 2: Download `script/Latin.traineddata` into the portable bundle**

Run:
```bash
mkdir -p "C:\BattleBot\tesseract_bin\tessdata\script"
curl -sL "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/script/Latin.traineddata" -o "C:\BattleBot\tesseract_bin\tessdata\script\Latin.traineddata" --max-time 90
```
Expected: file appears at `C:\BattleBot\tesseract_bin\tessdata\script\Latin.traineddata`, size
89 384 811 bytes.

- [ ] **Step 3: Verify the bundled tesseract.exe recognizes the new languages**

Run:
```bash
"C:\BattleBot\tesseract_bin\tesseract.exe" --tessdata-dir "C:\BattleBot\tesseract_bin\tessdata" --list-langs
```
Expected output: a 3-language list containing `eng`, `rus`, and `script\Latin` (Windows path
separator in the listing, the actual `-l` value is `script/Latin` with a forward slash).

- [ ] **Step 4: Verify `tesseract.exe --version` still works (per CLAUDE.md's mandatory pre-build check)**

Run: `& "C:\BattleBot\tesseract_bin\tesseract.exe" --version`
Expected: prints `tesseract v5.x.x`, exit code 0.

- [ ] **Step 5: Update `CLAUDE.md`'s locked tesseract_bin composition line**

In `CLAUDE.md`, find this line (in the "🔒 ОБЯЗАТЕЛЬНЫЙ ЧЕКЛИСТ ПЕРЕД СБОРКОЙ" section):

```
# 3. Эталонный состав tesseract_bin: 56 DLL + tessdata/eng.traineddata = 72 МБ
# Источник: C:\Program Files\Tesseract-OCR\ (все *.dll) + tessdata\eng.traineddata
```

Replace it with:

```
# 3. Эталонный состав tesseract_bin: 56 DLL + tessdata/{eng,rus}.traineddata +
#    tessdata/script/Latin.traineddata = ~165 МБ
# Источник: C:\Program Files\Tesseract-OCR\ (все *.dll + eng/rus.traineddata)
#           + https://github.com/tesseract-ocr/tessdata_fast (script/Latin.traineddata)
```

- [ ] **Step 6: Re-run the chest_reader live-fixture test now that the dev machine's system Tesseract still has `script/Latin` available too**

This step only matters if Task 3's Step 5 skipped the live-fixture assertion due to a missing
language on the system Tesseract install. If the dev machine's system Tesseract
(`C:\Program Files\Tesseract-OCR\`) doesn't have `script/Latin.traineddata` in its own
`tessdata\script\` folder (separate from the portable `tesseract_bin` copy — the dev machine's
system install is what `test_read_top_row_on_fixture` actually exercises, via
`tesseract_setup.find_tesseract()`'s dev-mode path), copy it there too:

```bash
mkdir -p "C:\Program Files\Tesseract-OCR\tessdata\script"
cp "C:\BattleBot\tesseract_bin\tessdata\script\Latin.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\script\Latin.traineddata"
```

Then run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -v`
Expected: all PASS, including `test_read_top_row_on_fixture`.

- [ ] **Step 7: Commit the CLAUDE.md change**

(The `tesseract_bin/` files themselves are gitignored and not committed — only the doc update is.)

```bash
git add CLAUDE.md
git commit -m "docs: update tesseract_bin reference composition (+rus, +script/Latin for literal diacritic name OCR)"
```

---

## Self-Review Notes

- Spec coverage: A (Task 1), B (Task 2), C (Task 3), D (Task 4) — all four spec sections have a
  task. Out-of-scope items (label leakage, garbage filtering, `tournament_reader.py`,
  `roy/exchange_reader.py`, `read_chest_type` config) are explicitly not touched by any task.
- Type/signature consistency: `ocr_text(roi, psm=7, lang='rus+eng', extra_config='')` (Task 3,
  Step 3) matches the `lang=`/`extra_config=` keyword names used in `read_fixed_field` (same step)
  and in the Task 3 tests (Step 1). `SENDER_OCR_LANG`/`SENDER_OCR_CONFIG` constant names match
  between the code change and the spec.
- No placeholders — every step has literal code/commands, no "add tests for the above" stubs.

## Deployment

This is a client-bot change (`chest_reader.py`, `navigator.py`, `tesseract_setup.py`,
`tesseract_bin/`), not a web/server change — per `CLAUDE.md`, deployment means a new client
release (`build_release.py` → ZIP → GitHub Release → `/admin/version/update`), which happens
**only on the owner's explicit instruction**, not automatically after this plan's tasks complete.
Do not build or release without being told to.
