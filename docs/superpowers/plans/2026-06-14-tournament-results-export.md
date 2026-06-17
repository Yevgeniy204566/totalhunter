# Tournament Results Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tournament_reader.py`, a standalone CLI tool that scrolls the in-game "Статистика" (tournament) dialog, OCRs each row (place, name, points) plus the pinned "own row", and POSTs the collected leaderboard to `{api_url}/api/v1/tournaments/import`.

**Architecture:** Two-stage screen capture (full `monitors[1]` grab → HSV/contour bbox autodetect → crop to dialog ROI) feeds a geometry-based row-pitch detector (gradient peak detection with edge/merge filtering) that slices the dialog into 4 visible rows. Each row is split into name/points sub-crops via fixed fractional coordinates, OCR'd with `pytesseract`, and cleaned with regex. Places are computed by anchor-matching on points values across scroll frames (no OCR of place numbers for the scrolling list). A separate static ROI handles the pinned "own row" (place IS OCR'd here, with a different threshold). The main loop scrolls via `pyautogui.scroll(-2)` with anti-detect pauses until `cv2.absdiff` detects no change (end of list), then POSTs the result to the website API, with local-JSON fallback on failure.

**Tech Stack:** Python 3.13, OpenCV (`cv2`), NumPy, `mss` (screen capture), `pyautogui` (scroll), `pytesseract` (OCR, `rus+eng`), `requests` (HTTP POST), `pytest` + `monkeypatch` (TDD).

---

## File Structure

- **Create:** `tournament_reader.py` (root) — all functions, single module, constants/imports defined in Task 1 and used by all subsequent tasks.
- **Create:** `test_tournament_reader.py` (root) — all tests, using `Турнир.png` fixture via `cv2.imdecode(np.fromfile(...))`.
- **Create:** `tournament_config.example.json` (root, committed template).
- **Modify:** `.gitignore` — add `tournament_config.json` (real config with secrets, not committed).

All 14 tasks below build up `tournament_reader.py` and `test_tournament_reader.py` incrementally. Constants and imports are established once in Task 1 and referenced (not redefined) by later tasks.

---

### Task 1: Project setup — config loader, constants, imports

**Files:**
- Create: `tournament_reader.py`
- Create: `tournament_config.example.json`
- Modify: `.gitignore`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Create `test_tournament_reader.py` with this initial content:

```python
import os
import json
import pytest
import tournament_reader as tr


def test_load_config_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tr, "CONFIG_PATH", os.path.join(str(tmp_path), "tournament_config.json"))
    with pytest.raises(FileNotFoundError) as exc_info:
        tr.load_config()
    assert "tournament_config.example.json" in str(exc_info.value)


def test_load_config_missing_keys_raises(tmp_path, monkeypatch):
    config_path = os.path.join(str(tmp_path), "tournament_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"api_url": "https://api.total-hunter.com"}, f)
    monkeypatch.setattr(tr, "CONFIG_PATH", config_path)
    with pytest.raises(ValueError) as exc_info:
        tr.load_config()
    assert "api_token" in str(exc_info.value)


def test_load_config_valid(tmp_path, monkeypatch):
    config_path = os.path.join(str(tmp_path), "tournament_config.json")
    data = {
        "api_url": "https://api.total-hunter.com",
        "api_token": "secret123",
        "alliance_tag": "K229",
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    monkeypatch.setattr(tr, "CONFIG_PATH", config_path)
    result = tr.load_config()
    assert result == data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tournament_reader'` (or `AttributeError` if the file exists but is empty).

- [ ] **Step 3: Write minimal implementation**

Create `tournament_reader.py`:

```python
import os
import re
import json
import time
import random
import datetime

import cv2
import numpy as np
import mss
import pyautogui
import pytesseract
import requests

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Dialog detection ---
DIALOG_HSV_LOWER = (10, 20, 150)
DIALOG_HSV_UPPER = (40, 120, 255)

# --- Row pitch detection ---
PEAK_GRADIENT_THRESHOLD = 30
PEAK_MERGE_DIST = 3
PEAK_EDGE_MARGIN = 5
NUM_VISIBLE_ROWS = 4
STARTING_RANK = 1

# --- Per-row crop fractions (of row width/height) ---
NAME_X_FRAC = (0.29, 0.56)
NAME_Y_FRAC = (0.05, 0.42)
PTS_X_FRAC = (0.74, 0.98)
PTS_Y_FRAC = (0.25, 0.75)

# --- Own row (pinned) ---
OWN_ROW_Y_FRAC = (0.805, 1.0)
PLACE_X_FRAC = (0.0, 0.07)
PLACE_Y_FRAC = (0.15, 0.70)

# --- End-of-list detection ---
SCROLLBAR_FRAC = 0.05
END_DIFF_THRESHOLD = 2.0

# --- OCR ---
OCR_THRESHOLD = 150
PLACE_OCR_THRESHOLD = 130

# --- Config / API ---
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tournament_config.json')
API_IMPORT_PATH = '/api/v1/tournaments/import'


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"Конфигурация не найдена: {CONFIG_PATH}\n"
            f"Скопируйте tournament_config.example.json в tournament_config.json и заполните значения."
        )
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    for key in ('api_url', 'api_token', 'alliance_tag'):
        if key not in config:
            raise ValueError(f"В конфигурации отсутствует обязательный ключ: {key}")
    return config
```

Create `tournament_config.example.json`:

```json
{
  "api_url": "https://api.total-hunter.com",
  "api_token": "REPLACE_WITH_YOUR_TOKEN",
  "alliance_tag": "K229"
}
```

Modify `.gitignore` — add a new line at the end:

```
tournament_config.json
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py tournament_config.example.json test_tournament_reader.py .gitignore
git commit -m "feat: tournament_reader config loader + constants"
```

---

### Task 2: Dialog bbox detection + crop

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def _load_fixture():
    return cv2.imdecode(np.fromfile("Турнир.png", dtype=np.uint8), cv2.IMREAD_COLOR)


def test_detect_dialog_bbox():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    assert bbox == (578, 268, 766, 546)


def test_crop_dialog():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    assert dialog.shape[:2] == (546, 766)
```

Add the import for `cv2`/`np` at top of `test_tournament_reader.py` (if not already present):

```python
import cv2
import numpy as np
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k bbox`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'detect_dialog_bbox'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def detect_dialog_bbox(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, DIALOG_HSV_LOWER, DIALOG_HSV_UPPER)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(largest)


def crop_dialog(frame, bbox):
    x, y, w, h = bbox
    return frame[y:y + h, x:x + w]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k "bbox or crop_dialog"`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament dialog bbox autodetect + crop"
```

---

### Task 3: Fullscreen capture

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
class _FakeShot:
    def __init__(self, bgra):
        self.bgra = bgra
        self.size = (bgra.shape[1], bgra.shape[0])


class _FakeSct:
    def __init__(self, bgra):
        self._bgra = bgra
        self.monitors = [None, {"left": 0, "top": 0, "width": bgra.shape[1], "height": bgra.shape[0]}]

    def grab(self, monitor):
        return _FakeShot(self._bgra)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_grab_fullscreen(monkeypatch):
    frame = _load_fixture()
    bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
    monkeypatch.setattr(tr.mss, "mss", lambda: _FakeSct(bgra))
    result = tr.grab_fullscreen()
    assert np.array_equal(result, frame)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k grab_fullscreen`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'grab_fullscreen'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def grab_fullscreen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        frame = np.array(shot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k grab_fullscreen`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament_reader fullscreen capture via mss"
```

---

### Task 4: Row pitch detection

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_detect_row_pitch():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    assert (pitch, row_top) == (100, 12)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k row_pitch`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'detect_row_pitch'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def detect_row_pitch(dialog):
    gray = cv2.cvtColor(dialog, cv2.COLOR_BGR2GRAY)
    row_means = gray.mean(axis=1)
    diffs = np.abs(np.diff(row_means))
    raw_peaks = np.where(diffs > PEAK_GRADIENT_THRESHOLD)[0]

    merged = []
    for p in raw_peaks:
        if p < PEAK_EDGE_MARGIN:
            continue
        if merged and p - merged[-1] <= PEAK_MERGE_DIST:
            continue
        merged.append(int(p))

    if len(merged) < 2:
        return None, None

    pitch = int(np.median(np.diff(merged)))
    row_top = int(merged[0] - pitch)
    return pitch, row_top
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k row_pitch`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament row pitch detection via gradient peak merge"
```

---

### Task 5: Per-row crops

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_get_row_crops():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    rows = tr.get_row_crops(dialog, pitch, row_top)
    assert len(rows) == tr.NUM_VISIBLE_ROWS
    for name_roi, pts_roi in rows:
        assert name_roi.shape[0] > 0 and name_roi.shape[1] > 0
        assert pts_roi.shape[0] > 0 and pts_roi.shape[1] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k get_row_crops`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'get_row_crops'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def _sub_roi(img, x_frac, y_frac):
    h, w = img.shape[:2]
    x0, x1 = int(w * x_frac[0]), int(w * x_frac[1])
    y0, y1 = int(h * y_frac[0]), int(h * y_frac[1])
    return img[y0:y1, x0:x1]


def get_row_crops(dialog, pitch, row_top):
    rows = []
    for i in range(NUM_VISIBLE_ROWS):
        top = row_top + i * pitch
        bot = top + pitch
        row = dialog[top:bot, :]
        name_roi = _sub_roi(row, NAME_X_FRAC, NAME_Y_FRAC)
        pts_roi = _sub_roi(row, PTS_X_FRAC, PTS_Y_FRAC)
        rows.append((name_roi, pts_roi))
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k get_row_crops`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament per-row name/points sub-crops"
```

---

### Task 6: OCR preprocessing + text extraction

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_ocr_text_row0_points_contains_digits():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    rows = tr.get_row_crops(dialog, pitch, row_top)
    _, pts_roi = rows[0]
    text = tr.ocr_text(pts_roi, threshold=tr.OCR_THRESHOLD)
    assert '488' in text
    assert '644' in text
    assert '262' in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k ocr_text_row0`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'ocr_text'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def preprocess_for_ocr(roi, threshold=OCR_THRESHOLD):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binary = cv2.threshold(resized, threshold, 255, cv2.THRESH_BINARY)
    return binary


def ocr_text(roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng', whitelist=None):
    processed = preprocess_for_ocr(roi, threshold=threshold)
    config = f'--psm {psm}'
    if whitelist:
        config += f' -c tessedit_char_whitelist={whitelist}'
    return pytesseract.image_to_string(processed, config=config, lang=lang, timeout=5).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k ocr_text_row0`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament OCR preprocessing + text extraction"
```

---

### Task 7: Name/points cleanup regex

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_clean_name_strips_tag_and_badge():
    assert tr.clean_name("[K229] Scaramouche 22") == "Scaramouche"
    assert tr.clean_name("[k229] МазаФака ZY") == "МазаФака"
    assert tr.clean_name("[K229] Yuki ay") == "Yuki"
    assert tr.clean_name("[K229] VikTor 2") == "VikTor"


def test_clean_name_no_tag():
    assert tr.clean_name("ЗОЛОТОЙ") == "ЗОЛОТОЙ"


def test_clean_points_strips_non_digits():
    assert tr.clean_points("488 644 262 очки") == 488644262
    assert tr.clean_points("71 896 730") == 71896730


def test_clean_points_empty_returns_none():
    assert tr.clean_points("очки") is None
    assert tr.clean_points("") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k "clean_name or clean_points"`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'clean_name'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def clean_name(text):
    text = re.sub(r'^\[.*?\]\s*', '', text)
    text = re.sub(r'\s+\S{1,3}$', '', text)
    return text.strip()


def clean_points(text):
    digits = re.sub(r'[^\d]', '', text)
    if not digits:
        return None
    return int(digits)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k "clean_name or clean_points"`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament name/points cleanup regex"
```

---

### Task 8: ocr_row — combined per-row OCR

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_ocr_row_all_visible_rows():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    pitch, row_top = tr.detect_row_pitch(dialog)
    rows = tr.get_row_crops(dialog, pitch, row_top)

    expected_names = ['Scaramouche', 'МазаФака', 'Yuki', 'VikTor']
    expected_points = [488644262, 315634592, 301084730, 300471402]

    for i, (name_roi, pts_roi) in enumerate(rows):
        name, points = tr.ocr_row(name_roi, pts_roi)
        assert name == expected_names[i]
        assert points == expected_points[i]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k ocr_row_all_visible`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'ocr_row'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def ocr_row(name_roi, pts_roi):
    name_text = ocr_text(name_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')
    pts_text = ocr_text(pts_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')
    return clean_name(name_text), clean_points(pts_text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k ocr_row_all_visible`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament combined per-row OCR (name+points)"
```

---

### Task 9: Own row (pinned) parsing

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_ocr_own_row():
    frame = _load_fixture()
    bbox = tr.detect_dialog_bbox(frame)
    dialog = tr.crop_dialog(frame, bbox)
    own_row = tr.get_own_row(dialog)
    place_roi, name_roi, pts_roi = tr.get_own_row_crops(own_row)
    result = tr.ocr_own_row(place_roi, name_roi, pts_roi)
    assert result == {'rank': 79, 'name': 'ЗОЛОТОЙ', 'points': 71896730}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k ocr_own_row`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'get_own_row'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def get_own_row(dialog):
    h = dialog.shape[0]
    top = int(h * OWN_ROW_Y_FRAC[0])
    return dialog[top:h, :]


def get_own_row_crops(own_row):
    place_roi = _sub_roi(own_row, PLACE_X_FRAC, PLACE_Y_FRAC)
    name_roi = _sub_roi(own_row, NAME_X_FRAC, NAME_Y_FRAC)
    pts_roi = _sub_roi(own_row, PTS_X_FRAC, PTS_Y_FRAC)
    return place_roi, name_roi, pts_roi


def ocr_own_row(place_roi, name_roi, pts_roi):
    place_text = ocr_text(place_roi, threshold=PLACE_OCR_THRESHOLD, psm=6, lang='rus+eng', whitelist='0123456789')
    name_text = ocr_text(name_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')
    pts_text = ocr_text(pts_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')

    rank = int(place_text) if place_text.isdigit() else None
    return {
        'rank': rank,
        'name': clean_name(name_text),
        'points': clean_points(pts_text),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k ocr_own_row`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament pinned own-row parsing"
```

---

### Task 10: Place computation by points anchor

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_compute_places_first_frame():
    rows = [('Alice', 100), ('Bob', 90), ('Carl', 80)]
    places = tr.compute_places(rows, known_places={})
    assert places == {1: ('Alice', 100), 2: ('Bob', 90), 3: ('Carl', 80)}


def test_compute_places_anchor_offset():
    known = {1: ('Alice', 100), 2: ('Bob', 90), 3: ('Carl', 80)}
    # New frame scrolled down by 1: Bob is now at index 0, Carl at index 1, Dave (new) at index 2
    rows = [('Bob', 90), ('Carl', 80), ('Dave', 70)]
    places = tr.compute_places(rows, known_places=known)
    assert places == {2: ('Bob', 90), 3: ('Carl', 80), 4: ('Dave', 70)}


def test_compute_places_no_anchor_returns_none():
    known = {1: ('Alice', 100), 2: ('Bob', 90)}
    rows = [('Zara', 999), ('Yara', 998)]
    places = tr.compute_places(rows, known_places=known)
    assert places is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k compute_places`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'compute_places'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def compute_places(rows, known_places):
    if not known_places:
        return {STARTING_RANK + i: rows[i] for i in range(len(rows))}

    points_to_place = {data[1]: place for place, data in known_places.items()}

    offset = None
    for i, (_, points) in enumerate(rows):
        if points in points_to_place:
            offset = points_to_place[points] - i
            break

    if offset is None:
        return None

    return {offset + i: rows[i] for i in range(len(rows))}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k compute_places`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament place computation via points anchor"
```

---

### Task 11: End-of-list detection

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_is_end_of_list_identical_frames():
    dialog = np.full((546, 766, 3), 200, dtype=np.uint8)
    assert tr.is_end_of_list(dialog, dialog) is True


def test_is_end_of_list_different_text_area():
    prev = np.full((546, 766, 3), 200, dtype=np.uint8)
    curr = prev.copy()
    # change pixels in the text area (not scrollbar, not own row)
    curr[100:110, 100:110] = 50
    assert tr.is_end_of_list(prev, curr) is False


def test_is_end_of_list_ignores_scrollbar_and_own_row():
    prev = np.full((546, 766, 3), 200, dtype=np.uint8)
    curr = prev.copy()
    h, w = curr.shape[:2]
    # change only the scrollbar strip (rightmost 5%)
    scrollbar_x0 = int(w * (1 - tr.SCROLLBAR_FRAC))
    curr[:, scrollbar_x0:] = 50
    # change only the own-row strip (bottom from OWN_ROW_Y_FRAC[0])
    own_y0 = int(h * tr.OWN_ROW_Y_FRAC[0])
    curr[own_y0:, :] = 50
    assert tr.is_end_of_list(prev, curr) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k is_end_of_list`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'is_end_of_list'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def is_end_of_list(prev_dialog, curr_dialog):
    h, w = curr_dialog.shape[:2]
    scrollbar_x0 = int(w * (1 - SCROLLBAR_FRAC))
    own_y0 = int(h * OWN_ROW_Y_FRAC[0])

    prev_crop = prev_dialog[:own_y0, :scrollbar_x0]
    curr_crop = curr_dialog[:own_y0, :scrollbar_x0]

    diff = cv2.absdiff(prev_crop, curr_crop)
    return diff.mean() < END_DIFF_THRESHOLD
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k is_end_of_list`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament end-of-list detection via absdiff"
```

---

### Task 12: Main collection loop

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_collect_tournament_data(monkeypatch):
    frame = _load_fixture()

    monkeypatch.setattr(tr, "grab_fullscreen", lambda: frame)
    monkeypatch.setattr(tr.pyautogui, "scroll", lambda *a, **k: None)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(tr.random, "uniform", lambda a, b: 0)

    result = tr.collect_tournament_data()

    leaderboard = result['leaderboard']
    assert [row['rank'] for row in leaderboard] == [1, 2, 3, 4]
    assert [row['name'] for row in leaderboard] == ['Scaramouche', 'МазаФака', 'Yuki', 'VikTor']
    assert [row['points'] for row in leaderboard] == [488644262, 315634592, 301084730, 300471402]

    assert result['own_data'] == {'rank': 79, 'name': 'ЗОЛОТОЙ', 'points': 71896730}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k collect_tournament_data`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'collect_tournament_data'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def collect_tournament_data():
    known_places = {}
    prev_dialog = None

    while True:
        frame = grab_fullscreen()
        bbox = detect_dialog_bbox(frame)
        dialog = crop_dialog(frame, bbox)

        if prev_dialog is not None and is_end_of_list(prev_dialog, dialog):
            break

        pitch, row_top = detect_row_pitch(dialog)
        rows = get_row_crops(dialog, pitch, row_top)
        ocr_rows = [ocr_row(name_roi, pts_roi) for name_roi, pts_roi in rows]
        ocr_rows = [(name, points) for name, points in ocr_rows if points is not None]

        places = compute_places(ocr_rows, known_places)
        if places is not None:
            known_places.update(places)
            for place, (name, points) in places.items():
                print(f"место {place}: {name} — {points}")

        prev_dialog = dialog

        pyautogui.scroll(-2)
        time.sleep(random.uniform(0.4, 0.9))

    own_row = get_own_row(dialog)
    place_roi, name_roi, pts_roi = get_own_row_crops(own_row)
    own_data = ocr_own_row(place_roi, name_roi, pts_roi)

    leaderboard = [
        {'rank': place, 'name': name, 'points': points}
        for place, (name, points) in sorted(known_places.items())
    ]

    return {'leaderboard': leaderboard, 'own_data': own_data}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k collect_tournament_data`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament main collection loop (scroll+OCR+dedup+end-detect)"
```

---

### Task 13: API export with local fallback

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_export_to_api_success(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['json'] = json
        return _FakeResponse(200)

    monkeypatch.setattr(tr.requests, "post", fake_post)

    config = {"api_url": "https://api.total-hunter.com", "api_token": "secret123", "alliance_tag": "K229"}
    data = {
        "leaderboard": [{"rank": 1, "name": "Scaramouche", "points": 488644262}],
        "own_data": {"rank": 79, "name": "ЗОЛОТОЙ", "points": 71896730},
    }

    result = tr.export_to_api(config, data, event_timestamp="2026-06-14T21:30:00")

    assert result is True
    assert captured['url'] == "https://api.total-hunter.com/api/v1/tournaments/import"
    assert captured['headers'] == {"Authorization": "Bearer secret123"}
    assert captured['json'] == {
        "event_timestamp": "2026-06-14T21:30:00",
        "alliance_tag": "K229",
        "own_data": data["own_data"],
        "leaderboard": data["leaderboard"],
    }


def test_export_to_api_failure_writes_local_fallback(monkeypatch, tmp_path):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse(500)

    monkeypatch.setattr(tr.requests, "post", fake_post)
    monkeypatch.chdir(tmp_path)

    config = {"api_url": "https://api.total-hunter.com", "api_token": "secret123", "alliance_tag": "K229"}
    data = {
        "leaderboard": [{"rank": 1, "name": "Scaramouche", "points": 488644262}],
        "own_data": {"rank": 79, "name": "ЗОЛОТОЙ", "points": 71896730},
    }

    result = tr.export_to_api(config, data, event_timestamp="2026-06-14T21:30:00")

    assert result is False
    files = list(tmp_path.glob("tournament_export_*.json"))
    assert len(files) == 1
    with open(files[0], encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["leaderboard"] == data["leaderboard"]
    assert saved["own_data"] == data["own_data"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k export_to_api`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'export_to_api'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def export_to_api(config, data, event_timestamp):
    payload = {
        "event_timestamp": event_timestamp,
        "alliance_tag": config["alliance_tag"],
        "own_data": data["own_data"],
        "leaderboard": data["leaderboard"],
    }
    headers = {"Authorization": f"Bearer {config['api_token']}"}
    url = config["api_url"] + API_IMPORT_PATH

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if 200 <= response.status_code < 300:
            return True
    except requests.RequestException:
        pass

    filename = f"tournament_export_{int(time.time())}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Не удалось отправить данные на сервер. Сохранено локально: {filename}")
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k export_to_api`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament POST export with local JSON fallback"
```

---

### Task 14: main() entry point

**Files:**
- Modify: `tournament_reader.py`
- Test: `test_tournament_reader.py`

- [ ] **Step 1: Write the failing test**

Append to `test_tournament_reader.py`:

```python
def test_main_smoke(monkeypatch):
    config = {"api_url": "https://api.total-hunter.com", "api_token": "secret123", "alliance_tag": "K229"}
    collected = {
        "leaderboard": [{"rank": 1, "name": "Scaramouche", "points": 488644262}],
        "own_data": {"rank": 79, "name": "ЗОЛОТОЙ", "points": 71896730},
    }

    monkeypatch.setattr(tr, "load_config", lambda: config)
    monkeypatch.setattr(tr, "collect_tournament_data", lambda: collected)
    monkeypatch.setattr(tr, "export_to_api", lambda cfg, data, event_timestamp: True)
    monkeypatch.setattr(tr.time, "sleep", lambda *a, **k: None)

    tr.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_tournament_reader.py -v -k main_smoke`
Expected: FAIL with `AttributeError: module 'tournament_reader' has no attribute 'main'`

- [ ] **Step 3: Write minimal implementation**

Append to `tournament_reader.py`:

```python
def main():
    config = load_config()

    print("Откройте диалог «Статистика» в игре. Сбор начнётся через 3 секунды...")
    for i in (3, 2, 1):
        print(i)
        time.sleep(1)

    data = collect_tournament_data()

    print(f"Собрано строк: {len(data['leaderboard'])}")
    print(f"Своё место: {data['own_data']}")

    event_timestamp = datetime.datetime.now().isoformat(timespec='seconds')
    success = export_to_api(config, data, event_timestamp)

    if success:
        print("Данные успешно отправлены на сервер.")
    else:
        print("Данные сохранены локально (см. сообщение выше).")


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_tournament_reader.py -v -k main_smoke`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py test_tournament_reader.py
git commit -m "feat: tournament_reader main() entry point"
```

---

## Final Check

After all 14 tasks:

```bash
pytest test_tournament_reader.py -v
```

Expected: all tests PASS (≈20 tests across constants/config, bbox, capture, pitch, crops, OCR, cleanup, own-row, places, end-detection, main loop, export, main).
