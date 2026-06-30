"""
clan_chat_reader.py — сканирование списка участников Кланового чата.

Алгоритм:
  1. Определяет регион списка по HSV золотой рамки диалога (как в tournament_reader)
  2. Дискретный скролл → пауза 0.4s → снимок → двухпроходный OCR (Latin+Cyrillic)
  3. Очищает и дедуплицирует имена
  4. Отправляет на сервер (hwid + kingdom + clan)

Игрок сначала открывает «Клановый чат» → иконку 👥, затем запускает.
"""
import os, re, tempfile, time, random
import cv2, mss, numpy as np, pyautogui, pytesseract, requests
from difflib import SequenceMatcher

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from auth import SERVER_URL, get_hwid

API_PATH = "/api/v1/clan/roster-upload"

# ── Детекция списка участников ────────────────────────────────────────────────
# Ищем кремово-бежевый фон самого списка (не золотую рамку — она на ЛЕВОЙ панели
# каналов, и именно её находил старый детектор, ставя курсор не туда).
# BGR ≈ (195,225,240) → HSV: H≈25-45, S≈10-70, V≈185-255
LIST_HSV_LOWER = np.array([15, 10, 185], dtype=np.uint8)
LIST_HSV_UPPER = np.array([45, 75, 255], dtype=np.uint8)
MIN_LIST_W = 100
MIN_LIST_H = 120
# Пропускаем строку поиска сверху (~14%) и кнопки снизу (~8%)
SKIP_TOP_FRAC = 0.14
SKIP_BOT_FRAC = 0.08

# ── OCR: препроцессинг ────────────────────────────────────────────────────────
SCALE        = 5
BORDER_PAD   = 50
MIN_TEXT_PX  = 8
TEXT_DARK_THR = 150
ROW_MERGE_GAP = 4
ROW_PAD       = 4
MIN_NAME_LEN  = 2
MAX_NAME_LEN  = 20

# ── Скроллинг ─────────────────────────────────────────────────────────────────
SCROLL_CLICKS    = 1
SCROLL_PAUSE_SEC = 0.40
END_STREAK_LIMIT = 4
ANTI_AFK_SEC     = 170

# ── Tesseract: два прохода, DAWG отключён ────────────────────────────────────
_DAWG_OFF = (
    "load_system_dawg 0\n"
    "load_freq_dawg 0\n"
    "load_punc_dawg 0\n"
    "load_number_dawg 0\n"
)
_WL_LATIN = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
_WL_CYR   = ("абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
              "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
              "іІїЇєЄґҐ0123456789 ")

_CFG_LAT = os.path.join(tempfile.gettempdir(), "tess_chat_lat.cfg")
_CFG_CYR = os.path.join(tempfile.gettempdir(), "tess_chat_cyr.cfg")
with open(_CFG_LAT, "w", encoding="utf-8") as _f:
    _f.write(f"tessedit_char_whitelist {_WL_LATIN}\n{_DAWG_OFF}")
with open(_CFG_CYR, "w", encoding="utf-8") as _f:
    _f.write(f"tessedit_char_whitelist {_WL_CYR}\n{_DAWG_OFF}")

_TESS_SCRIPT = os.path.join(
    os.path.dirname(pytesseract.pytesseract.tesseract_cmd), "tessdata", "script"
)
_HAVE_SCRIPTS = (
    os.path.exists(os.path.join(_TESS_SCRIPT, "Latin.traineddata")) and
    os.path.exists(os.path.join(_TESS_SCRIPT, "Cyrillic.traineddata"))
)


# ── Детекция ──────────────────────────────────────────────────────────────────

def detect_list_region():
    """
    Возвращает (left, top, width, height) кремового списка участников.
    Детектируем сам список по цвету фона, а не золотую рамку (та стоит
    на ЛЕВОЙ панели каналов и сбивала курсор не туда).
    """
    with mss.mss() as sct:
        frame = cv2.cvtColor(np.array(sct.grab(sct.monitors[1])), cv2.COLOR_BGRA2BGR)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LIST_HSV_LOWER, LIST_HSV_UPPER)

    # Морфология: убираем шум, склеиваем прерывистые пятна
    k = np.ones((12, 12), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError("Список участников не найден — откройте «Клановый чат» → 👥")

    largest = max(contours, key=cv2.contourArea)
    lx, ly, lw, lh = cv2.boundingRect(largest)

    if lw < MIN_LIST_W or lh < MIN_LIST_H:
        raise RuntimeError("Список участников слишком мал — убедитесь что открыт раздел «Участники»")

    # Отрезаем строку поиска (top) и кнопочную панель (bottom)
    skip_top = int(lh * SKIP_TOP_FRAC)
    skip_bot = int(lh * SKIP_BOT_FRAC)
    ly += skip_top
    lh -= (skip_top + skip_bot)

    return lx, ly, lw, lh


# ── Захват ────────────────────────────────────────────────────────────────────

def _grab(region):
    left, top, w, h = region
    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": w, "height": h})
    return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)


# ── Детекция строк ────────────────────────────────────────────────────────────

def _find_rows(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    dark = (gray < TEXT_DARK_THR).sum(axis=1)
    spans, in_span, start = [], False, 0
    for y in range(frame.shape[0]):
        if dark[y] >= MIN_TEXT_PX and not in_span:
            start = y; in_span = True
        elif dark[y] < MIN_TEXT_PX and in_span:
            spans.append([start, y]); in_span = False
    if in_span:
        spans.append([start, frame.shape[0]])
    merged = []
    for sp in spans:
        if merged and sp[0] - merged[-1][1] <= ROW_MERGE_GAP:
            merged[-1][1] = sp[1]
        else:
            merged.append(sp)
    return [(max(0, y0 - ROW_PAD), min(frame.shape[0], y1 + ROW_PAD))
            for y0, y1 in merged]


# ── OCR ───────────────────────────────────────────────────────────────────────

def _preprocess(row_img):
    gray = cv2.cvtColor(row_img, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_LANCZOS4)
    _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.copyMakeBorder(binary, BORDER_PAD, BORDER_PAD, BORDER_PAD, BORDER_PAD,
                              cv2.BORDER_CONSTANT, value=255)


_JUNK_HEAD = re.compile(r"^[|}\'\`\"‚\s\[\]!_\.\-]+")
_JUNK_TAIL = re.compile(r"[|}\'\`\"‚\s\[\]!]+$")
_JUNK_LINE = re.compile(
    r"^\s*(\d+%|введите|клановый|чат\b|\W{0,3}\s*\d{1,3}\s*$)", re.IGNORECASE)
_PREFIX_NUM = re.compile(r"^[1lI]\s+")


def _clean(text):
    text = text.strip()
    if _JUNK_LINE.match(text):
        return ""
    text = _PREFIX_NUM.sub("", text)
    text = _JUNK_HEAD.sub("", text)
    text = _JUNK_TAIL.sub("", text)
    text = re.sub(r"\s+\S$", "", text)
    letters = [c for c in text if c.isalpha()]
    if text and len(letters) / len(text) < 0.5:
        return ""
    return text.strip()


def _ocr_script(binary, script_name, cfg_path):
    if not _HAVE_SCRIPTS:
        return "", 0.0
    try:
        d = pytesseract.image_to_data(
            binary, config=f"--psm 7 {cfg_path}",
            lang=f"script/{script_name}",
            output_type=pytesseract.Output.DICT, timeout=10,
        )
        valid = [(w, int(c)) for w, c in zip(d["text"], d["conf"])
                 if w.strip() and int(c) >= 0]
        text = " ".join(w for w, _ in valid)
        conf = sum(c for _, c in valid) / len(valid) if valid else 0.0
        return text.strip(), conf
    except Exception:
        return "", 0.0


def _ocr_row(row_img):
    binary = _preprocess(row_img)
    name_lat, conf_lat = _ocr_script(binary, "Latin",    _CFG_LAT)
    name_cyr, conf_cyr = _ocr_script(binary, "Cyrillic", _CFG_CYR)
    name_lat = _clean(name_lat)
    name_cyr = _clean(name_cyr)
    # Порог +3 — эмпирически: уникальные кириллические глифы (Г,Б,Ш,Й)
    # дают большой разрыв conf; омонимы (А,О,Е) — разрыв < 3 → Latin побеждает
    if conf_cyr > conf_lat + 3 and name_cyr:
        return name_cyr
    return name_lat if name_lat else name_cyr


def _ocr_frame(frame):
    names = []
    for y0, y1 in _find_rows(frame):
        if y1 - y0 < 10:
            continue
        name = _ocr_row(frame[y0:y1, :])
        if len(name) >= MIN_NAME_LEN:
            names.append(name)
    return names


def _frames_same(a, b, thr=0.997):
    if a.shape != b.shape:
        return False
    return (cv2.absdiff(a, b).mean() / 255.0) < (1 - thr)


# ── Очистка (дедупликация) ────────────────────────────────────────────────────

_JUNK_CHARS = re.compile(r"[»«Э\'`^$#@!()=?/\\|{}<>\[\]~]")
_JUNK_ONLY  = re.compile(r"^[\W\d_]+$", re.UNICODE)


def _is_junk(name):
    name = _PREFIX_NUM.sub("", name)
    if len(name) < 2:
        return True
    if len(name) > MAX_NAME_LEN:
        return True
    if _JUNK_CHARS.search(name):
        return True
    if _JUNK_ONLY.match(name):
        return True
    if re.search(r'\d{3,}', name):
        return True
    if len(name) > 0 and sum(c.isdigit() for c in name) / len(name) > 0.4:
        return True
    if sum(1 for c in name if c.isalpha()) < 2:
        return True
    non_word = sum(1 for c in name if not c.isalnum() and c not in " _-.")
    if name and non_word / len(name) > 0.35:
        return True
    if re.match(r"^[a-z]{2,3}$", name):
        return True

    words = name.split()
    # 4+ слов → почти всегда мусор UI/OCR
    if len(words) >= 4:
        return True
    # 2+ коротких слова (≤ 2 символа) → мусор
    if sum(1 for w in words if len(w) <= 2) >= 2:
        return True
    # Цифра между буквами → OCR-артефакт ("Ma3aQakxa")
    if re.search(r'[A-Za-zА-Яа-я]\d[A-Za-zА-Яа-я]', name):
        return True
    # Любое длинное слово с почти нулевыми гласными → случайный набор букв
    for word in words:
        if len(word) > 7 and word.isalpha():
            vowels = sum(1 for c in word.lower() if c in "aeiouаеіоуиє")
            if vowels / len(word) < 0.15:
                return True
    # Высокое чередование регистра → OCR склеил две строки ("MaKnJoHaHnH")
    if len(name) > 8:
        alpha = [c for c in name if c.isalpha()]
        if len(alpha) > 5:
            transitions = sum(1 for i in range(1, len(alpha))
                              if alpha[i - 1].isupper() != alpha[i].isupper())
            if transitions / len(alpha) > 0.55:
                return True

    first = words[0]
    if len(first) > 5 and first.islower():
        vowels = sum(1 for c in first if c in "aeiouаеіоуиє")
        if vowels / len(first) < 0.15:
            return True
    return False


def _cyrillic_ratio(s):
    cyr = sum(1 for c in s if "Ѐ" <= c <= "ӿ" or c in "іІїЇєЄ")
    letters = sum(1 for c in s if c.isalpha())
    return cyr / letters if letters else 0.0


def _looks_garbled(s):
    return (bool(re.search(r"[A-Za-z]\d[A-Za-z]", s)) or
            bool(re.search(r"(?<![0-9])\d[A-Za-z]{2,}", s)))


def _pick_better(a, b):
    ga, gb = _looks_garbled(a), _looks_garbled(b)
    if ga and not gb:
        return b
    if gb and not ga:
        return a
    ca, cb = _cyrillic_ratio(a), _cyrillic_ratio(b)
    if ca > 0.7 and cb < 0.3 and not ga:
        return a
    if cb > 0.7 and ca < 0.3 and not gb:
        return b
    if abs(len(a) - len(b)) > 3:
        return a if len(a) > len(b) else b
    return a if sum(1 for c in a if c.isupper()) >= sum(1 for c in b if c.isupper()) else b


def _fuzzy_dedup(names, threshold=0.85):
    canonical = []
    for name in names:
        matched = False
        for i, exist in enumerate(canonical):
            if SequenceMatcher(None, name.lower(), exist.lower()).ratio() >= threshold:
                canonical[i] = _pick_better(exist, name)
                matched = True
                break
        if not matched:
            canonical.append(name)
    return canonical


def clean_names(raw):
    raw = [_PREFIX_NUM.sub("", n).strip() for n in raw]
    filtered = [n for n in raw if not _is_junk(n)]
    seen = {}
    for name in filtered:
        key = name.lower()
        seen[key] = _pick_better(seen[key], name) if key in seen else name
    after_fuzzy = _fuzzy_dedup(list(seen.values()), threshold=0.82)
    return sorted(after_fuzzy, key=lambda n: n.lower())


# ── Основной цикл ─────────────────────────────────────────────────────────────

def collect(stop_flag, on_status=None):
    """
    stop_flag: callable → bool
    on_status: callable(str) → обновляет GUI
    Возвращает список имён или [] если пользователь нажал СТОП.
    """
    def status(msg):
        if on_status:
            on_status(msg)

    region = detect_list_region()
    list_x, list_y, list_w, list_h = region
    scroll_cx = list_x + list_w // 2
    scroll_cy = list_y + list_h // 2

    all_names = []
    end_streak = 0
    prev_frame = None
    last_afk   = time.time()

    # Точный паттерн tournament_reader.py: медленный moveTo(duration=0.3) + click()
    # без аргументов. click(x,y) телепортирует мгновенно — игра не успевает
    # зарегистрировать hover и не принимает последующие scroll-события.
    pyautogui.moveTo(scroll_cx, scroll_cy, duration=0.3)
    pyautogui.click()
    time.sleep(0.3)

    while not stop_flag():
        frame = _grab(region)

        if prev_frame is not None and _frames_same(prev_frame, frame):
            end_streak += 1
            if end_streak >= END_STREAK_LIMIT:
                break
        else:
            end_streak = 0

        names = _ocr_frame(frame)
        all_names.extend(names)
        status(f"В работе... {len(all_names)} имён")

        prev_frame = frame

        # Anti-AFK — паттерн tournament_reader: moveTo + click()
        if time.time() - last_afk >= ANTI_AFK_SEC:
            pyautogui.moveTo(scroll_cx + random.randint(-5, 5),
                             scroll_cy + random.randint(-5, 5), duration=0.1)
            pyautogui.click()
            last_afk = time.time()
            time.sleep(0.3)

        # Скролл в КОНЦЕ итерации — как в tournament_reader
        pyautogui.moveTo(scroll_cx, scroll_cy, duration=0.05)
        pyautogui.scroll(-2)
        time.sleep(SCROLL_PAUSE_SEC)

    if stop_flag():
        return []

    return clean_names(all_names)


# ── Загрузка на сервер ────────────────────────────────────────────────────────

def upload(kingdom, clan, names):
    """Возвращает (success: bool, count: int)."""
    payload = {
        "hwid":    get_hwid(),
        "kingdom": kingdom,
        "clan":    clan,
        "names":   names,
    }
    try:
        r = requests.post(SERVER_URL + API_PATH, json=payload, timeout=15)
        if 200 <= r.status_code < 300:
            return True, len(names)
    except requests.RequestException:
        pass
    return False, 0


# ── Публичный API ─────────────────────────────────────────────────────────────

def run(kingdom, clan, stop_flag, on_status=None):
    """
    Полный цикл: детекция → сбор → очистка → загрузка.
    Возвращает ("ok", count) | ("stopped", 0) | ("error", описание).
    """
    try:
        names = collect(stop_flag, on_status)
    except RuntimeError as e:
        return "error", str(e)

    if stop_flag():
        return "stopped", 0

    if not names:
        return "error", "Имён не найдено"

    success, count = upload(kingdom, clan, names)
    return ("ok", count) if success else ("error", "Ошибка отправки на сервер")
