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
