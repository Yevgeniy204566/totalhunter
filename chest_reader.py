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
