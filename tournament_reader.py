import re
import sys
import json
import time
import random
import datetime

# OCR garbage on rare/exotic glyphs can land outside the console's active
# codepage (e.g. cp1251) — without this, a single such character crashes the
# whole scan via print() and loses every row collected so far.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

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
# A scroll(-2) that produces zero measured pixel shift (see
# measure_scroll_shift) means the scrollbar is maxed out. Require 2 in a row
# to rule out a single noisy/glitched matchTemplate measurement.
END_OF_LIST_ZERO_SHIFTS = 2

# --- Scroll-shift measurement: exclude the scrollbar strip on the right
# edge of the dialog from the matchTemplate template/search area.
SCROLLBAR_MARGIN = 0.05

# --- Anti-AFK: the game shows an ad popup after ~3 min without a click,
# which covers the dialog and breaks measure_scroll_shift. A periodic click
# on the dialog header (no buttons there) resets the game's AFK timer.
ANTI_AFK_INTERVAL_SEC = 180
ANTI_AFK_HEADER_Y_FRAC = 0.03

# --- Capture sanity check ---
# detect_dialog_bbox occasionally returns a near-degenerate bbox on a glitched
# frame (1-2px tall). Such a frame must never reach row/own-row extraction -
# it can produce empty crops and crash cv2. 200px ~= 2 rows.
MIN_DIALOG_DIM = 200

# --- OCR ---
OCR_THRESHOLD = 150
PLACE_OCR_THRESHOLD = 130

# --- Name OCR: a fixed threshold binarizes some row backgrounds to a
# uniformly black/white image, losing the text entirely (confirmed via
# debug_name_crops/ - visually readable text, empty OCR at every fixed
# threshold). Otsu picks a threshold per-ROI; the INV variant covers rows
# where Otsu inverts text vs background.
NAME_MIN_LENGTH = 2

# VIP badge (bright gold icon + white digit, placed right after the name)
# gets read by every Otsu candidate as garbage trailing letters — Tesseract
# tries to read the badge glyphs since Otsu's per-ROI threshold doesn't
# reliably wash it out. Name text is much darker than both the badge and
# the row background, so a fixed threshold tuned below the badge's
# brightness erases the badge before Tesseract ever sees it. Confirmed
# live against a real VIP-badge crop: threshold 90 + psm 7 gave a clean
# "DNIPRO" where every Otsu candidate produced "DNIPRO 'ay"-style noise —
# and also fixed unrelated misreads on plain rows (e.g. "Conquest Georgio"
# correctly, where Otsu read "Со nquest Georgio"). Tried first; falls back
# to the Otsu sweep (which the badge problem doesn't fully explain away —
# see comment above on backgrounds that lose all text at any fixed
# threshold) only when this pass is empty.
NAME_BADGE_THRESHOLD = 90

# --- Config / API ---
from auth import SERVER_URL, get_hwid

API_IMPORT_PATH = '/api/v1/tournaments/import'


def detect_dialog_bbox(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, DIALOG_HSV_LOWER, DIALOG_HSV_UPPER)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError("Диалог «Статистика» не найден на экране")
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
    if row_top < 0:
        row_top = merged[0]
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


def preprocess_for_ocr_otsu(roi, invert=False):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    method = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(resized, 0, 255, method + cv2.THRESH_OTSU)
    return binary


# Player name: stylized/unpredictable — dictionaries only hurt here (they force
# Tesseract to "correct" unfamiliar glyph shapes into known dictionary words, which is
# exactly what splits a name like "Conquest" into "Со nquest"). Disabling DAWG reads
# any script literally instead. Two language sets, same split and same rationale as
# chest_reader.py's read_sender_name: LIGHT (fast, Latin+Cyrillic) covers most clans;
# FULL (all 19 bot-supported languages) adds Arabic/Japanese/Chinese/Korean for clans
# that actually need it, at the cost of more cross-script confusion on plain names —
# confirmed live: FULL alone misreads "[K229] Scaramouche" as "1229] Scaramouche".
#
# Tried and reverted: a confidence-based candidate picker (image_to_data mean word
# confidence) plus an adaptive-threshold+FULL-lang escalation pass on low confidence,
# per an external review's recommendation. Live-tested worse than this simpler
# version — Tesseract reads garbage from noisy/textured crops with high *and*
# confident-looking per-word scores just as often as it reads real text, so the
# escalation pass would confidently overwrite a correct first-pass name with garbage
# (e.g. "VikTor Я" → "VikTor Я — р. » a m >= Aun ea Hoa"). Do not re-add without a much
# stronger plausibility check than raw mean confidence.
LIGHT_NAME_OCR_LANG = 'rus+eng+script/Latin'
FULL_NAME_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'
NAME_OCR_CONFIG = '-c load_system_dawg=0 -c load_freq_dawg=0'


def ocr_text_otsu(roi, invert=False, psm=7, lang='rus+eng', extra_config=''):
    processed = preprocess_for_ocr_otsu(roi, invert=invert)
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


def clean_points(text):
    digits = re.sub(r'[^\d]', '', text)
    if not digits:
        return None
    return int(digits)


def ocr_name(roi, full_lang=False):
    lang = FULL_NAME_OCR_LANG if full_lang else LIGHT_NAME_OCR_LANG

    # Badge-erasing fixed-threshold pass first (see NAME_BADGE_THRESHOLD).
    # Trusted outright when non-empty — NOT pooled with the Otsu candidates
    # below and picked by length, since badge garbage tends to make the
    # Otsu candidates *longer*, which would make a naive max(len) pick the
    # contaminated result over this clean one.
    processed = preprocess_for_ocr(roi, threshold=NAME_BADGE_THRESHOLD)
    config = f'--psm 7 {NAME_OCR_CONFIG}'.strip()
    text = pytesseract.image_to_string(processed, config=config, lang=lang, timeout=5).strip()
    name = clean_name(text.splitlines()[0] if text else '')
    if len(name) >= NAME_MIN_LENGTH:
        return name

    candidates = []
    for psm, invert in ((7, False), (7, True), (6, True), (6, False)):
        text = ocr_text_otsu(roi, invert=invert, psm=psm, lang=lang, extra_config=NAME_OCR_CONFIG)
        first_line = text.splitlines()[0] if text else ''
        name = clean_name(first_line)
        if len(name) >= NAME_MIN_LENGTH:
            candidates.append(name)

    if not candidates:
        return ''
    return max(candidates, key=len)


def ocr_row(name_roi, pts_roi, full_lang=False):
    name = ocr_name(name_roi, full_lang=full_lang)
    pts_text = ocr_text(pts_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')
    return name, clean_points(pts_text)


def get_own_row(dialog):
    h = dialog.shape[0]
    top = int(h * OWN_ROW_Y_FRAC[0])
    return dialog[top:h, :]


def get_own_row_crops(own_row):
    place_roi = _sub_roi(own_row, PLACE_X_FRAC, PLACE_Y_FRAC)
    name_roi = _sub_roi(own_row, NAME_X_FRAC, NAME_Y_FRAC)
    pts_roi = _sub_roi(own_row, PTS_X_FRAC, PTS_Y_FRAC)
    return place_roi, name_roi, pts_roi


def ocr_own_row(place_roi, name_roi, pts_roi, full_lang=False):
    place_text = ocr_text(place_roi, threshold=PLACE_OCR_THRESHOLD, psm=6, lang='rus+eng', whitelist='0123456789')
    name = ocr_name(name_roi, full_lang=full_lang)
    pts_text = ocr_text(pts_roi, threshold=OCR_THRESHOLD, psm=7, lang='rus+eng')

    rank = int(place_text) if place_text.isdigit() else None
    return {
        'rank': rank,
        'name': name,
        'points': clean_points(pts_text),
    }


def measure_scroll_shift(prev_dialog, curr_dialog, pitch, row_top):
    """Returns the pixel shift between two consecutive dialog captures, or
    None if the frames aren't comparable (e.g. a 1-2px detection-jitter
    difference in dialog size between frames — not a real window resize,
    this game's dialogs are fixed-size; just a transient capture glitch).
    Callers must treat None as "retry this frame", never as a real
    zero-shift (which means "end of list reached")."""
    prev_h, prev_w = prev_dialog.shape[:2]
    curr_h, curr_w = curr_dialog.shape[:2]

    template_y0 = row_top + pitch
    template_y1 = row_top + 2 * pitch
    template_x1 = int(prev_w * (1 - SCROLLBAR_MARGIN))
    template = prev_dialog[template_y0:template_y1, 0:template_x1]

    search_y0 = int(curr_h * OWN_ROW_Y_FRAC[0])
    search_x1 = int(curr_w * (1 - SCROLLBAR_MARGIN))
    search = curr_dialog[0:search_y0, 0:search_x1]

    if search.shape[0] < template.shape[0] or search.shape[1] < template.shape[1]:
        return None

    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    return template_y0 - max_loc[1]


def anti_afk_click(bbox):
    x, y, w, h = bbox
    click_x = x + w // 2 + random.randint(-8, 8)
    click_y = y + int(h * ANTI_AFK_HEADER_Y_FRAC) + random.randint(-5, 5)
    pyautogui.click(click_x, click_y)


def collect_tournament_data(stop_flag=None, full_lang=False):
    """Scrolls and OCRs the tournament leaderboard dialog until the end of
    the list is reached or stop_flag() returns True. On early stop, returns
    whatever rows were collected so far (same partial-result convention as
    chest_reader.collect_chests). full_lang switches name OCR to the slower
    8-script set for clans with Arabic/Japanese/Chinese/Korean nicknames —
    see LIGHT_NAME_OCR_LANG/FULL_NAME_OCR_LANG."""
    if stop_flag is None:
        stop_flag = lambda: False
    next_place = STARTING_RANK
    remainder_px = 0
    zero_shift_streak = 0
    prev_dialog = None
    leaderboard = []
    dialog = None

    # One-time click to focus the game window — the always-on-top bot GUI
    # keeps scroll focus after "Start"; without this, scroll(-2) goes to the
    # bot instead of the game. anti_afk_click handles re-focus every 3 min.
    try:
        _init_frame = grab_fullscreen()
        _init_bbox = detect_dialog_bbox(_init_frame)
        hdr_x = _init_bbox[0] + _init_bbox[2] // 2
        hdr_y = _init_bbox[1] + int(_init_bbox[3] * ANTI_AFK_HEADER_Y_FRAC)
        pyautogui.click(hdr_x, hdr_y)
        time.sleep(0.3)
    except Exception:
        pass  # dialog not yet visible — loop will handle it

    last_click_time = time.time()

    while not stop_flag():
        frame = grab_fullscreen()
        bbox = detect_dialog_bbox(frame)
        dialog = crop_dialog(frame, bbox)

        if dialog.shape[0] < MIN_DIALOG_DIM or dialog.shape[1] < MIN_DIALOG_DIM:
            time.sleep(0.2)
            continue

        pitch, row_top = detect_row_pitch(dialog)
        if pitch is None:
            time.sleep(0.2)
            continue

        rows = get_row_crops(dialog, pitch, row_top)

        if prev_dialog is None:
            new_rows = NUM_VISIBLE_ROWS
        else:
            shift_px = measure_scroll_shift(prev_dialog, dialog, pitch, row_top)
            if shift_px is None:
                # transient capture glitch, not a real zero-shift — retry
                # without advancing prev_dialog or touching zero_shift_streak
                time.sleep(0.2)
                continue
            if shift_px <= 0:
                zero_shift_streak += 1
                if zero_shift_streak >= END_OF_LIST_ZERO_SHIFTS:
                    break
                new_rows = 0
            else:
                zero_shift_streak = 0
                remainder_px += shift_px
                new_rows = min(remainder_px // pitch, NUM_VISIBLE_ROWS)
                remainder_px -= new_rows * pitch

        for name_roi, pts_roi in rows[NUM_VISIBLE_ROWS - new_rows:]:
            name, points = ocr_row(name_roi, pts_roi, full_lang=full_lang)
            print(f"место {next_place}: {name} — {points}")
            leaderboard.append({'rank': next_place, 'name': name, 'points': points})
            next_place += 1

        prev_dialog = dialog

        if time.time() - last_click_time >= ANTI_AFK_INTERVAL_SEC:
            anti_afk_click(bbox)
            last_click_time = time.time()

        pyautogui.moveTo(bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2, duration=0.05)
        pyautogui.scroll(-2)
        time.sleep(random.uniform(0.4, 0.9))

    own_data = None
    if dialog is not None:
        own_row = get_own_row(dialog)
        place_roi, name_roi, pts_roi = get_own_row_crops(own_row)
        own_data = ocr_own_row(place_roi, name_roi, pts_roi, full_lang=full_lang)

    return {'leaderboard': leaderboard, 'own_data': own_data}


def export_to_api(kingdom, clan, data, event_timestamp):
    items = list(data["leaderboard"])
    if data.get("own_data"):
        own_name = data["own_data"].get("name")
        if own_name and not any(row.get("name") == own_name for row in items):
            items.append(data["own_data"])

    payload = {
        "hwid": get_hwid(),
        "kingdom": kingdom,
        "clan": clan,
        "timestamp": event_timestamp,
        "items": [
            {"name": row["name"], "place": row.get("rank"), "points": row.get("points")}
            for row in items if row.get("name")
        ],
    }
    url = SERVER_URL + API_IMPORT_PATH

    try:
        response = requests.post(url, json=payload, timeout=10)
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
    if len(sys.argv) < 3:
        print("Использование: python tournament_reader.py <kingdom> <clan> [full]")
        print("  full — необязательный флаг: распознавать имена с арабским/японским/"
              "китайским/корейским алфавитом (медленнее, для клана с такими никами)")
        return
    kingdom, clan = sys.argv[1], sys.argv[2]
    full_lang = len(sys.argv) >= 4 and sys.argv[3].lower() == 'full'

    print("Откройте диалог «Статистика» в игре. Сбор начнётся через 3 секунды...")
    for i in (3, 2, 1):
        print(i)
        time.sleep(1)

    data = collect_tournament_data(full_lang=full_lang)

    print(f"Собрано строк: {len(data['leaderboard'])}")
    print(f"Своё место: {data['own_data']}")

    event_timestamp = datetime.datetime.now().isoformat(timespec='seconds')
    success = export_to_api(kingdom, clan, data, event_timestamp)

    if success:
        print("Данные успешно отправлены на сервер.")
    else:
        print("Данные сохранены локально (см. сообщение выше).")


if __name__ == '__main__':
    main()
