import os
import re
import sys
import json
import time
import random
import pathlib
import datetime

import cv2
import numpy as np
import mss
import pyautogui
import pytesseract
import requests

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Allowed capture area (MANDATORY: only this rectangle may be read) ---
# Calibrated: top-left (688,346), bottom-right (1412,709)  → w=724, h=363
_DEFAULT_PANEL = [688, 346, 724, 363]

# --- Card geometry (FIXED — cards never change size in this game) ---
PITCH = 172          # physical height of one player card in pixels

# --- OCR crop rectangles in absolute pixels FROM TOP-LEFT OF CARD ---
# Derived from КАРТОЧКА ИГРОКА.png calibration screenshot (NAME=green, MIGHT=red)
NAME_ROI_PX  = [166,  3, 485,  77]   # [x1, y1, x2, y2]
MIGHT_ROI_PX = [449, 65, 709, 117]   # [x1, y1, x2, y2]

# --- Known rank separator labels (uppercase) ---
KNOWN_RANKS = {'ГЛАВА', 'СТАРШИЙ', 'ОФИЦЕР', 'ВЕТЕРАН', 'РЯДОВОЙ'}

NAME_MIN_LENGTH = 2

# --- End-of-list detection ---
END_OF_LIST_ZERO_SHIFTS = 2

# --- Scrollbar strip excluded from matchTemplate ---
SCROLLBAR_MARGIN = 0.05

# --- Anti-AFK ---
ANTI_AFK_INTERVAL_SEC = 240
ANTI_AFK_X = 1157
ANTI_AFK_Y = 416

# --- Debug photos ---
DEBUG_DIR = pathlib.Path(__file__).parent / '_clan_debug'


def _dbg_save(img, name):
    DEBUG_DIR.mkdir(exist_ok=True)
    cv2.imwrite(str(DEBUG_DIR / name), img)


# --- Config / API ---
CONFIG_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roster_config.json')
API_ROSTER_PATH = '/api/v1/clan/roster'


# ─── Screen capture ────────────────────────────────────────────────────────

def grab_fullscreen():
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        frame = np.array(shot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def grab_panel(panel_bbox):
    """Capture ONLY the allowed rectangle. Nothing outside."""
    px, py, pw, ph = panel_bbox
    frame = grab_fullscreen()
    return frame[py:py + ph, px:px + pw]


# ─── Profile loading ────────────────────────────────────────────────────────

def _load_profile():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gui_cfg  = os.path.join(base_dir, 'gui_config.json')
    name     = 'client'
    if os.path.exists(gui_cfg):
        with open(gui_cfg, 'r', encoding='utf-8') as f:
            name = json.load(f).get('last_calibration_profile', 'client').lower()
    path = os.path.join(base_dir, 'profiles', f'profile_{name}.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f), path


def _load_panel_bbox():
    profile, _ = _load_profile()
    coords = profile.get('clan_panel_screen', _DEFAULT_PANEL)
    return tuple(int(c) for c in coords)   # (x, y, w, h)


def _load_tab_coords():
    profile, profile_path = _load_profile()
    from coord_manager import coord_manager as _cm
    _cm.load(profile_path)
    raw_tabs = profile.get('clan_roster_tabs', {})
    if not raw_tabs:
        raise ValueError("clan_roster_tabs не найдены в профиле.")
    return {rank: tuple(_cm.to_screen(int(rx), int(ry))) for rank, (rx, ry) in raw_tabs.items()}


# ─── OCR helpers ───────────────────────────────────────────────────────────

def _preprocess_otsu(roi, invert=False):
    gray    = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    flag    = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, out  = cv2.threshold(resized, 0, 255, flag + cv2.THRESH_OTSU)
    return out


def _ocr_otsu(roi, invert=False, psm=7, lang='rus+eng'):
    return pytesseract.image_to_string(
        _preprocess_otsu(roi, invert), config=f'--psm {psm}', lang=lang, timeout=5
    ).strip()


# ─── Member name OCR ───────────────────────────────────────────────────────

def _clean_member_name(text):
    # Remove activity timers ("Был 24:59 м назад", "Был 11ч: 21м назад", etc.)
    text = re.sub(r'(?i)был[а-яёА-ЯЁa-z0-9\s:.,©\-]*назад', '', text)
    text = re.sub(r'(?i)в\s*сети',                           '', text)
    text = re.sub(r'\d+[чмh:]+\s*\d*\s*назад',              '', text, flags=re.IGNORECASE)
    # Standard cleanup
    text = re.sub(r'^\[.*?\]\s*',                    '', text)
    text = re.sub(r'\s*\(.*',                        '', text, flags=re.DOTALL)
    text = re.sub(r'\s*[KКXХYУkxy]:\d+.*',          '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'^[^Ѐ-ӿa-zA-Z_-]+',             '', text)
    # Strip 1-2 char OCR artifact from rank-badge icon at left edge
    text = re.sub(r'^[а-яёА-ЯЁ]{1,2}\s+(?=\S{2,})', '', text)
    text = re.sub(r'^[a-z]{1,2}\s+(?=\S{2,})',       '', text)
    text = re.sub(r'\s+\S{1,3}$',                    '', text)
    while True:
        s = re.sub(r'\s+(?:\d{1,3}|\S{1})$', '', text)
        if s == text:
            break
        text = s
    text = re.sub(r'[^\w]+$', '', text, flags=re.UNICODE)
    return text.strip()


def ocr_member_name(card_img):
    x1, y1, x2, y2 = NAME_ROI_PX
    name_roi = card_img[y1:y2, x1:x2]
    candidates = []
    for psm, inv in ((7, False), (7, True), (6, True), (6, False)):
        raw  = _ocr_otsu(name_roi, invert=inv, psm=psm, lang='rus+eng')
        line = raw.splitlines()[0] if raw else ''
        name = _clean_member_name(line)
        if len(name) >= NAME_MIN_LENGTH:
            candidates.append(name)
    return max(candidates, key=len) if candidates else ''


# ─── Might OCR ─────────────────────────────────────────────────────────────

def _clean_might(text):
    digits = re.sub(r'[^\d]', '', text)
    return int(digits) if digits else None


def ocr_member_might(card_img):
    x1, y1, x2, y2 = MIGHT_ROI_PX
    might_roi = card_img[y1:y2, x1:x2]
    for inv in (True, False):
        text   = pytesseract.image_to_string(
            _preprocess_otsu(might_roi, inv), config='--psm 7', lang='eng', timeout=5
        ).strip()
        result = _clean_might(text)
        if result is not None:
            return result
    return None


# ─── Fuzzy dedup ───────────────────────────────────────────────────────────

FUZZY_DEDUP_MAX_DIST = 2


def _levenshtein(a, b):
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for ca in a:
        curr = [prev[0] + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j] + (ca != cb), curr[-1] + 1, prev[j + 1] + 1))
        prev = curr
    return prev[-1]


def _fuzzy_find(name, existing):
    nl = name.lower()
    for e in existing:
        if e.lower() == nl:
            return e
    if len(name) < 5:
        return None
    for e in existing:
        if _levenshtein(nl, e.lower()) <= FUZZY_DEDUP_MAX_DIST:
            return e
    return None


# ─── Scroll-shift measurement ──────────────────────────────────────────────

def _measure_scroll_shift(prev_panel, curr_panel):
    """Match second card of prev_panel inside curr_panel → returns shift in px."""
    h, w    = prev_panel.shape[:2]
    x_right = int(w * (1 - SCROLLBAR_MARGIN))
    t0      = PITCH
    t1      = 2 * PITCH
    if t1 > h:
        return 0
    template = prev_panel[t0:t1, 0:x_right]
    search   = curr_panel[0:h,   0:x_right]
    if template.shape[0] < 2 or template.shape[1] < 2:
        return 0
    if search.shape[0] < template.shape[0] or search.shape[1] < template.shape[1]:
        return 0
    _, _, _, max_loc = cv2.minMaxLoc(
        cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    )
    return t0 - max_loc[1]


# ─── Main collection loop ──────────────────────────────────────────────────

def anti_afk_click():
    pyautogui.click(ANTI_AFK_X + random.randint(-5, 5),
                    ANTI_AFK_Y + random.randint(-3, 3))


def _collect_rank_tab(rank, tab_x, tab_y, panel_bbox, max_rows=0):
    px, py, pw, ph = panel_bbox
    num_rows  = ph // PITCH          # how many full cards fit: 363 // 172 = 2
    panel_cx  = px + pw // 2
    panel_cy  = py + ph // 2

    print(f"\n[{rank}] Клик ({tab_x},{tab_y})", flush=True)
    pyautogui.moveTo(tab_x + random.randint(-3, 3),
                     tab_y + random.randint(-2, 2),
                     duration=random.uniform(0.3, 0.5))
    time.sleep(random.uniform(0.1, 0.3))
    pyautogui.click()
    time.sleep(random.uniform(0.9, 1.2))

    # Cursor stays at FIXED panel center — never moves elsewhere
    pyautogui.moveTo(panel_cx, panel_cy, duration=0.2)
    print(f"[{rank}] Курсор ({panel_cx},{panel_cy}) PITCH={PITCH}px видимых строк={num_rows}", flush=True)

    members           = {}
    prev_panel_img    = None
    remainder_px      = 0
    zero_shift_streak = 0
    last_afk_time     = time.time()
    frame_num         = 0

    while True:
        curr_panel_img = grab_panel(panel_bbox)

        if prev_panel_img is None:
            new_rows = num_rows
            print(f"[{rank}] Первый кадр: {pw}×{ph}", flush=True)
            _dbg_save(curr_panel_img, f"{rank}_frame0.png")
        else:
            shift = _measure_scroll_shift(prev_panel_img, curr_panel_img)
            if shift <= 0:
                zero_shift_streak += 1
                print(f"[{rank}] shift={shift}px zero_streak={zero_shift_streak}/{END_OF_LIST_ZERO_SHIFTS}", flush=True)
                if zero_shift_streak >= END_OF_LIST_ZERO_SHIFTS:
                    print(f"[{rank}] КОНЕЦ СПИСКА — финальный скан", flush=True)
                    for i in range(num_rows):
                        top     = i * PITCH
                        card_img = curr_panel_img[top:top + PITCH, :]
                        name    = ocr_member_name(card_img)
                        might   = ocr_member_might(card_img)
                        if not name or name.upper() in KNOWN_RANKS:
                            continue
                        _dbg_save(card_img, f"{rank}_FINAL_r{i:02d}_{name[:20]}.png")
                        if _fuzzy_find(name, list(members.keys())) is None:
                            members[name] = {'name': name, 'rank': rank, 'might': might}
                            might_str = f"{might:,}" if might else "—"
                            print(f"[{rank}]   [ADD-FINAL] '{name}' | {might_str}", flush=True)
                    break
                new_rows = 0
            else:
                zero_shift_streak = 0
                remainder_px += shift
                new_rows      = min(remainder_px // PITCH, num_rows)
                remainder_px -= new_rows * PITCH
                print(f"[{rank}] shift={shift}px remainder={remainder_px}px новых={new_rows}", flush=True)

        # Process only newly revealed cards (bottom ones)
        start_row = num_rows - new_rows
        for i in range(start_row, num_rows):
            top      = i * PITCH
            card_img = curr_panel_img[top:top + PITCH, :]
            name     = ocr_member_name(card_img)
            might    = ocr_member_might(card_img)

            if not name or name.upper() in KNOWN_RANKS:
                print(f"[{rank}]   [SKIP] row={i} кадр={frame_num}", flush=True)
                _dbg_save(card_img, f"{rank}_f{frame_num:02d}_r{i:02d}_SKIP.png")
                continue

            _dbg_save(card_img, f"{rank}_f{frame_num:02d}_r{i:02d}_{name[:20]}.png")
            canonical = _fuzzy_find(name, list(members.keys()))
            if canonical is not None:
                print(f"[{rank}]   [DEDUP] '{name}' -> '{canonical}'", flush=True)
            else:
                members[name] = {'name': name, 'rank': rank, 'might': might}
                might_str = f"{might:,}" if might else "—"
                print(f"[{rank}]   [ADD] '{name}' | {might_str}", flush=True)
                if max_rows and len(members) >= max_rows:
                    print(f"[{rank}] ЛИМИТ {max_rows} — стоп", flush=True)
                    return list(members.values())

        prev_panel_img = curr_panel_img.copy()
        frame_num += 1

        if time.time() - last_afk_time >= ANTI_AFK_INTERVAL_SEC:
            anti_afk_click()
            last_afk_time = time.time()

        pyautogui.scroll(-2)
        time.sleep(random.uniform(0.4, 0.9))

    result = list(members.values())
    print(f"[{rank}] ИТОГ: {len(result)} чел.", flush=True)
    return result


def collect_roster(max_rows=0):
    panel_bbox = _load_panel_bbox()
    tab_coords = _load_tab_coords()

    px, py, pw, ph = panel_bbox
    print(f"Панель: ({px},{py}) {pw}×{ph}  PITCH={PITCH}px  строк={ph//PITCH}", flush=True)

    all_members = {}
    for rank, (tx, ty) in tab_coords.items():
        if max_rows and len(all_members) >= max_rows:
            break
        remaining   = max(0, max_rows - len(all_members)) if max_rows else 0
        tab_members = _collect_rank_tab(rank, tx, ty, panel_bbox, max_rows=remaining)
        if rank == 'ГЛАВА':
            tab_members = tab_members[:1]
        for m in tab_members:
            n = m['name']
            if n and n not in all_members:
                all_members[n] = m
        print(f"  [{rank}] -> {len(tab_members)} чел.", flush=True)

    return list(all_members.values())


# ─── Config & export ───────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"Конфигурация не найдена: {CONFIG_PATH}\n"
            "Скопируйте roster_config.example.json и заполните значения."
        )
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    for key in ('api_url', 'api_token'):
        if key not in cfg:
            raise ValueError(f"В конфигурации отсутствует обязательный ключ: {key}")
    return cfg


def export_to_api(roster, config):
    payload = {
        'collected_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'roster': roster,
    }
    headers = {'Authorization': f"Bearer {config['api_token']}"}
    try:
        r = requests.post(config['api_url'] + API_ROSTER_PATH,
                          headers=headers, json=payload, timeout=10)
        if 200 <= r.status_code < 300:
            return True
    except requests.RequestException:
        pass
    fname = f"roster_export_{int(time.time())}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Не удалось отправить данные. Сохранено локально: {fname}")
    return False


class _Tee:
    def __init__(self, *files):
        self._files = files

    def write(self, data):
        for f in self._files:
            try:
                f.write(data)
            except UnicodeEncodeError:
                enc = getattr(f, 'encoding', 'utf-8') or 'utf-8'
                f.write(data.encode(enc, errors='replace').decode(enc))

    def flush(self):
        for f in self._files:
            f.flush()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-rows', type=int, default=0,
                        help='Стоп после N участников (0=без лимита)')
    args = parser.parse_args()

    config = load_config()

    log_path = pathlib.Path(__file__).parent / f"roster_log_{int(time.time())}.txt"
    _log = open(log_path, 'w', encoding='utf-8')
    sys.stdout = _Tee(sys.__stdout__, _log)
    print(f"Лог: {log_path}", flush=True)

    print("Откройте «Мой клан → Участники» в игре. Сбор начнётся через 10 секунд...")
    for i in range(10, 0, -1):
        print(i, flush=True)
        time.sleep(1)

    roster = collect_roster(max_rows=args.max_rows)

    print(f"\nСобрано участников: {len(roster)}")
    for m in sorted(roster, key=lambda r: (r['rank'], r['name'])):
        might_str = f"{m['might']:,}" if m['might'] else '—'
        print(f"  [{m['rank']}] {m['name']} — {might_str}")

    success = export_to_api(roster, config)
    print("Данные отправлены на сервер." if success else "Данные сохранены локально.")


if __name__ == '__main__':
    main()
