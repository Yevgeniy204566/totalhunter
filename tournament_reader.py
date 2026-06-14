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


def clean_name(text):
    text = re.sub(r'^\[.*?\]\s*', '', text)
    text = re.sub(r'\s+\S{1,3}$', '', text)
    return text.strip()


def clean_points(text):
    digits = re.sub(r'[^\d]', '', text)
    if not digits:
        return None
    return int(digits)


def ocr_row(name_roi, pts_roi):
    name_text = ocr_text(name_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')
    pts_text = ocr_text(pts_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')
    return clean_name(name_text), clean_points(pts_text)


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


def is_end_of_list(prev_dialog, curr_dialog):
    h, w = curr_dialog.shape[:2]
    scrollbar_x0 = int(w * (1 - SCROLLBAR_FRAC))
    own_y0 = int(h * OWN_ROW_Y_FRAC[0])

    prev_crop = prev_dialog[:own_y0, :scrollbar_x0]
    curr_crop = curr_dialog[:own_y0, :scrollbar_x0]

    diff = cv2.absdiff(prev_crop, curr_crop)
    return bool(diff.max() < END_DIFF_THRESHOLD)


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
        if pitch is not None:
            rows = get_row_crops(dialog, pitch, row_top)
            ocr_rows = [ocr_row(name_roi, pts_roi) for name_roi, pts_roi in rows]
            ocr_rows = [(name, points) for name, points in ocr_rows if points is not None]

            places = compute_places(ocr_rows, known_places)
            if places is not None:
                for place, (name, points) in places.items():
                    if place not in known_places:
                        print(f"место {place}: {name} — {points}")
                known_places.update(places)

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
