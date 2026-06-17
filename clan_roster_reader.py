"""
clan_roster_reader.py — Фаза 0 ERP
Сканирует «Мой клан → Участники», считывает имя/ранг/могущество.
"""
import os
import re
import json
import time
import random

import cv2
import numpy as np
import mss
import pyautogui
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ── Панель (из profiles/profile_client.json) ──────────────────────────────
PANEL_LEFT   = 688
PANEL_TOP    = 346
PANEL_WIDTH  = 724
PANEL_HEIGHT = 363

SCROLL_CX = 1050   # центр панели — курсор здесь при скролле
SCROLL_CY = 527

# ── Вкладки рангов ─────────────────────────────────────────────────────────
RANK_TABS = {
    "ГЛАВА":   (869,  318),
    "СТАРШИЙ": (990,  318),
    "ОФИЦЕР":  (1119, 318),
    "ВЕТЕРАН": (1237, 318),
    "РЯДОВОЙ": (1359, 318),
}

# ── Структура панели (хардкод, верифицировано по _dbg2_row_*.png) ──────────
PITCH            = 86    # высота одной карточки участника, px
HEADER_HEIGHT_PX = 35    # «СТАРШИЙ ⓘ» — сепаратор ранга вверху вкладки
NUM_VISIBLE_ROWS = 3
OWN_Y0           = HEADER_HEIGHT_PX + NUM_VISIBLE_ROWS * PITCH   # = 293

# ── Кропы внутри карточки ─────────────────────────────────────────────────────
# Имя: ШИРОКИЙ кроп — захватываем всё (статус предыдущего игрока + разделитель + имя)
# OCR+regex отделит имя от статуса.  x=108 — после рамки аватара
NAME_X1, NAME_X2 = 108, 560
NAME_Y1,  NAME_Y2 = 0, 57   # 0..57px: весь верхний блок карточки

# Могущество: y=35..55 для card_0 (нет сепаратора), y=57..77 для card_1+
MIGHT_X1, MIGHT_X2 = 460, 710
MIGHT_Y1_C0, MIGHT_Y2_C0 = 35, 55
MIGHT_Y1_C1, MIGHT_Y2_C1 = 57, 77

# ── Скролл / конец списка ──────────────────────────────────────────────────
END_OF_LIST_ZERO_SHIFTS = 2
SCROLLBAR_MARGIN = 0.05    # правый край (скроллбар) — исключаем из matchTemplate

# ── OCR имени ──────────────────────────────────────────────────────────────
NAME_MIN_LENGTH = 2

# ── Anti-AFK ───────────────────────────────────────────────────────────────
ANTI_AFK_INTERVAL_SEC  = 180
ANTI_AFK_HEADER_Y_FRAC = 0.05

# ── Выходной файл ─────────────────────────────────────────────────────────
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clan_roster.json')
API_PATH    = '/api/v1/clan/roster'


# ─────────────────────────────────────────────────────────────────────────────
# Захват панели
# ─────────────────────────────────────────────────────────────────────────────

def grab_panel():
    with mss.mss() as sct:
        region = {"left": PANEL_LEFT, "top": PANEL_TOP,
                  "width": PANEL_WIDTH, "height": PANEL_HEIGHT}
        shot = sct.grab(region)
        frame = np.array(shot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


# ─────────────────────────────────────────────────────────────────────────────
# Кропы карточек — абсолютные пиксели, без динамики
# ─────────────────────────────────────────────────────────────────────────────

def get_card_crops(panel_img, first_frame=True):
    """
    Возвращает список (name_roi, might_roi).
    Имя: ШИРОКИЙ кроп y=0..57 для ВСЕХ карточек — regex в _clean_name уберёт статус.
    Могущество: C0 для верхней карточки первого кадра, C1 для остальных.
    """
    cards = []
    for i in range(NUM_VISIBLE_ROWS):
        y0 = HEADER_HEIGHT_PX + i * PITCH
        y1 = y0 + PITCH
        if y1 > OWN_Y0:
            break
        card = panel_img[y0:y1, :]
        if card.shape[0] < PITCH // 2:
            break

        name_roi = card[NAME_Y1:NAME_Y2, NAME_X1:NAME_X2]

        use_c0 = first_frame and (i == 0)
        my1, my2 = (MIGHT_Y1_C0, MIGHT_Y2_C0) if use_c0 else (MIGHT_Y1_C1, MIGHT_Y2_C1)
        might_roi = card[my1:my2, MIGHT_X1:MIGHT_X2]

        cards.append((name_roi, might_roi))
    return cards


# ─────────────────────────────────────────────────────────────────────────────
# Измерение сдвига скролла
# ─────────────────────────────────────────────────────────────────────────────

def measure_scroll_shift(prev_panel, curr_panel):
    w = prev_panel.shape[1]
    content_x2 = int(w * (1 - SCROLLBAR_MARGIN))

    # Шаблон — вторая карточка предыдущего кадра
    tmpl_y0 = HEADER_HEIGHT_PX + PITCH
    tmpl_y1 = tmpl_y0 + PITCH
    template = prev_panel[tmpl_y0:tmpl_y1, 0:content_x2]
    search   = curr_panel[HEADER_HEIGHT_PX:OWN_Y0, 0:content_x2]

    if template.size == 0 or search.size == 0:
        return 0
    if template.shape[0] >= search.shape[0] or template.shape[1] > search.shape[1]:
        return 0

    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    return tmpl_y0 - (HEADER_HEIGHT_PX + max_loc[1])


# ─────────────────────────────────────────────────────────────────────────────
# OCR
# ─────────────────────────────────────────────────────────────────────────────

def _preprocess_otsu(roi, invert=False):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    method = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(scaled, 0, 255, method + cv2.THRESH_OTSU)
    return binary


def _ocr_otsu(roi, invert=False, psm=7):
    processed = _preprocess_otsu(roi, invert=invert)
    return pytesseract.image_to_string(
        processed, config=f'--psm {psm}', lang='rus+eng', timeout=5
    ).strip()


_STATUS_LINE = re.compile(
    r'(?i)^\s*(был[аои]?\b|в\s+сет[иь]|не\s+в\s+сет[иь]|в\s+игре)',
)

def _clean_name(text):
    # Широкий кроп даёт несколько строк: статус пред. игрока + разделитель + имя.
    # Берём первую строку, которая НЕ является статусной.
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name_line = ''
    for line in lines:
        if not _STATUS_LINE.match(line):
            name_line = line
            break
    if not name_line:
        name_line = lines[-1] if lines else ''
    text = name_line

    # 1. Ведущие артефакты от рамки карточки (|, }, ‚, ', `)
    text = re.sub(r'^[|}\'\`"‚\s\[\]!i]+', '', text)
    # 2. Координаты "(K:229 X:478 Y:516)" — OCR часто читает ( как |, {, i, [
    text = re.sub(r'\s*[\(\{\|\[iI]\s*[KkКкRr]:?\s*\d+.*', '', text)
    # 3. Фолбэк: K:229 без открывающей скобки
    text = re.sub(r'\s+[KkКкRr]:?\s*\d{1,3}[\s:].*', '', text)
    # 4. Тег королевства [K229]
    text = re.sub(r'^\[.*?\]\s*', '', text)
    # 5. Хвостовые артефакты
    text = re.sub(r'\s+\S{1,3}$', '', text)
    while True:
        stripped = re.sub(r'\s+(?:\d{1,3}|\S{1})$', '', text)
        if stripped == text:
            break
        text = stripped
    return re.sub(r'[^\w]+$', '', text, flags=re.UNICODE).strip()


def ocr_name(name_roi):
    if name_roi.size == 0:
        return ''
    candidates = []
    # psm=6 (блок текста) идёт первым — он видит статус+имя в широком кропе
    for psm, inv in ((6, False), (6, True), (7, False), (7, True)):
        raw = _ocr_otsu(name_roi, invert=inv, psm=psm)
        name = _clean_name(raw)   # _clean_name сам выбирает нужную строку
        if len(name) >= NAME_MIN_LENGTH:
            candidates.append(name)
    if not candidates:
        return ''
    return max(candidates, key=len)


def ocr_might(might_roi):
    if might_roi.size == 0:
        return None
    gray = cv2.cvtColor(might_roi, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    raw = pytesseract.image_to_string(
        binary, config='--psm 7 -c tessedit_char_whitelist=0123456789,', timeout=5
    ).strip()
    digits = re.sub(r'[^\d]', '', raw)
    return int(digits) if digits else None


# ─────────────────────────────────────────────────────────────────────────────
# Anti-AFK
# ─────────────────────────────────────────────────────────────────────────────

def _anti_afk_click():
    click_x = PANEL_LEFT + PANEL_WIDTH // 2 + random.randint(-8, 8)
    click_y = PANEL_TOP + int(PANEL_HEIGHT * ANTI_AFK_HEADER_Y_FRAC) + random.randint(-3, 3)
    pyautogui.click(click_x, click_y)
    time.sleep(0.3)


# ─────────────────────────────────────────────────────────────────────────────
# Основной сбор данных
# ─────────────────────────────────────────────────────────────────────────────

def collect_roster():
    all_members = []
    global_seen = set()
    last_afk = time.time()

    for rank_name, (tx, ty) in RANK_TABS.items():
        print(f"\n── {rank_name} ──")

        pyautogui.moveTo(tx, ty)
        time.sleep(0.1 + random.random() * 0.1)
        pyautogui.click()
        time.sleep(0.5)

        panel = grab_panel()
        tab_data = {}   # name → might
        zero_streak = 0
        first_frame = True   # первый кадр: i=0 без сепаратора

        while True:
            if time.time() - last_afk > ANTI_AFK_INTERVAL_SEC:
                _anti_afk_click()
                last_afk = time.time()

            for name_roi, might_roi in get_card_crops(panel, first_frame=first_frame):
                name = ocr_name(name_roi)
                if name and name not in tab_data:
                    might = ocr_might(might_roi)
                    tab_data[name] = might
                    print(f"  {name} — {might}")

            prev_panel = panel
            pyautogui.moveTo(SCROLL_CX, SCROLL_CY)
            pyautogui.scroll(-2)
            time.sleep(0.28 + random.random() * 0.1)
            panel = grab_panel()
            first_frame = False   # после скролла все карточки имеют сепаратор

            shift_px = measure_scroll_shift(prev_panel, panel)

            if shift_px <= 0:
                zero_streak += 1
                if zero_streak >= END_OF_LIST_ZERO_SHIFTS:
                    for name_roi, might_roi in get_card_crops(panel, first_frame=False):
                        name = ocr_name(name_roi)
                        if name and name not in tab_data:
                            might = ocr_might(might_roi)
                            tab_data[name] = might
                            print(f"  {name} — {might}")
                    break
            else:
                zero_streak = 0

        for name, might in tab_data.items():
            if name not in global_seen:
                global_seen.add(name)
                all_members.append({"name": name, "rank": rank_name, "might": might})

    return all_members


# ─────────────────────────────────────────────────────────────────────────────
# Экспорт
# ─────────────────────────────────────────────────────────────────────────────

def export_roster(roster):
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clan_roster_config.json')
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        api_url   = cfg.get('api_url', '')
        api_token = cfg.get('api_token', '')
        if api_url:
            try:
                import requests
                resp = requests.post(
                    f"{api_url}{API_PATH}",
                    json={"members": roster},
                    headers={"Authorization": f"Bearer {api_token}"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    print(f"Отправлено на сервер: {len(roster)} участников")
                    return
                print(f"[WARN] API {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                print(f"[WARN] API недоступен: {e}")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({"members": roster}, f, ensure_ascii=False, indent=2)
    print(f"Сохранено: {OUTPUT_PATH} ({len(roster)} участников)")


# ─────────────────────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Открыта вкладка «Мой клан → Участники»? Старт через 3 сек...")
    for i in (3, 2, 1):
        print(i)
        time.sleep(1)

    roster = collect_roster()

    print(f"\n===RESULT=== ({len(roster)} участников)")
    for m in roster:
        print(f"  [{m['rank']}] {m['name']} — {m['might']}")

    export_roster(roster)


if __name__ == '__main__':
    main()
