# Chest Sender-Name OCR — Full 19-Language Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the chest sender-name OCR (shipped in v1.8.2 with Latin-diacritic support) to cover all 19 languages the bot's own UI already supports (`main.py::LANGS`), so player nicknames in Cyrillic, Arabic, Japanese, Chinese (both scripts), and Korean are read correctly instead of only Latin-diacritic names.

**Architecture:** One constant change in `chest_reader.py` (`SENDER_OCR_LANG` gains 5 more language codes) plus the corresponding language-data files added to the distributed `tesseract_bin/` and to the dev machine's system Tesseract install (so the live-fixture test in `test_chest_reader.py` can genuinely exercise the new languages, same pattern as the v1.8.2 plan's Task 4). `read_chest_type()` and its `rus+eng` default are untouched — `rus.traineddata` stays in `tesseract_bin` for that reason.

**Tech Stack:** Python 3.13, pytest, pytesseract/Tesseract OCR — client bot (not web/server).

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-06-22-chest-name-ocr-19-languages-design.md`
- `rus.traineddata` **must stay** in `tesseract_bin/tessdata/` — `read_chest_type()` and `ocr_text()`'s default (`lang='rus+eng'`) still depend on it. Do not delete it.
- New `SENDER_OCR_LANG` value (exact, verified live): `'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'`
- `SENDER_OCR_CONFIG` is unchanged.
- `read_chest_type()` is unchanged — out of scope, same as the prior plan.
- New files, exact sizes (already downloaded and verified during brainstorming, byte sizes confirmed live): `script/Cyrillic.traineddata` = 29,252,466 bytes; `ara.traineddata` = 1,432,056 bytes; `jpn.traineddata` = 2,471,260 bytes; `chi_sim.traineddata` = 2,469,156 bytes; `chi_tra.traineddata` = 2,366,642 bytes; `kor.traineddata` = 1,677,415 bytes.

---

### Task 1: Update `SENDER_OCR_LANG` and its test

**Files:**
- Modify: `chest_reader.py:126` (`SENDER_OCR_LANG`)
- Modify: `test_chest_reader.py:487` (`test_read_sender_name_uses_literal_diacritic_config`)

**Interfaces:** None new — this only changes the value of an existing constant already consumed by `read_sender_name()` (unchanged call site at `chest_reader.py:131-132`).

- [ ] **Step 1: Update the test's expected value (TDD — this makes the test fail first)**

In `test_chest_reader.py`, replace line 487:

```python
    assert captured["lang"] == "rus+eng+script/Latin"
```

with:

```python
    assert captured["lang"] == "eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor"
```

- [ ] **Step 2: Run the test to verify it fails against the old constant**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py::test_read_sender_name_uses_literal_diacritic_config -v`
Expected: FAIL — `captured["lang"]` is still `"rus+eng+script/Latin"`.

- [ ] **Step 3: Update the constant**

In `chest_reader.py`, replace line 126:

```python
SENDER_OCR_LANG = 'rus+eng+script/Latin'
```

with:

```python
SENDER_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py::test_read_sender_name_uses_literal_diacritic_config -v`
Expected: PASS

- [ ] **Step 5: Run the full `test_chest_reader.py` file**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -v`
Expected: all PASS except possibly `test_read_top_row_on_fixture` — that one calls REAL Tesseract
and will only fully exercise the new languages once Task 2 installs the language-data files on
this dev machine's system Tesseract. If it fails purely because a new language is unavailable (not
for any other reason), that is expected at this point — note it in your report, do not treat it as
a regression in this task's own code, and Task 2 will resolve it.

- [ ] **Step 6: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chests): extend sender-name OCR to all 19 bot-supported languages (Cyrillic, Arabic, Japanese, Chinese x2, Korean)"
```

---

### Task 2: Distribute the new language files + update CLAUDE.md

**Files:**
- Add (not git-tracked — `tesseract_bin/` is in `.gitignore`): `tesseract_bin/tessdata/script/Cyrillic.traineddata`, `tesseract_bin/tessdata/ara.traineddata`, `tesseract_bin/tessdata/jpn.traineddata`, `tesseract_bin/tessdata/chi_sim.traineddata`, `tesseract_bin/tessdata/chi_tra.traineddata`, `tesseract_bin/tessdata/kor.traineddata`
- Modify: `CLAUDE.md` (the tesseract_bin reference-composition checklist line, last updated in the v1.8.2 plan)

**Interfaces:** None — files + one doc edit, no code.

- [ ] **Step 1: Verify the 6 new files already exist in `tesseract_bin/tessdata/` with the correct sizes**

These were already downloaded during the design/brainstorm phase for this feature. Run:

```bash
ls -la "C:\BattleBot\tesseract_bin\tessdata\script\Cyrillic.traineddata" \
       "C:\BattleBot\tesseract_bin\tessdata\ara.traineddata" \
       "C:\BattleBot\tesseract_bin\tessdata\jpn.traineddata" \
       "C:\BattleBot\tesseract_bin\tessdata\chi_sim.traineddata" \
       "C:\BattleBot\tesseract_bin\tessdata\chi_tra.traineddata" \
       "C:\BattleBot\tesseract_bin\tessdata\kor.traineddata"
```

Expected sizes (bytes): `script/Cyrillic.traineddata`=29252466, `ara.traineddata`=1432056,
`jpn.traineddata`=2471260, `chi_sim.traineddata`=2469156, `chi_tra.traineddata`=2366642,
`kor.traineddata`=1677415.

If any file is missing or the wrong size, re-download it from
`https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/<name>.traineddata` (note:
`script/Cyrillic.traineddata` needs its `script/` subdirectory under `tessdata/`, same convention
as `script/Latin.traineddata` already there from the previous release).

- [ ] **Step 2: Confirm `rus.traineddata` is still present (must NOT be deleted)**

Run: `ls -la "C:\BattleBot\tesseract_bin\tessdata\rus.traineddata"`
Expected: file exists, size 3,861,738 bytes (unchanged from the previous release — `read_chest_type()` still needs it).

- [ ] **Step 3: Verify the bundled tesseract.exe recognizes all 9 languages now**

Run:
```bash
"C:\BattleBot\tesseract_bin\tesseract.exe" --tessdata-dir "C:\BattleBot\tesseract_bin\tessdata" --list-langs
```
Expected: a 9-language list: `ara`, `chi_sim`, `chi_tra`, `eng`, `jpn`, `kor`, `rus`,
`script\Cyrillic`, `script\Latin`.

- [ ] **Step 4: Mirror the new files onto the dev machine's system Tesseract install**

This makes the live-fixture test in `test_chest_reader.py` (which exercises the real, non-mocked
system Tesseract, not the portable bundle) actually able to use the new languages — same reasoning
as the previous release's Task 4. A prior session needed elevated permissions for this kind of
copy into `C:\Program Files\...`; if a plain copy fails with a permission error, retry via an
elevated PowerShell invocation (`Start-Process -Verb RunAs`) rather than skipping the step:

```bash
mkdir -p "C:\Program Files\Tesseract-OCR\tessdata\script"
cp "C:\BattleBot\tesseract_bin\tessdata\script\Cyrillic.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\script\Cyrillic.traineddata"
cp "C:\BattleBot\tesseract_bin\tessdata\ara.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\ara.traineddata"
cp "C:\BattleBot\tesseract_bin\tessdata\jpn.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\jpn.traineddata"
cp "C:\BattleBot\tesseract_bin\tessdata\chi_sim.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\chi_sim.traineddata"
cp "C:\BattleBot\tesseract_bin\tessdata\chi_tra.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\chi_tra.traineddata"
cp "C:\BattleBot\tesseract_bin\tessdata\kor.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\kor.traineddata"
```

- [ ] **Step 5: Run the full `test_chest_reader.py` suite to confirm the live fixture now genuinely passes**

Run: `cd C:\BattleBot && python -m pytest test_chest_reader.py -v`
Expected: all PASS, including `test_read_top_row_on_fixture`.

- [ ] **Step 6: Update `CLAUDE.md`'s tesseract_bin reference-composition line**

Find this block in `CLAUDE.md` (in the "🔒 ОБЯЗАТЕЛЬНЫЙ ЧЕКЛИСТ ПЕРЕД СБОРКОЙ" section, set by the
previous release's plan):

```
# 3. Эталонный состав tesseract_bin: 56 DLL + tessdata/{eng,rus}.traineddata +
#    tessdata/script/Latin.traineddata = ~165 МБ
# Источник: C:\Program Files\Tesseract-OCR\ (все *.dll + eng/rus.traineddata)
#           + https://github.com/tesseract-ocr/tessdata_fast (script/Latin.traineddata)
```

Replace it with:

```
# 3. Эталонный состав tesseract_bin: 56 DLL + tessdata/{eng,rus,ara,jpn,chi_sim,chi_tra,kor}.traineddata
#    + tessdata/script/{Latin,Cyrillic}.traineddata = ~205 МБ (полное покрытие 19 языков бота)
# Источник: C:\Program Files\Tesseract-OCR\ (все *.dll + eng/rus.traineddata)
#           + https://github.com/tesseract-ocr/tessdata_fast (script/Latin, script/Cyrillic,
#             ara, jpn, chi_sim, chi_tra, kor)
```

- [ ] **Step 7: Commit the CLAUDE.md change**

(The `tesseract_bin/` files themselves are gitignored and not committed — only the doc update is.)

```bash
git add CLAUDE.md
git commit -m "docs: update tesseract_bin reference composition for full 19-language sender-name OCR coverage"
```

---

## Self-Review Notes

- Spec coverage: the spec's "Языки → файлы" table maps to Task 1 (code constant) + Task 2 (data
  files); "Изменение кода" maps to Task 1; "Дистрибутив tesseract_bin" maps to Task 2; "Тестирование"
  maps to Task 1 Step 1/Task 2 Step 5. Nothing in the spec lacks a task.
- Placeholder scan: none — every step has literal code/commands/expected output.
- Type/value consistency: `SENDER_OCR_LANG`'s new literal string is identical in Task 1's Step 1
  (test) and Step 3 (implementation) — copy-paste identical, no risk of a typo mismatch between them.

## Deployment

This is a client-bot change. Per `CLAUDE.md`, building and releasing a new ZIP happens **only on
the owner's explicit instruction** — do not build or release automatically after these tasks land.
