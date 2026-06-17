# Chest Counter (Сундуки) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new "СУНДУКИ" (Chests) tab to the bot GUI that scans the in-game «Мой клан → Подарки» dialog, opens each gift chest top-to-bottom (no scrolling — the list shifts up after every click), counts chest types per sender, buffers every read into a local SQLite DB, and lets the user push the buffered batch to the server on demand.

**Architecture:** New standalone, GUI-free module `chest_reader.py` (HSV dialog detection + OCR + SQLite + collection loop — same family as `tournament_reader.py`/`clan_roster_reader.py`) plus a new tab in `main.py` (`TotalHunterApp`) that drives it from a daemon thread, following the exact existing patterns used by the СКЛЕПЫ/РЕФЕРАЛЫ/РОЙ tabs (CTkSegmentedButton tab switching, `self.after(0, ...)` for thread-safe GUI updates, `gui_config.json` for persisted text fields).

**Tech Stack:** Python 3.13, OpenCV, pytesseract, mss, pyautogui, sqlite3 (stdlib), CustomTkinter, pytest.

**Spec:** `docs/superpowers/specs/2026-06-17-chest-counter-design.md`

**Calibration source:** fixture `Сундуки_1.png` (1920×1080), already in repo root. Verified during planning:
- `detect_dialog_bbox` (same HSV range as `tournament_reader.py`: `(10,20,150)`–`(40,120,255)`) → bbox `(671, 340, 764, 475)` on the fixture — this region is the gift-list content panel (rows + bottom action buttons).
- Top row band = `dialog[0:100, :]` (`ROW_PITCH = 100`, `ROW_TOP = 0` — the bbox top edge already aligns with the first row's top edge, no header offset needed, no scroll/pitch-detection required since the list never scrolls).
- Type text crop (row-relative fractions): `x∈(0.135, 0.58)`, `y∈(0.03, 0.32)`.
- Sender text crop: `x∈(0.135, 0.58)`, `y∈(0.34, 0.60)`.
- OCR (Otsu, non-inverted, `psm=7`, `lang='rus+eng'`) on the fixture returns `'| Сундук Эпического Монстра'` and `'р От: Gray Cardinal'` (small icon-bleed artifact at the start of each line) — cleaned by regex to `'Сундук Эпического Монстра'` / `'Gray Cardinal'`.
- The existing `button_finder.find_colored_button(region, color='green', pick='largest')` (no changes needed) finds the «Открыть» button inside the row at row-relative `(679, 75)` of a `(100, 764)` row — confirms the established green-button HSV range already covers this UI's button with no recalibration.

---

## Task 1: `chest_reader.py` — dialog & row detection

**Files:**
- Create: `C:\BattleBot\chest_reader.py`
- Create: `C:\BattleBot\test_chest_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# test_chest_reader.py
import os
import cv2
import numpy as np
import chest_reader as cr


def _load_fixture():
    return cv2.imdecode(np.fromfile("Сундуки_1.png", dtype=np.uint8), cv2.IMREAD_COLOR)


def test_detect_dialog_bbox():
    frame = _load_fixture()
    bbox = cr.detect_dialog_bbox(frame)
    assert bbox == (671, 340, 764, 475)


def test_detect_dialog_bbox_returns_none_when_no_match():
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    assert cr.detect_dialog_bbox(blank) is None


def test_crop_dialog():
    frame = _load_fixture()
    bbox = cr.detect_dialog_bbox(frame)
    dialog = cr.crop_dialog(frame, bbox)
    assert dialog.shape[:2] == (475, 764)


def test_get_top_row():
    frame = _load_fixture()
    dialog = cr.crop_dialog(frame, cr.detect_dialog_bbox(frame))
    row = cr.get_top_row(dialog)
    assert row.shape[:2] == (100, 764)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'chest_reader'`

- [ ] **Step 3: Write `chest_reader.py` (dialog/row detection part)**

```python
"""
chest_reader.py — Сундуки (Chests) module.
Scans the in-game «Мой клан → Подарки» dialog: reads the top gift row
(chest type + sender), clicks «Открыть», the list shifts up by itself —
no scrolling. Buffers every read chest into a local SQLite DB
(chest_buffer.db) so data survives crashes/restarts until explicitly
pushed to the server.
"""
import os
import re
import time
import random
import sqlite3
import datetime
import collections

import cv2
import numpy as np
import mss
import pyautogui
import pytesseract
import requests

from auth import SERVER_URL, get_hwid
from button_finder import find_colored_button

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Dialog detection (same tan/gold frame as tournament_reader.py) -------
DIALOG_HSV_LOWER = (10, 20, 150)
DIALOG_HSV_UPPER = (40, 120, 255)
MIN_DIALOG_DIM = 200  # guard against a 1-2px degenerate bbox on a glitched frame

# --- Row geometry — no scroll, only the top row is ever read --------------
ROW_PITCH = 100

# --- Per-row crop fractions (relative to the 764x100 top-row band) --------
TYPE_X_FRAC = (0.135, 0.58)
TYPE_Y_FRAC = (0.03, 0.32)
SENDER_X_FRAC = (0.135, 0.58)
SENDER_Y_FRAC = (0.34, 0.60)

# --- «Открыть» button search box (relative to the top row) ----------------
BUTTON_X_FRAC = (0.78, 1.0)
BUTTON_Y_FRAC = (0.45, 1.0)

# --- Anti-detect click ------------------------------------------------------
ANTI_DETECT_OFFSET_PX = 8
ANTI_DETECT_PAUSE_RANGE = (0.4, 0.9)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chest_buffer.db')
API_IMPORT_PATH = '/api/v1/chests/import'


def detect_dialog_bbox(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, DIALOG_HSV_LOWER, DIALOG_HSV_UPPER)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(largest)


def crop_dialog(frame, bbox):
    x, y, w, h = bbox
    return frame[y:y + h, x:x + w]


def grab_fullscreen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        frame = np.array(shot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def get_top_row(dialog):
    return dialog[0:ROW_PITCH, :]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest-reader): dialog and top-row detection"
```

---

## Task 2: OCR parsing of chest type & sender

**Files:**
- Modify: `C:\BattleBot\chest_reader.py`
- Modify: `C:\BattleBot\test_chest_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to test_chest_reader.py

def test_parse_chest_type_strips_leading_ocr_artifact():
    assert cr.parse_chest_type("| Сундук Эпического Монстра") == "Сундук Эпического Монстра"


def test_parse_chest_type_empty_text():
    assert cr.parse_chest_type("") == ""


def test_parse_sender_extracts_name_after_prefix():
    assert cr.parse_sender("р От: Gray Cardinal") == "Gray Cardinal"


def test_parse_sender_strips_trailing_ocr_artifact():
    assert cr.parse_sender("От: Золотой|") == "Золотой"


def test_parse_sender_no_prefix_match_falls_back_to_raw_line():
    assert cr.parse_sender("SomeGarbledText") == "SomeGarbledText"


def test_read_top_row_on_fixture():
    frame = _load_fixture()
    dialog = cr.crop_dialog(frame, cr.detect_dialog_bbox(frame))
    chest_type, sender = cr.read_top_row(dialog)
    assert chest_type == "Сундук Эпического Монстра"
    assert sender == "Gray Cardinal"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -v`
Expected: FAIL — `AttributeError: module 'chest_reader' has no attribute 'parse_chest_type'`

- [ ] **Step 3: Append OCR/parsing functions to `chest_reader.py`**

```python
def _sub_roi(img, x_frac, y_frac):
    h, w = img.shape[:2]
    x0, x1 = int(w * x_frac[0]), int(w * x_frac[1])
    y0, y1 = int(h * y_frac[0]), int(h * y_frac[1])
    return img[y0:y1, x0:x1]


def preprocess_for_ocr(roi):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binary = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def ocr_text(roi, psm=7, lang='rus+eng'):
    processed = preprocess_for_ocr(roi)
    config = f'--psm {psm}'
    return pytesseract.image_to_string(processed, config=config, lang=lang, timeout=5).strip()


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


def parse_chest_type(raw_text):
    first_line = raw_text.splitlines()[0] if raw_text else ''
    return re.sub(r'^[^А-Яа-яA-Za-z]+', '', first_line).strip()


def parse_sender(raw_text):
    first_line = raw_text.splitlines()[0] if raw_text else ''
    match = re.search(r'[OО0]т\s*[:;]\s*(.+)', first_line)
    name = match.group(1) if match else first_line
    return clean_name(name)


def read_top_row(dialog):
    row = get_top_row(dialog)
    type_roi = _sub_roi(row, TYPE_X_FRAC, TYPE_Y_FRAC)
    sender_roi = _sub_roi(row, SENDER_X_FRAC, SENDER_Y_FRAC)
    chest_type = parse_chest_type(ocr_text(type_roi))
    sender = parse_sender(ocr_text(sender_roi))
    return chest_type, sender
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest-reader): OCR parsing of chest type and sender"
```

---

## Task 3: SQLite local buffer

**Files:**
- Modify: `C:\BattleBot\chest_reader.py`
- Modify: `C:\BattleBot\test_chest_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to test_chest_reader.py

def test_init_db_creates_table(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='local_chests'")
    assert cur.fetchone() is not None
    conn.close()


def test_insert_and_get_unsynced(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Alice", "2026-06-17T10:00:00")
    cr.insert_chest(conn, "Сундук Легендарного Монстра", "Bob", "2026-06-17T10:01:00")
    rows = cr.get_unsynced(conn)
    assert len(rows) == 2
    assert rows[0][1] == "Alice"
    assert rows[0][2] == "Сундук Эпического Монстра"
    conn.close()


def test_mark_synced_excludes_from_unsynced(tmp_path):
    db_path = str(tmp_path / "chest_buffer.db")
    conn = cr.init_db(db_path)
    cr.insert_chest(conn, "Сундук Эпического Монстра", "Alice", "2026-06-17T10:00:00")
    cr.insert_chest(conn, "Сундук Легендарного Монстра", "Bob", "2026-06-17T10:01:00")
    rows = cr.get_unsynced(conn)
    ids = [r[0] for r in rows]
    cr.mark_synced(conn, ids)
    assert cr.get_unsynced(conn) == []
    conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -v`
Expected: FAIL — `AttributeError: module 'chest_reader' has no attribute 'init_db'`

- [ ] **Step 3: Append SQLite layer to `chest_reader.py`**

```python
def init_db(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS local_chests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_player_name TEXT,
            chest_type TEXT,
            timestamp TEXT,
            is_synced INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    return conn


def insert_chest(conn, chest_type, raw_player_name, timestamp):
    conn.execute(
        'INSERT INTO local_chests (raw_player_name, chest_type, timestamp, is_synced) '
        'VALUES (?, ?, ?, 0)',
        (raw_player_name, chest_type, timestamp),
    )
    conn.commit()


def get_unsynced(conn):
    cur = conn.execute(
        'SELECT id, raw_player_name, chest_type, timestamp FROM local_chests WHERE is_synced = 0'
    )
    return cur.fetchall()


def mark_synced(conn, ids):
    conn.executemany('UPDATE local_chests SET is_synced = 1 WHERE id = ?', [(i,) for i in ids])
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest-reader): SQLite local buffer (chest_buffer.db)"
```

---

## Task 4: Button detection, click, and the collection loop

**Files:**
- Modify: `C:\BattleBot\chest_reader.py`
- Modify: `C:\BattleBot\test_chest_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to test_chest_reader.py

def test_find_open_button_region_is_top_row_right_side():
    """find_open_button must restrict the color search to the top-row band,
    not the whole dialog (avoids matching unrelated green UI elsewhere)."""
    captured = {}

    def fake_find_colored_button(region, color, pick):
        captured['region'] = region
        captured['color'] = color
        return (region[0] + 10, region[1] + 10)

    import chest_reader as cr_mod
    monkey_target = cr_mod.find_colored_button
    cr_mod.find_colored_button = fake_find_colored_button
    try:
        bbox = (671, 340, 764, 475)
        pos = cr.find_open_button(bbox)
        # region[0] = 671 + int(764*0.78) = 1266; region[1] = 340 + int(100*0.45) = 385
        # fake_find_colored_button returns (region[0]+10, region[1]+10)
        assert pos == (1276, 395)
        x, y, w, h = captured['region']
        assert x == 671 + int(764 * 0.78)
        assert y == 340 + int(100 * 0.45)
        assert captured['color'] == 'green'
    finally:
        cr_mod.find_colored_button = monkey_target


def test_collect_chests_counts_and_persists(tmp_path, monkeypatch):
    sequence = [
        ((100, 100), "Сундук Эпического Монстра", "Alice"),
        ((100, 100), "Сундук Эпического Монстра", "Bob"),
        (None, None, None),
    ]
    state = {'n': 0}

    monkeypatch.setattr(cr, "grab_fullscreen", lambda: np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(cr, "detect_dialog_bbox", lambda frame: (0, 0, 764, 475))
    monkeypatch.setattr(cr, "crop_dialog", lambda frame, bbox: np.zeros((475, 764, 3), dtype=np.uint8))

    def fake_find_open_button(bbox):
        return sequence[state['n']][0]

    def fake_read_top_row(dialog):
        _, chest_type, sender = sequence[state['n']]
        state['n'] += 1
        return chest_type, sender

    clicked = []
    monkeypatch.setattr(cr, "find_open_button", fake_find_open_button)
    monkeypatch.setattr(cr, "read_top_row", fake_read_top_row)
    monkeypatch.setattr(cr, "click_open_button", lambda pos: clicked.append(pos))

    db_path = str(tmp_path / "test_chest_buffer.db")
    result = cr.collect_chests(lambda: False, db_path=db_path)

    assert result["counts"] == {"Сундук Эпического Монстра": 2}
    assert len(clicked) == 2

    conn = cr.init_db(db_path)
    rows = cr.get_unsynced(conn)
    assert len(rows) == 2
    assert rows[0][1] == "Alice"
    assert rows[1][1] == "Bob"
    conn.close()


def test_collect_chests_stops_immediately_when_flag_already_set(tmp_path, monkeypatch):
    def boom():
        raise AssertionError("grab_fullscreen must not be called when stop_flag is already True")
    monkeypatch.setattr(cr, "grab_fullscreen", boom)

    db_path = str(tmp_path / "test_chest_buffer.db")
    result = cr.collect_chests(lambda: True, db_path=db_path)
    assert result == {"counts": {}, "items": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -v`
Expected: FAIL — `AttributeError: module 'chest_reader' has no attribute 'find_open_button'`

- [ ] **Step 3: Append button/click/loop functions to `chest_reader.py`**

```python
def find_open_button(bbox):
    x, y, w, h = bbox
    region = (
        x + int(w * BUTTON_X_FRAC[0]),
        y + int(ROW_PITCH * BUTTON_Y_FRAC[0]),
        int(w * (BUTTON_X_FRAC[1] - BUTTON_X_FRAC[0])),
        int(ROW_PITCH * (BUTTON_Y_FRAC[1] - BUTTON_Y_FRAC[0])),
    )
    return find_colored_button(region, color='green', pick='largest')


def click_open_button(pos):
    cx, cy = pos
    click_x = cx + random.randint(-ANTI_DETECT_OFFSET_PX, ANTI_DETECT_OFFSET_PX)
    click_y = cy + random.randint(-5, 5)
    pyautogui.click(click_x, click_y)
    time.sleep(random.uniform(*ANTI_DETECT_PAUSE_RANGE))


def collect_chests(stop_flag, on_update=None, db_path=DB_PATH):
    """Reads and opens chests from the top of the «Мой клан → Подарки» list
    until the list is empty (no «Открыть» button found) or stop_flag()
    returns True. Every chest is persisted to SQLite as it's read.
    Returns {'counts': {chest_type: n}, 'items': [{'chest_type', 'sender',
    'timestamp'}, ...]} for this session."""
    conn = init_db(db_path)
    counts = collections.Counter()
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

            chest_type, sender = read_top_row(dialog)
            timestamp = datetime.datetime.now().isoformat(timespec='seconds')
            insert_chest(conn, chest_type, sender, timestamp)
            counts[chest_type] += 1
            items.append({'chest_type': chest_type, 'sender': sender, 'timestamp': timestamp})

            if on_update:
                on_update(dict(counts))

            click_open_button(pos)
    finally:
        conn.close()

    return {'counts': dict(counts), 'items': items}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest-reader): button detection, click, and collection loop"
```

---

## Task 5: Server export

**Files:**
- Modify: `C:\BattleBot\chest_reader.py`
- Modify: `C:\BattleBot\test_chest_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to test_chest_reader.py

class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_export_to_api_success(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured['url'] = url
        captured['json'] = json
        return _FakeResponse(200)

    monkeypatch.setattr(cr.requests, "post", fake_post)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")

    items = [{"chest_type": "Сундук Эпического Монстра", "sender": "Alice",
              "timestamp": "2026-06-17T10:00:00"}]
    result = cr.export_to_api("K229", "Legion", items)

    assert result is True
    assert captured['url'].endswith("/api/v1/chests/import")
    assert captured['json']["hwid"] == "ABCD1234"
    assert captured['json']["kingdom"] == "K229"
    assert captured['json']["clan"] == "Legion"
    assert captured['json']["items"] == items


def test_export_to_api_http_failure(monkeypatch):
    monkeypatch.setattr(cr.requests, "post", lambda url, json, timeout: _FakeResponse(404))
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    assert cr.export_to_api("K229", "Legion", []) is False


def test_export_to_api_network_exception(monkeypatch):
    def raise_exc(url, json, timeout):
        raise cr.requests.RequestException("no connection")
    monkeypatch.setattr(cr.requests, "post", raise_exc)
    monkeypatch.setattr(cr, "get_hwid", lambda: "ABCD1234")
    assert cr.export_to_api("K229", "Legion", []) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest test_chest_reader.py -v`
Expected: FAIL — `AttributeError: module 'chest_reader' has no attribute 'export_to_api'`

- [ ] **Step 3: Append to `chest_reader.py`**

```python
def export_to_api(kingdom, clan, items):
    payload = {
        "hwid": get_hwid(),
        "kingdom": kingdom,
        "clan": clan,
        "timestamp": datetime.datetime.now().isoformat(timespec='seconds'),
        "items": items,
    }
    try:
        response = requests.post(SERVER_URL + API_IMPORT_PATH, json=payload, timeout=10)
        return 200 <= response.status_code < 300
    except requests.RequestException:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest test_chest_reader.py -v`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add chest_reader.py test_chest_reader.py
git commit -m "feat(chest-reader): export buffered chests to server API"
```

---

## Task 6: `main.py` — i18n keys for all 19 languages

**Files:**
- Modify: `C:\BattleBot\main.py:142,204,263,311,359,407,455,503,551,599,647,695,743,791,839,887,935,983,1031`

No test for this task (pure data/string addition) — verified in Task 9 by running the app and switching languages without crashing. RU gets real Russian text, EN gets real English text, the other 17 languages get the same English text (per project decision — real translations are a separate future task).

- [ ] **Step 1: RU (line 142)**

```python
# OLD:
        "tab_crypt": "СКЛЕПЫ", "tab_cal": "Калибровка", "tab_roy": "РОЙ",

# NEW:
        "tab_crypt": "СКЛЕПЫ", "tab_cal": "Калибровка", "tab_roy": "РОЙ", "tab_chest": "СУНДУКИ",
        # --- chest tab ---
        "chest_kingdom_lb": "Королевство:", "chest_clan_lb": "Название клана:",
        "chest_start_btn": "СТАРТ", "chest_stop_btn": "СТОП",
        "chest_status_ready": "Готово к сбору", "chest_status_running": "Сбор сундуков...",
        "chest_status_stopped": "Остановлено", "chest_status_no_dialog": "Откройте «Мой клан → Подарки»",
        "chest_missing_fields": "Укажите Королевство и Клан",
        "chest_send_btn": "ОТПРАВИТЬ НА СЕРВЕР", "chest_send_success": "Отправлено на сервер",
        "chest_send_failed": "Сервер недоступен. Данные сохранены локально.",
        "chest_total_lb": "Всего открыто:",
```

- [ ] **Step 2: EN (line 204)**

```python
# OLD:
        "tab_crypt": "CRYPTS", "tab_cal": "Calibration", "tab_roy": "SWARM",

# NEW:
        "tab_crypt": "CRYPTS", "tab_cal": "Calibration", "tab_roy": "SWARM", "tab_chest": "CHESTS",
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 3: DE (line 263)** — old line: `        "tab_crypt": "KRYPTEN", "tab_cal": "Kalibrierung", "tab_roy": "SCHWARM",`

```python
        "tab_crypt": "KRYPTEN", "tab_cal": "Kalibrierung", "tab_roy": "SCHWARM", "tab_chest": "CHESTS",
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 4: ES (line 311)** — old line: `        "tab_crypt": "CRIPTAS", "tab_cal": "Calibración", "tab_roy": "ENJAMBRE",`

Same NEW block as Step 3, with the first line being:
```python
        "tab_crypt": "CRIPTAS", "tab_cal": "Calibración", "tab_roy": "ENJAMBRE", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 5: FR (line 359)** — old line: `        "tab_crypt": "CRYPTES", "tab_cal": "Calibration", "tab_roy": "ESSAIM",`

```python
        "tab_crypt": "CRYPTES", "tab_cal": "Calibration", "tab_roy": "ESSAIM", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 6: IT (line 407)** — old line: `        "tab_crypt": "CRIPTE", "tab_cal": "Calibrazione", "tab_roy": "SCIAME",`

```python
        "tab_crypt": "CRIPTE", "tab_cal": "Calibrazione", "tab_roy": "SCIAME", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 7: NL (line 455)** — old line: `        "tab_crypt": "CRYPTEN", "tab_cal": "Kalibratie", "tab_roy": "ZWERM",`

```python
        "tab_crypt": "CRYPTEN", "tab_cal": "Kalibratie", "tab_roy": "ZWERM", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 8: NO (line 503)** — old line: `        "tab_crypt": "KRYPTER", "tab_cal": "Kalibrering", "tab_roy": "SVERM",`

```python
        "tab_crypt": "KRYPTER", "tab_cal": "Kalibrering", "tab_roy": "SVERM", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 9: PL (line 551)** — old line: `        "tab_crypt": "KRYPTY", "tab_cal": "Kalibracja", "tab_roy": "RÓJ",`

```python
        "tab_crypt": "KRYPTY", "tab_cal": "Kalibracja", "tab_roy": "RÓJ", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 10: PT (line 599)** — old line: `        "tab_crypt": "CRIPTAS", "tab_cal": "Calibração", "tab_roy": "ENXAME",`

```python
        "tab_crypt": "CRIPTAS", "tab_cal": "Calibração", "tab_roy": "ENXAME", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 11: SV (line 647)** — old line: `        "tab_crypt": "KRYPTOR", "tab_cal": "Kalibrering", "tab_roy": "SVÄRM",`

```python
        "tab_crypt": "KRYPTOR", "tab_cal": "Kalibrering", "tab_roy": "SVÄRM", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 12: TR (line 695)** — old line: `        "tab_crypt": "KRİPTALAR", "tab_cal": "Kalibrasyon", "tab_roy": "OĞUL",`

```python
        "tab_crypt": "KRİPTALAR", "tab_cal": "Kalibrasyon", "tab_roy": "OĞUL", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 13: AR (line 743)** — old line: `        "tab_crypt": "المقابر", "tab_cal": "معايرة", "tab_roy": "سرب",`

```python
        "tab_crypt": "المقابر", "tab_cal": "معايرة", "tab_roy": "سرب", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 14: JA (line 791)** — old line: `        "tab_crypt": "クリプト", "tab_cal": "キャリブレーション", "tab_roy": "群れ",`

```python
        "tab_crypt": "クリプト", "tab_cal": "キャリブレーション", "tab_roy": "群れ", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 15: ZH-CN (line 839)** — old line: `        "tab_crypt": "地下墓穴", "tab_cal": "校准", "tab_roy": "蜂群",`

```python
        "tab_crypt": "地下墓穴", "tab_cal": "校准", "tab_roy": "蜂群", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 16: ZH-TW (line 887)** — old line: `        "tab_crypt": "地下墓穴", "tab_cal": "校準", "tab_roy": "蜂群",`

```python
        "tab_crypt": "地下墓穴", "tab_cal": "校準", "tab_roy": "蜂群", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

(Note: distinguish this `old_string` from Step 15 by including a few lines of unique surrounding context — the `tab_cal` value differs: `校准` (Step 15, simplified) vs `校準` (this step, traditional) — these ARE different strings, so each is independently unique in the file.)

- [ ] **Step 17: KO (line 935)** — old line: `        "tab_crypt": "크립트", "tab_cal": "보정", "tab_roy": "군집",`

```python
        "tab_crypt": "크립트", "tab_cal": "보정", "tab_roy": "군집", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 18: UK (line 983)** — old line: `        "tab_crypt": "СКЛЕПИ", "tab_cal": "Калібрування", "tab_roy": "РОЙ",`

```python
        "tab_crypt": "СКЛЕПИ", "tab_cal": "Калібрування", "tab_roy": "РОЙ", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

(Note: this line is textually identical to RU's old line except this one doesn't have the Step-1 RU "NEW" content yet at the time you reach it — match against the literal line text `"tab_crypt": "СКЛЕПИ", "tab_cal": "Калібрування", "tab_roy": "РОЙ",` which is unique because "СКЛЕПИ"/"Калібрування" — Ukrainian — differ from RU's "СКЛЕПЫ"/"Калибровка".)

- [ ] **Step 19: ID (line 1031)** — old line: `        "tab_crypt": "KRIPTA", "tab_cal": "Kalibrasi", "tab_roy": "KAWANAN",`

```python
        "tab_crypt": "KRIPTA", "tab_cal": "Kalibrasi", "tab_roy": "KAWANAN", "tab_chest": "CHESTS",
```
followed by:

```python
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "chest_total_lb": "Total opened:",
```

- [ ] **Step 20: Verify no syntax errors**

Run: `python -c "import main"`
Expected: no exception (this will also exercise `LANGS` dict literal parsing). If running outside the game/without a display this may fail later at `ctk.CTk()` init — that's fine, the goal here is confirming the dict literal itself parses; if it fails before reaching GUI init with a `SyntaxError`/`KeyError`, fix it.

- [ ] **Step 21: Commit**

```bash
git add main.py
git commit -m "feat(i18n): add chest tab strings to all 19 language dicts"
```

---

## Task 7: `main.py` — tab plumbing (segmented button, frame, show/hide)

**Files:**
- Modify: `C:\BattleBot\main.py:1308-1309` (init flags)
- Modify: `C:\BattleBot\main.py:1440-1441` (`_tab_init_names`)
- Modify: `C:\BattleBot\main.py:1479-1484` (frame creation)
- Modify: `C:\BattleBot\main.py:1502-1507` (setup_*_tab calls)
- Modify: `C:\BattleBot\main.py:2663,2668-2673` (`_show_tab`)
- Modify: `C:\BattleBot\main.py:3534` (`change_lang`)

No isolated unit test (this is GUI wiring inside a `customtkinter.CTk` subclass that needs a live Tk root) — verified by manually launching the app in Task 9's verification step. Each step below is a small, independently-verifiable edit.

- [ ] **Step 1: Add chest-running state flags to `__init__`**

In `C:\BattleBot\main.py`, find (around line 1308-1309):

```python
        # self.combo_engine = CombinerEngine()  # Combo временно отключён
        self.is_combo_running = False
```

Replace with:

```python
        # self.combo_engine = CombinerEngine()  # Combo временно отключён
        self.is_combo_running = False
        self._chest_running = False
        self._chest_stop_event = threading.Event()
```

- [ ] **Step 2: Add "tab_chest" to the segmented-button tab list**

Find (around line 1440-1441):

```python
        self._tab_init_names = {k: LANGS[self.current_lang][k]
                                for k in ("tab_crypt", "tab_hunt", "tab_roy", "tab_ref")}
```

Replace with:

```python
        self._tab_init_names = {k: LANGS[self.current_lang][k]
                                for k in ("tab_crypt", "tab_hunt", "tab_roy", "tab_ref", "tab_chest")}
```

- [ ] **Step 3: Create the `tab_chest` frame**

Find (around line 1479-1484):

```python
        self.tab_crypt = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_hunt  = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        # self.tab_combo = ...  # временно отключён
        self.tab_ref   = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_roy   = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self._cal_frame = ctk.CTkScrollableFrame(self._content_frame, fg_color="transparent")
```

Replace with:

```python
        self.tab_crypt = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_hunt  = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        # self.tab_combo = ...  # временно отключён
        self.tab_ref   = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_roy   = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_chest = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self._cal_frame = ctk.CTkScrollableFrame(self._content_frame, fg_color="transparent")
```

- [ ] **Step 4: Call `setup_chest_tab()` during init**

Find (around line 1502-1507):

```python
        self.setup_hunt_tab()
        self.setup_crypt_tab()
        # self.setup_combo_tab()  # временно отключён
        self.setup_ref_tab()
        self.setup_calibration_tab()
        self.setup_roy_tab()
```

Replace with:

```python
        self.setup_hunt_tab()
        self.setup_crypt_tab()
        # self.setup_combo_tab()  # временно отключён
        self.setup_ref_tab()
        self.setup_chest_tab()
        self.setup_calibration_tab()
        self.setup_roy_tab()
```

(`setup_chest_tab` is defined in Task 8 — until then this line will raise `AttributeError` on launch, which is expected and resolved by the next task.)

- [ ] **Step 5: Add `tab_chest` to `_show_tab`**

Find (around line 2661-2673):

```python
    def _show_tab(self, key):
        """Показать фрейм вкладки по ключу, скрыть остальные."""
        _all = (self.tab_crypt, self.tab_hunt, self.tab_ref, self.tab_roy, self._cal_frame)
        for f in _all:
            f.pack_forget()
        self._cal_btn.configure(fg_color=MD3["elevated"], hover_color=MD3["card"])
        self._cal_visible = False
        tab_map = {
            "tab_crypt": self.tab_crypt,
            "tab_hunt":  self.tab_hunt,
            "tab_ref":   self.tab_ref,
            "tab_roy":   self.tab_roy,
        }
```

Replace with:

```python
    def _show_tab(self, key):
        """Показать фрейм вкладки по ключу, скрыть остальные."""
        _all = (self.tab_crypt, self.tab_hunt, self.tab_ref, self.tab_roy, self.tab_chest, self._cal_frame)
        for f in _all:
            f.pack_forget()
        self._cal_btn.configure(fg_color=MD3["elevated"], hover_color=MD3["card"])
        self._cal_visible = False
        tab_map = {
            "tab_crypt": self.tab_crypt,
            "tab_hunt":  self.tab_hunt,
            "tab_ref":   self.tab_ref,
            "tab_roy":   self.tab_roy,
            "tab_chest": self.tab_chest,
        }
```

- [ ] **Step 6: Add "tab_chest" to `change_lang`'s tab-name refresh**

Find (around line 3534):

```python
        new_names = {k: LANGS[val][k] for k in ("tab_crypt", "tab_hunt", "tab_roy", "tab_ref")}
```

Replace with:

```python
        new_names = {k: LANGS[val][k] for k in ("tab_crypt", "tab_hunt", "tab_roy", "tab_ref", "tab_chest")}
```

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat(chest-tab): wire tab into segmented button and show/hide logic"
```

---

## Task 8: `main.py` — `setup_chest_tab()` GUI builder

**Files:**
- Modify: `C:\BattleBot\main.py` (add a new method `setup_chest_tab`, placed directly after `setup_ref_tab` — find the end of `setup_ref_tab` by locating the next `def setup_calibration_tab` and insert the new method immediately before it)

- [ ] **Step 1: Locate the insertion point**

Run: `grep -n "def setup_calibration_tab" main.py`
Expected: one match (around line 3626, per Task 8's exploration — re-check the current line number since Task 6/7 edits shifted line numbers, then insert `setup_chest_tab` immediately before that line).

- [ ] **Step 2: Add the `setup_chest_tab` method**

Insert immediately before `def setup_calibration_tab(self):`:

```python
    def setup_chest_tab(self):
        L = LANGS[self.current_lang]

        title_lb = ctk.CTkLabel(self.tab_chest, text=L["tab_chest"],
                                font=ctk.CTkFont(size=20, weight="bold"),
                                text_color=MD3["primary"])
        title_lb.pack(pady=(14, 8))
        self._i18n_labels.append((title_lb, "tab_chest"))

        # ── Королевство / Клан ────────────────────────────────────────────
        id_card = ctk.CTkFrame(self.tab_chest, fg_color=MD3["elevated"],
                               corner_radius=12, border_width=1,
                               border_color=MD3["outline"])
        id_card.pack(padx=20, pady=(0, 8), fill="x")

        kingdom_row = ctk.CTkFrame(id_card, fg_color="transparent")
        kingdom_row.pack(padx=10, pady=(10, 4), fill="x")
        self.chest_kingdom_lb = ctk.CTkLabel(kingdom_row, text=L["chest_kingdom_lb"],
                                             font=ctk.CTkFont(size=12),
                                             text_color=MD3["on_surface2"])
        self.chest_kingdom_lb.pack(side="left", padx=(0, 8))
        self.chest_kingdom_entry = ctk.CTkEntry(kingdom_row, width=120)
        self.chest_kingdom_entry.pack(side="left")
        saved_kingdom = self._load_gui_config().get("chest_kingdom", "")
        if saved_kingdom:
            self.chest_kingdom_entry.insert(0, saved_kingdom)
        self.chest_kingdom_entry.bind("<FocusOut>", self._on_chest_kingdom_change)

        clan_row = ctk.CTkFrame(id_card, fg_color="transparent")
        clan_row.pack(padx=10, pady=(4, 10), fill="x")
        self.chest_clan_lb = ctk.CTkLabel(clan_row, text=L["chest_clan_lb"],
                                          font=ctk.CTkFont(size=12),
                                          text_color=MD3["on_surface2"])
        self.chest_clan_lb.pack(side="left", padx=(0, 8))
        self.chest_clan_entry = ctk.CTkEntry(clan_row, width=160)
        self.chest_clan_entry.pack(side="left")
        saved_clan = self._load_gui_config().get("chest_clan", "")
        if saved_clan:
            self.chest_clan_entry.insert(0, saved_clan)
        self.chest_clan_entry.bind("<FocusOut>", self._on_chest_clan_change)

        # ── Старт/Стоп + статус ──────────────────────────────────────────
        self.chest_start_btn = ctk.CTkButton(
            self.tab_chest, text=L["chest_start_btn"],
            height=42, corner_radius=10,
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self.toggle_chest_bot)
        self.chest_start_btn.pack(padx=20, pady=(4, 4), fill="x")

        self.chest_status_label = ctk.CTkLabel(self.tab_chest, text=L["chest_status_ready"],
                                               font=ctk.CTkFont(size=12),
                                               text_color=MD3["on_surface2"])
        self.chest_status_label.pack(pady=(0, 8))

        # ── Live-счётчик по типам ────────────────────────────────────────
        counts_card = ctk.CTkFrame(self.tab_chest, fg_color=MD3["elevated"],
                                   corner_radius=12, border_width=1,
                                   border_color=MD3["outline"])
        counts_card.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        self.chest_counts_frame = ctk.CTkFrame(counts_card, fg_color="transparent")
        self.chest_counts_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.chest_total_label = ctk.CTkLabel(counts_card, text=f"{L['chest_total_lb']} 0",
                                              font=ctk.CTkFont(size=13, weight="bold"),
                                              text_color=MD3["value_text"])
        self.chest_total_label.pack(pady=(0, 10))

        # ── Отправить на сервер ──────────────────────────────────────────
        self.chest_send_btn = ctk.CTkButton(
            self.tab_chest, text=L["chest_send_btn"],
            height=38, corner_radius=10,
            fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=13, weight="bold"),
            command=self.send_chests_to_server)
        self.chest_send_btn.pack(padx=20, pady=(0, 14), fill="x")

    def _on_chest_kingdom_change(self, event=None):
        self._save_gui_config_key("chest_kingdom", self.chest_kingdom_entry.get().strip())

    def _on_chest_clan_change(self, event=None):
        self._save_gui_config_key("chest_clan", self.chest_clan_entry.get().strip())

    def _update_chest_counts_display(self, counts):
        for child in self.chest_counts_frame.winfo_children():
            child.destroy()
        total = 0
        for chest_type, n in counts.items():
            total += n
            row_lb = ctk.CTkLabel(self.chest_counts_frame, text=f"{chest_type}: {n}",
                                  font=ctk.CTkFont(size=12), text_color=MD3["on_surface"])
            row_lb.pack(anchor="w", pady=1)
        L = LANGS[self.current_lang]
        self.chest_total_label.configure(text=f"{L['chest_total_lb']} {total}")
```

- [ ] **Step 3: Verify the app still launches**

Run: `python main.py`
Expected: the app window opens without a traceback (it will raise `AttributeError: 'TotalHunterApp' object has no attribute 'toggle_chest_bot'`/`'send_chests_to_server'` — that's expected and resolved by Task 9. If it raises anything else — e.g. a `KeyError` from a missing LANGS key, or a widget-layout exception — stop and fix before proceeding).

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(chest-tab): GUI builder (kingdom/clan fields, live counter, buttons)"
```

---

## Task 9: `main.py` — start/stop/send wiring + ESC integration

**Files:**
- Modify: `C:\BattleBot\main.py` (add `toggle_chest_bot`, `_on_chest_collection_done`, `send_chests_to_server` methods near the other `toggle_*_bot` methods — e.g. right after `toggle_crypt_bot`, around line 2229 pre-edit)
- Modify: `C:\BattleBot\main.py:2933-2969` (`_emergency_stop`)

- [ ] **Step 1: Add `toggle_chest_bot` and `_on_chest_collection_done`**

Insert as new methods (e.g. directly after `toggle_crypt_bot`'s closing line):

```python
    def toggle_chest_bot(self):
        L = LANGS[self.current_lang]
        if self._chest_running:
            self._chest_stop_event.set()
            return

        import chest_reader
        frame = chest_reader.grab_fullscreen()
        bbox = chest_reader.detect_dialog_bbox(frame)
        if bbox is None:
            self.chest_status_label.configure(text=L["chest_status_no_dialog"],
                                              text_color=MD3["error_text"])
            return

        self._chest_running = True
        self._chest_stop_event = threading.Event()
        self._update_chest_counts_display({})
        self.chest_start_btn.configure(text=L["chest_stop_btn"],
                                       fg_color=MD3["error"], hover_color=MD3["error_hover"])
        self.chest_status_label.configure(text=L["chest_status_running"],
                                          text_color=MD3["secondary"])

        stop_event = self._chest_stop_event

        def _on_update(counts):
            self.after(0, lambda c=dict(counts): self._update_chest_counts_display(c))

        def _worker():
            result = chest_reader.collect_chests(stop_event.is_set, on_update=_on_update)
            self.after(0, lambda: self._on_chest_collection_done(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_chest_collection_done(self, result):
        L = LANGS[self.current_lang]
        self._chest_running = False
        self.chest_start_btn.configure(text=L["chest_start_btn"],
                                       fg_color=MD3["green_btn"], hover_color=MD3["green_hover"])
        self.chest_status_label.configure(text=L["chest_status_stopped"],
                                          text_color=MD3["on_surface2"])
        self._update_chest_counts_display(result.get("counts", {}))

    def send_chests_to_server(self):
        L = LANGS[self.current_lang]
        kingdom = self.chest_kingdom_entry.get().strip()
        clan = self.chest_clan_entry.get().strip()
        if not kingdom or not clan:
            self.chest_status_label.configure(text=L["chest_missing_fields"],
                                              text_color=MD3["error_text"])
            return

        def _worker():
            import chest_reader
            conn = chest_reader.init_db()
            rows = chest_reader.get_unsynced(conn)
            if not rows:
                conn.close()
                return

            from auth import spend_credit
            res = spend_credit(hunt_type="chest")
            if not (res and res.get("success")):
                conn.close()
                self.after(0, lambda: messagebox.showwarning("Hunter", L["no_credits"]))
                return

            items = [{"chest_type": r[2], "sender": r[1], "timestamp": r[3]} for r in rows]
            ids = [r[0] for r in rows]
            success = chest_reader.export_to_api(kingdom, clan, items)
            if success:
                chest_reader.mark_synced(conn, ids)
            conn.close()

            def _update():
                if success:
                    self.chest_status_label.configure(text=L["chest_send_success"],
                                                       text_color=MD3["secondary"])
                else:
                    self.chest_status_label.configure(text=L["chest_send_failed"],
                                                       text_color=MD3["error_text"])
            self.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()
```

- [ ] **Step 2: Add chest-collection stop to `_emergency_stop` (ESC)**

Find (around line 2963-2966, right after the crypt-stop block and before the Combo block):

```python
        # Combo (заморожен — guard на случай если engine не инициализирован)
        if self.is_combo_running and hasattr(self, 'combo_engine'):
            self.is_combo_running = False
            self.combo_engine.stop()
```

Replace with:

```python
        # Сундуки
        if self._chest_running:
            self._chest_stop_event.set()
        # Combo (заморожен — guard на случай если engine не инициализирован)
        if self.is_combo_running and hasattr(self, 'combo_engine'):
            self.is_combo_running = False
            self.combo_engine.stop()
```

(Note: setting the event is enough — the worker thread's `_on_chest_collection_done` callback resets the button/status text once `collect_chests` notices the flag and returns; no separate button-text update needed here, unlike crypt/exchange which call `engine.stop()` synchronously.)

- [ ] **Step 3: Manual verification (cannot be unit-tested — requires the live game)**

Run: `python main.py`

Checklist — perform each, confirm the described behavior, fix anything that doesn't match before considering this task done:
1. Switch through all language options in the language dropdown — app must not crash, "СУНДУКИ"/"CHESTS" tab label must appear in the segmented control for every language.
2. Click the "СУНДУКИ"/"CHESTS" segment — the tab must show Kingdom/Clan fields, a green "СТАРТ"/"START" button, status label, empty counter area, and a blue "ОТПРАВИТЬ НА СЕРВЕР"/"SEND TO SERVER" button.
3. With the in-game «Мой клан → Подарки» dialog **closed**, click "СТАРТ" — status label must show `chest_status_no_dialog` text, button must stay green/unstarted.
4. Open «Мой клан → Подарки» in the game (at least 2-3 chests in the list), click "СТАРТ" — button turns red/"СТОП", status shows "Сбор сундуков...". Confirm:
   - The bot clicks the top row's «Открыть» button repeatedly without scrolling.
   - The live counter list updates after each click with the correct chest type and running count.
   - When the list becomes empty, the bot stops on its own, button returns to green/"СТАРТ", status shows "Остановлено".
5. Repeat step 4 but press ESC mid-run — collection must stop immediately, button must return to green within ~1 collection-loop iteration.
6. Enter Kingdom/Clan, click "ОТПРАВИТЬ НА СЕРВЕР" — since `/api/v1/chests/import` does not exist yet, expect `chest_send_failed` status text (server unavailable) and confirm via `sqlite3 chest_buffer.db "select count(*) from local_chests where is_synced=0"` that the rows are still buffered (not lost, not marked synced).
7. Restart the app and confirm Kingdom/Clan fields are still filled in (persisted via `gui_config.json`).

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(chest-tab): start/stop/send wiring, ESC stop, live counter updates"
```

---

## Self-review notes (already applied above)

- Spec coverage: dialog detection ✅ (Task 1), OCR+cleanup ✅ (Task 2), SQLite buffer ✅ (Task 3), click loop/end-of-list ✅ (Task 4), server export ✅ (Task 5), Kingdom/Clan fields ✅ (Task 8), billing via `spend_credit(hunt_type="chest")` ✅ (Task 9), ESC stop ✅ (Task 9), live counters ✅ (Task 8/9), persisted fields ✅ (Task 8), tab ordering after РЕФЕРАЛЫ/before Калибровка ✅ (Task 7 — `tab_chest` is appended last in the segmented tuple; Калибровка is a separate toggle button outside the segmented control, so being last in the segment already satisfies "before Калибровка").
- Alias Map / admin panel / 2-week server-side aggregation — explicitly out of scope per the spec ("future, not this implementation").
- `hunt_type="chest"` passed to `auth.spend_credit` assumes the server's `/use_credit` endpoint will recognize it — it currently doesn't (server-side work, not in this plan); until then `spend_credit` will return a falsy/`success: False` result and `send_chests_to_server` will surface `no_credits`-style messaging without spending anything, which is safe (no silent free sends, no crash).
