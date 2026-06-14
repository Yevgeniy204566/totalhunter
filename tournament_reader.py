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


def detect_dialog_bbox(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, DIALOG_HSV_LOWER, DIALOG_HSV_UPPER)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
