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

import cv2
import numpy as np
import mss
import pyautogui
import pytesseract
import requests

from auth import SERVER_URL, get_hwid
from button_finder import find_colored_button
from coord_manager import coord_manager
from tesseract_setup import configure_pytesseract

configure_pytesseract(pytesseract)

# --- Dialog detection (same tan/gold frame as tournament_reader.py) -------
DIALOG_HSV_LOWER = (10, 20, 150)
DIALOG_HSV_UPPER = (40, 120, 255)
MIN_DIALOG_DIM = 200  # guard against a 1-2px degenerate bbox on a glitched frame

# --- Row geometry — no scroll, only the top row is ever read --------------
ROW_PITCH = 100

# --- Sender name and chest source: fixed coordinates, not a relative crop.
# The dialog's render/composition never changes (always the same UI, same
# position relative to the game window), so both fields always land in the
# same spot — calibrated 2026-06-18 via coord_picker.py against the live
# game. Reference coords at the project's эталон 1920x1080; coord_manager
# scales/offsets them to the real screen per calibration profile, same as
# every other coordinate in this project. Neither crop includes its label
# ("От:" / "Источник:"), so no regex-stripping of a prefix is needed.
SENDER_REF_RECT = (816, 375, 361, 24)
# "Источник:" line — identifies what dropped the chest (e.g. "Эпический
# отряд нежити"). Used as chest_type instead of the generic title line
# ("Сундук Эпического Монстра"), since the title alone doesn't distinguish
# between different drop sources.
SOURCE_REF_RECT = (865, 398, 371, 24)

# --- «Открыть» button search box (relative to the top row) ----------------
BUTTON_X_FRAC = (0.78, 1.0)
BUTTON_Y_FRAC = (0.45, 1.0)

# --- Anti-detect click ------------------------------------------------------
ANTI_DETECT_OFFSET_PX = 8
ANTI_DETECT_PAUSE_RANGE = (0.16, 0.28)  # reduced again 2026-06-19 by owner decision, chests-only

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


def preprocess_for_ocr(roi):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binary = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def ocr_text(roi, psm=7, lang='rus+eng', extra_config=''):
    processed = preprocess_for_ocr(roi)
    config = f'--psm {psm} {extra_config}'.strip()
    return pytesseract.image_to_string(processed, config=config, lang=lang, timeout=5).strip()


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


def read_top_row(frame):
    chest_type = read_chest_type(frame)
    sender = read_sender_name(frame)
    return chest_type, sender


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


def get_unsynced_counts(conn):
    """{chest_type: count} for is_synced=0 rows — single source of truth for the
    displayed unsynced backlog (live ticker, post-stop display, tab-open display)."""
    cur = conn.execute(
        'SELECT chest_type, COUNT(*) FROM local_chests WHERE is_synced = 0 '
        'GROUP BY chest_type'
    )
    return {chest_type: n for chest_type, n in cur.fetchall()}


def mark_synced(conn, ids):
    conn.executemany('UPDATE local_chests SET is_synced = 1 WHERE id = ?', [(i,) for i in ids])
    conn.commit()


def find_open_button(bbox):
    x, y, w, h = bbox
    region = (
        x + int(w * BUTTON_X_FRAC[0]),
        y + int(ROW_PITCH * BUTTON_Y_FRAC[0]),
        int(w * (BUTTON_X_FRAC[1] - BUTTON_X_FRAC[0])),
        int(ROW_PITCH * (BUTTON_Y_FRAC[1] - BUTTON_Y_FRAC[0])),
    )
    return find_colored_button(region, color='green', pick='largest')


def click_open_button(pos, pause_range=ANTI_DETECT_PAUSE_RANGE):
    cx, cy = pos
    click_x = cx + random.randint(-ANTI_DETECT_OFFSET_PX, ANTI_DETECT_OFFSET_PX)
    click_y = cy + random.randint(-5, 5)
    pyautogui.click(click_x, click_y)
    time.sleep(random.uniform(*pause_range))


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

            click_open_button(pos, pause_range)

        final_counts = get_unsynced_counts(conn)
    finally:
        conn.close()

    return {'counts': final_counts, 'items': items}


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
        if response.status_code == 402:
            return {"success": False, "low_credits": True}
        if 200 <= response.status_code < 300:
            return {"success": True}
        return {"success": False}
    except requests.RequestException:
        return {"success": False}
