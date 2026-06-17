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
