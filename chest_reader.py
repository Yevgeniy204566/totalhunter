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
import threading

import cv2
import numpy as np
import mss
import pyautogui
import pytesseract
import requests

from auth import SERVER_URL, get_hwid, log_error_to_server
from button_finder import find_colored_button
from coord_manager import coord_manager
from tesseract_setup import configure_pytesseract

configure_pytesseract(pytesseract)

# --- Dialog detection (same tan/gold frame as tournament_reader.py) -------
DIALOG_HSV_LOWER = (10, 20, 150)
DIALOG_HSV_UPPER = (40, 120, 255)
MIN_DIALOG_DIM = 200  # guard against a 1-2px degenerate bbox on a glitched frame

# --- Row geometry — no scroll, only the top row is ever read --------------
# Row height used to be a hardcoded raw-pixel constant (ROW_PITCH=100), correct only
# at the resolution it was calibrated on. Broke on a 2K monitor (found live, castle
# view): the game renders the dialog at a bigger real pixel size there, so a fixed
# 100px search band lands above the actual row content and the «Открыть» button is
# never found — read as "list empty", collection stops early even though chests
# remain. Same problem tournament_reader.py already solved for the same tan/gold
# dialog family — reused verbatim (brightness-gradient row-boundary detection on the
# actual captured dialog) instead of inventing a second fix for one architecture.
PEAK_GRADIENT_THRESHOLD = 30
PEAK_MERGE_DIST = 3
PEAK_EDGE_MARGIN = 5

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

# «Открыть» button: HSV/contour search still decides WHETHER a button is visible
# (the only reliable "list is empty, stop" signal — blank-crop OCR text turned out
# to be unreliable, Tesseract returns noise instead of "" on a uniform background).
# But WHERE to click is a fixed point + the "chest_collect" tuning offset, not the
# detected position — the button's screen position never moves (each claimed row
# is replaced in-place by the next one, not a list scroll), same reasoning as
# SENDER_REF_RECT/SOURCE_REF_RECT above. Calibrated via coord_picker.py 2026-06-23.
BUTTON_X_FRAC = (0.78, 1.0)
BUTTON_Y_FRAC = (0.45, 1.0)
OPEN_BUTTON_REF_POS = (1352, 416)

# A single missed detection (dialog open animation, a hover-state color shift,
# a reward popup momentarily overlapping the button) must not be read as "list
# is empty" — only conclude that after this many consecutive misses in a row.
EMPTY_BUTTON_RETRY_LIMIT = 3
EMPTY_BUTTON_RETRY_PAUSE = 1.0  # владелец 2026-09-26: было 0.3 — бот вставал после 2 сундуков

# --- Anti-detect click ------------------------------------------------------
ANTI_DETECT_OFFSET_PX = 8
ANTI_DETECT_PAUSE_RANGE = (0.16, 0.28)  # reduced again 2026-06-19 by owner decision, chests-only

def resolve_storage_dir(environ=os.environ):
    """Одна база сундуков на ПК (владелец 2026-09-26). Раньше база лежала рядом с модулем:
    у исходников — папка проекта, у exe — его _internal, и на одном ПК жили две независимые
    базы. %LOCALAPPDATA% одинаков для любой копии бота. Без запасного пути: он снова создал
    бы вторую базу."""
    base = environ.get('LOCALAPPDATA')
    if not base:
        raise RuntimeError('LOCALAPPDATA не задан — хранилище сундуков не определено')
    return os.path.join(base, 'TotalHunter')


STORAGE_DIR = resolve_storage_dir()
DB_PATH = os.path.join(STORAGE_DIR, 'chest_buffer.db')
# Где база жила раньше (рядом с модулем) — только для однократного переноса неотправленного.
LEGACY_DIR = os.path.dirname(os.path.abspath(__file__))
API_IMPORT_PATH = '/api/v1/chests/import'

# --- Конвейер (сессия #149, входящие заметки п.D): захват+клик отдельно от OCR --------------
# Очередь на диске — только маленькие кропы (два ROI, PNG без потерь, ~30КБ на сундук), не полные кадры как у
# Биржи 2.0 (там нужен весь экран для YOLO). Без TTL — кроп сундука не «протухает» со временем,
# в отличие от координат биржи в игре. Без паузы-по-размеру-очереди — OCR дешевле YOLO, узкое
# место не в диске/памяти.
PENDING_DIR = os.path.join(STORAGE_DIR, 'chest_pending')

# Лимит батча — НЕ защита от потери данных (кропы и так надёжны), а денежное решение владельца
# (2026-09-25): CHEST_IMPORT_COST на сервере (server/chests.py) списывает 10◆ ФЛЭТОМ за отправку
# батча целиком, независимо от размера — без потолка пользователь мог бы копить неограниченный
# батч за одну и ту же фиксированную оплату. При достижении лимита producer останавливает приём
# новых сундуков (просто перестаёт жать «Собрать» — уже находящиеся в игре сундуки никуда не
# делись, их можно забрать следующим стартом), consumer дообрабатывает хвост, затем должна
# сработать отправка батча (on_batch_ready, реализуется вызывающим кодом в main.py).
BATCH_LIMIT = 5000


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


def detect_row_pitch(dialog):
    """Measures the real on-screen row height from the captured dialog itself
    (brightness-gradient peaks between rows), instead of assuming a fixed pixel
    value — same algorithm as tournament_reader.py's detect_row_pitch for the
    same dialog family. Returns (None, None) if fewer than two row boundaries
    are found (e.g. the list is genuinely empty, or a transient capture glitch)."""
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


def crop_fixed_field(frame, ref_rect, offset_name=None):
    """Region-lookup half of read_fixed_field, without OCR — the producer side of the
    conveyor (сессия #149) needs just the pixels to save to disk; OCR happens later,
    in the background, on whatever crop_top_row saved (see ocr_top_row_crops)."""
    x, y, w, h = coord_manager.to_region_dialog(*ref_rect)
    if offset_name is not None:
        dx, dy = coord_manager.get_ui_offset(offset_name)
        x, y = x + dx, y + dy
    return frame[y:y + h, x:x + w]


def read_fixed_field(frame, ref_rect, offset_name=None, lang='rus+eng', extra_config=''):
    roi = crop_fixed_field(frame, ref_rect, offset_name)
    return clean_name(ocr_text(roi, lang=lang, extra_config=extra_config))


# Player name: stylized/unpredictable — dictionaries only hurt here (they force
# Tesseract to "correct" unfamiliar glyph shapes into known dictionary words, which is
# exactly what splits a name like "Marisha" into single dictionary-shaped letters).
# Disabling DAWG reads any script literally instead. Two language sets: LIGHT (fast,
# Latin+Cyrillic, ~0.39s/call) covers most clans; FULL (all 19 bot-supported languages,
# ~1.0s/call — measured live on the real SENDER_REF_RECT crop size) adds Arabic/Japanese/
# Chinese/Korean for clans that actually need it. GUI lets the owner pick — most clans
# never need the 2.5x-slower FULL set.
LIGHT_SENDER_OCR_LANG = 'rus+eng+script/Latin'
FULL_SENDER_OCR_LANG = 'eng+script/Latin+script/Cyrillic+ara+jpn+chi_sim+chi_tra+kor'
SENDER_OCR_CONFIG = '-c load_system_dawg=0 -c load_freq_dawg=0'


def crop_sender_name(frame):
    return crop_fixed_field(frame, SENDER_REF_RECT, "chest_sender")


def crop_chest_type(frame):
    return crop_fixed_field(frame, SOURCE_REF_RECT, "chest_type")


def ocr_sender_name_crop(roi, full_lang=False):
    lang = FULL_SENDER_OCR_LANG if full_lang else LIGHT_SENDER_OCR_LANG
    return clean_name(ocr_text(roi, lang=lang, extra_config=SENDER_OCR_CONFIG))


def ocr_chest_type_crop(roi):
    return clean_name(ocr_text(roi, lang='rus+eng', extra_config=''))


def read_sender_name(frame, full_lang=False):
    return ocr_sender_name_crop(crop_sender_name(frame), full_lang=full_lang)


def read_chest_type(frame):
    return ocr_chest_type_crop(crop_chest_type(frame))


def read_top_row(frame, full_lang=False):
    chest_type = read_chest_type(frame)
    sender = read_sender_name(frame, full_lang=full_lang)
    return chest_type, sender


def pack_row_crops(type_roi, sender_roi):
    """Combines the two tiny OCR crops into one small image for the pending queue — one
    file per captured chest instead of two, simpler ordering/pairing on disk.

    Regression (сессия #149, живой баг владельца 2026-09-25): unpack_row_crops раньше
    резал холст по ЖЁСТКО ЗАШИТЫМ эталонным размерам SOURCE_REF_RECT/SENDER_REF_RECT
    (371x24 / 361x24), а coord_manager.to_region() масштабирует и ширину, и высоту
    (scale_x/scale_y), не только позицию — на реальном экране кроп получается совсем
    другого размера (например ~494x33 / ~481x33). Смещение среза имени наполовину
    состояло из низа кропа типа, склеенного с верхом настоящего имени — франкенштейн
    из двух надписей. И SOURCE_REF_RECT, и SENDER_REF_RECT имеют ОДНУ И ТУ ЖЕ эталонную
    высоту (24) — после одного и того же scale_y их реальные высоты ВСЕГДА равны, поэтому
    unpack делит холст РОВНО ПОПОЛАМ по фактической высоте, а не по константам."""
    h1, w1 = type_roi.shape[:2]
    h2, w2 = sender_roi.shape[:2]
    canvas = np.zeros((h1 + h2, max(w1, w2), 3), dtype=np.uint8)
    canvas[0:h1, 0:w1] = type_roi
    canvas[h1:h1 + h2, 0:w2] = sender_roi
    return canvas


def unpack_row_crops(combined):
    """Пересчитывает РЕАЛЬНЫЙ (масштабированный) размер каждого ROI напрямую через
    coord_manager — тот же источник, что использовал crop_fixed_field при вырезке, а не
    жёстко зашитые эталонные константы (см. pack_row_crops). Ширина полей разная (371 vs
    361 в эталоне) — после масштаба тоже разная, поэтому размер каждого поля нужен
    отдельно, не только высота."""
    type_w, type_h = coord_manager.to_region_dialog(*SOURCE_REF_RECT)[2:4]
    sender_w, sender_h = coord_manager.to_region_dialog(*SENDER_REF_RECT)[2:4]
    type_roi = combined[0:type_h, 0:type_w]
    sender_roi = combined[type_h:type_h + sender_h, 0:sender_w]
    return type_roi, sender_roi


def crop_top_row(frame):
    """Producer side: vырезает оба ROI сейчас (пока кадр свежий), OCR — потом, в фоне."""
    return pack_row_crops(crop_chest_type(frame), crop_sender_name(frame))


def ocr_top_row_crops(combined, full_lang=False):
    """Consumer side: OCR над кропом, сохранённым crop_top_row — не над живым кадром."""
    type_roi, sender_roi = unpack_row_crops(combined)
    chest_type = ocr_chest_type_crop(type_roi)
    sender = ocr_sender_name_crop(sender_roi, full_lang=full_lang)
    return chest_type, sender


def init_db(path=DB_PATH):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
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
    # Владелец 2026-09-26: отправленные сундуки на ПК не хранятся. Старые версии
    # помечали их is_synced=1 и копили вечно — вычищаем при каждом открытии базы.
    conn.execute('DELETE FROM local_chests WHERE is_synced = 1')
    # Королевство+клан на момент СБОРА (владелец 2026-09-26): раньше пара бралась из полей
    # в момент отправки, и переключение пары посреди сбора уводило весь батч в новый клан.
    cols = {r[1] for r in conn.execute('PRAGMA table_info(local_chests)')}
    for col in ('kingdom', 'clan'):
        if col not in cols:
            conn.execute(f'ALTER TABLE local_chests ADD COLUMN {col} TEXT')
    conn.commit()
    return conn


def migrate_legacy_storage(legacy_dir=LEGACY_DIR, db_path=DB_PATH, pending_dir=PENDING_DIR) -> int:
    """Однократный перенос НЕОТПРАВЛЕННЫХ сундуков из старой базы рядом с модулем в единую
    базу, затем старый файл удаляется — очередь пользователя при обновлении не теряется.
    Необработанные кропы переименовываются в '000000_legacy_*.png': такое имя никогда не
    пишет producer (NNNNNN.png с 000001) и идёт в очереди первым. Возвращает число
    перенесённых строк."""
    legacy_db = os.path.join(legacy_dir, 'chest_buffer.db')
    moved = 0
    if os.path.exists(legacy_db) and os.path.abspath(legacy_db) != os.path.abspath(db_path):
        old = init_db(legacy_db)
        rows = old.execute('SELECT raw_player_name, chest_type, timestamp, kingdom, clan '
                           'FROM local_chests WHERE is_synced = 0 ORDER BY id').fetchall()
        old.close()
        new = init_db(db_path)
        new.executemany('INSERT INTO local_chests (raw_player_name, chest_type, timestamp, '
                        'kingdom, clan, is_synced) VALUES (?, ?, ?, ?, ?, 0)', rows)
        new.commit()
        new.close()
        moved = len(rows)
        os.remove(legacy_db)

    legacy_pending = os.path.join(legacy_dir, 'chest_pending')
    if os.path.isdir(legacy_pending) and os.path.abspath(legacy_pending) != os.path.abspath(pending_dir):
        os.makedirs(pending_dir, exist_ok=True)
        for src in _pending_queue(legacy_pending):
            dst = os.path.join(pending_dir, '000000_legacy_' + os.path.basename(src))
            os.replace(src, dst)
    return moved


def insert_chest(conn, chest_type, raw_player_name, timestamp, kingdom=None, clan=None):
    conn.execute(
        'INSERT INTO local_chests (raw_player_name, chest_type, timestamp, kingdom, clan, is_synced) '
        'VALUES (?, ?, ?, ?, ?, 0)',
        (raw_player_name, chest_type, timestamp, kingdom, clan),
    )
    conn.commit()


def get_unsynced(conn):
    cur = conn.execute(
        'SELECT id, raw_player_name, chest_type, timestamp FROM local_chests WHERE is_synced = 0'
    )
    return cur.fetchall()


def get_unsynced_by_pair(conn, fallback_kingdom='', fallback_clan=''):
    """Неотправленные строки, сгруппированные по паре (королевство, клан) момента сбора:
    [((kingdom, clan), [(id, raw_player_name, chest_type, timestamp), ...]), ...] в порядке
    сбора. Строки старых версий без пары идут в fallback (пара из полей ввода)."""
    groups = {}
    for id_, name, ctype, ts, k, c in conn.execute(
            'SELECT id, raw_player_name, chest_type, timestamp, kingdom, clan '
            'FROM local_chests WHERE is_synced = 0 ORDER BY id'):
        pair = (k, c) if k and c else (fallback_kingdom, fallback_clan)
        groups.setdefault(pair, []).append((id_, name, ctype, ts))
    return list(groups.items())


def get_unsynced_counts(conn):
    """{chest_type: count} for is_synced=0 rows — single source of truth for the
    displayed unsynced backlog (live ticker, post-stop display, tab-open display)."""
    cur = conn.execute(
        'SELECT chest_type, COUNT(*) FROM local_chests WHERE is_synced = 0 '
        'GROUP BY chest_type'
    )
    return {chest_type: n for chest_type, n in cur.fetchall()}


def delete_sent(conn, ids):
    """Сервер подтвердил батч — строки удаляются с ПК сразу, без архива (владелец 2026-09-26)."""
    conn.executemany('DELETE FROM local_chests WHERE id = ?', [(i,) for i in ids])
    conn.commit()


def find_open_button(bbox, dialog):
    """Presence-only check: does a green «Открыть» button exist in the top row
    right now? Used solely as the "list is empty, stop" signal — the returned
    position is intentionally NOT used for clicking, see click_open_button.
    Row height comes from detect_row_pitch(dialog) — measured on the actual
    captured frame, not a fixed pixel constant — so the search band lands on
    the real row content at any resolution/scene. If no row boundary can be
    measured (dialog has no visible row), that itself counts as "no button"."""
    x, y, w, h = bbox
    pitch, row_top = detect_row_pitch(dialog)
    if pitch is None:
        return None
    region = (
        x + int(w * BUTTON_X_FRAC[0]),
        y + row_top + int(pitch * BUTTON_Y_FRAC[0]),
        int(w * (BUTTON_X_FRAC[1] - BUTTON_X_FRAC[0])),
        int(pitch * (BUTTON_Y_FRAC[1] - BUTTON_Y_FRAC[0])),
    )
    return find_colored_button(region, color='green', pick='largest')


def click_open_button(pause_range=ANTI_DETECT_PAUSE_RANGE):
    cx, cy = coord_manager.to_screen_dialog(*OPEN_BUTTON_REF_POS)
    dx, dy = coord_manager.get_ui_offset("chest_collect")
    cx, cy = cx + dx, cy + dy
    click_x = cx + random.randint(-ANTI_DETECT_OFFSET_PX, ANTI_DETECT_OFFSET_PX)
    click_y = cy + random.randint(-5, 5)
    pyautogui.click(click_x, click_y)
    time.sleep(random.uniform(*pause_range))


def save_crop_atomic(combined, final_path: str) -> bool:
    """Атомарная запись кропа в очередь: кодирует в память, пишет во временный файл, затем
    os.replace — тот же надёжный приём, что уже проверен в Бирже 2.0 (exchange_scout.py,
    save_frame_atomic), продублирован здесь, а не импортирован — chest_reader.py остаётся
    самодостаточным файлом, как и его братья tournament_reader.py/exchange_scout.py (каждый
    reader-модуль в проекте самостоятелен, общие приёмы копируются, а не связываются импортом).

    PNG (без потерь), НЕ JPEG — сессия #149, живая проверка владельца показала ухудшение
    распознавания имён после перехода на конвейер; OCR должен видеть ТЕ ЖЕ пиксели, что
    видел бы синхронный код 1:1. Биржа 2.0 намеренно использует JPEG (полный кадр для YOLO,
    там сжатие не критично и экономит место) — здесь кроп ~30КБ и без сжатия, экономить нечего.
    False при любом сбое — вызывающий producer не останавливается из-за одного сбойного кадра."""
    try:
        ok, encoded = cv2.imencode(".png", combined)
    except cv2.error:
        return False
    if not ok:
        return False

    base, _ext = os.path.splitext(final_path)
    tmp_path = base + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(encoded.tobytes())
    except OSError:
        return False

    os.replace(tmp_path, final_path)
    return True


def _pending_queue(pending_dir: str) -> list:
    """Кропы, ждущие OCR, по возрастанию номера — тот же порядок, в котором сундуки собраны.
    Проще, чем очередь Биржи 2.0 (list_queue): этот каталог заполняет только сам producer
    последовательными именами `NNNNNN.png`, нет ни ручных скринов, ни подпапок, ни TTL —
    сортировки по имени файла достаточно."""
    if not os.path.isdir(pending_dir):
        return []
    names = sorted(n for n in os.listdir(pending_dir) if n.endswith(".png"))
    return [os.path.join(pending_dir, n) for n in names]


def count_pending(pending_dir: str = PENDING_DIR) -> int:
    """Сколько кропов сейчас ждут OCR — источник прогресс-бара очереди в GUI
    (main.py, по образцу count_queue Биржи 2.0)."""
    return len(_pending_queue(pending_dir))


def delete_unsynced_batch(db_path: str = DB_PATH, pending_dir: str = PENDING_DIR) -> int:
    """Кнопка «Удалить батч» (владелец 2026-09-25): безвозвратно убирает ещё не
    отправленные сундуки — и уже прочитанные (is_synced=0 в БД), и ещё необработанные
    кропы в очереди OCR — чтобы _batch_size() снова стал 0 и сбор мог продолжиться без
    отправки на сервер. Возвращает число удалённых строк БД (кропы не считаются —
    для прогресс-бара очереди достаточно count_pending() сразу после)."""
    conn = init_db(db_path)
    try:
        cur = conn.execute("DELETE FROM local_chests WHERE is_synced = 0")
        conn.commit()
        removed = cur.rowcount
    finally:
        conn.close()
    for path in _pending_queue(pending_dir):
        try:
            os.remove(path)
        except OSError:
            pass
    return removed


def _batch_size(pending_dir: str, db_path: str) -> int:
    """Сколько сундуков сейчас 'в этом батче' — уже в БД (is_synced=0) плюс ещё необработанные
    кропы в очереди. Считать нужно ОБА, иначе producer может проскочить лимит, пока consumer
    не успел дообработать хвост (BATCH_LIMIT)."""
    conn = init_db(db_path)
    try:
        unsynced = len(get_unsynced(conn))
    finally:
        conn.close()
    return unsynced + len(_pending_queue(pending_dir))


_now = datetime.datetime.now
_last_chest_ts = None
_chest_ts_lock = threading.Lock()


def _unique_chest_timestamp() -> str:
    """Бот считает АБСОЛЮТНО ВСЕ сундуки (владелец 2026-09-26). Сервер склеивает записи с
    одинаковым (игрок, тип, время) — это защита от повторной отправки того же батча, а не
    «повторы» сундуков. С точностью до секунды фоновый OCR давал двум одинаковым сундукам
    одного игрока подряд один ключ, и второй терялся. Поэтому время — с микросекундами и
    строго возрастает, даже если часы не сдвинулись между двумя сундуками."""
    global _last_chest_ts
    with _chest_ts_lock:
        ts = _now()
        if _last_chest_ts is not None and ts <= _last_chest_ts:
            ts = _last_chest_ts + datetime.timedelta(microseconds=1)
        _last_chest_ts = ts
    return ts.isoformat(timespec='microseconds')


def _chest_consumer_loop(pending_dir: str, db_path: str, on_update, full_lang: bool,
                         producer_done: threading.Event, items_out: list,
                         kingdom=None, clan=None) -> None:
    """Фоновый consumer: разбирает очередь кропов независимо от скорости producer'а (клики не
    ждут OCR). Останавливается, только когда очередь пуста И producer точно закончил (иначе
    кроп, записанный между проверками, был бы пропущен) — тот же порядок проверки, что и в
    Бирже 2.0 (exchange_scout.py:_consumer_loop)."""
    while True:
        queue = _pending_queue(pending_dir)
        if not queue:
            if producer_done.is_set():
                break
            time.sleep(0.05)
            continue

        src = queue[0]
        try:
            combined = cv2.imread(src)
        except (FileNotFoundError, OSError):
            continue
        if combined is None:
            try:
                os.remove(src)
            except OSError:
                pass
            continue

        chest_type, sender = ocr_top_row_crops(combined, full_lang=full_lang)
        timestamp = _unique_chest_timestamp()

        conn = init_db(db_path)
        try:
            insert_chest(conn, chest_type, sender, timestamp, kingdom, clan)
            counts = get_unsynced_counts(conn)
        finally:
            conn.close()

        try:
            os.remove(src)
        except OSError:
            pass

        items_out.append({'chest_type': chest_type, 'sender': sender, 'timestamp': timestamp})
        if on_update:
            on_update(counts)


def collect_chests(stop_flag, on_update=None, db_path=DB_PATH,
                   pause_range=ANTI_DETECT_PAUSE_RANGE, full_lang=False,
                   pending_dir=PENDING_DIR, batch_limit=BATCH_LIMIT, on_batch_ready=None,
                   kingdom=None, clan=None):
    """Конвейер (сессия #149, входящие заметки п.D): клики по «Собрать» НЕ ждут OCR.
    Этот (producer) поток захватывает кадр, проверяет кнопку «Открыть» (find_open_button,
    как раньше), вырезает оба ROI (crop_top_row) и атомарно сохраняет кроп в pending_dir —
    затем СРАЗУ кликает и переходит к следующему сундуку. Отдельный фоновый consumer-поток
    (_chest_consumer_loop) параллельно разбирает очередь: OCR (ocr_top_row_crops) → запись в
    БД (insert_chest) → on_update. Останавливается по stop_flag() (список в игре ещё не
    закончился — пользователь/ESC), по естественному концу списка (EMPTY_BUTTON_RETRY_LIMIT
    промахов подряд) или по лимиту батча (см. BATCH_LIMIT).

    Перед возвратом ВСЕГДА дожидается полной дообработки очереди consumer'ом (владелец
    2026-09-25: партия должна уходить на сервер только после 100% OCR, не частично) — поэтому
    вызывающий код (main.py) может звать on_batch_ready сразу после возврата, зная, что счётчик
    уже окончательный. on_batch_ready(reason), reason — 'list_ended' или 'batch_full' — вызывается
    ИЗНУТРИ этой функции (тем же потоком, что и весь collect_chests, обычно уже фоновый поток
    GUI) перед возвратом результата; исключение в нём не теряет результат сбора — попадает в
    ключ 'batch_ready_error'.

    Возвращает {'counts', 'items', 'batch_full': bool, 'list_ended': bool, 'batch_ready_error'?}.
    'counts' — из БД (get_unsynced_counts), не сессионный счётчик, всегда полный бэклог.
    pause_range/full_lang — как раньше (анти-детект клика; язык OCR имени отправителя)."""
    os.makedirs(pending_dir, exist_ok=True)

    producer_done = threading.Event()
    items = []
    consumer_thread = threading.Thread(
        target=_chest_consumer_loop,
        args=(pending_dir, db_path, on_update, full_lang, producer_done, items, kingdom, clan),
        daemon=True,
    )
    consumer_thread.start()

    batch_full = False
    list_ended = False
    empty_streak = 0
    frame_id = 0
    try:
        while not stop_flag():
            if _batch_size(pending_dir, db_path) >= batch_limit:
                batch_full = True
                break

            frame = grab_fullscreen()
            bbox = detect_dialog_bbox(frame)
            if bbox is None:
                time.sleep(0.2)
                continue
            dialog = crop_dialog(frame, bbox)
            if dialog.shape[0] < MIN_DIALOG_DIM or dialog.shape[1] < MIN_DIALOG_DIM:
                time.sleep(0.2)
                continue

            if find_open_button(bbox, dialog) is None:
                empty_streak += 1
                if empty_streak >= EMPTY_BUTTON_RETRY_LIMIT:
                    list_ended = True
                    break
                time.sleep(EMPTY_BUTTON_RETRY_PAUSE)
                continue
            empty_streak = 0

            frame_id += 1
            combined = crop_top_row(frame)
            frame_path = os.path.join(pending_dir, f"{frame_id:06d}.png")
            save_crop_atomic(combined, frame_path)

            click_open_button(pause_range)
    finally:
        producer_done.set()
        consumer_thread.join()   # владелец 2026-09-25: ждать полного OCR, не частичный батч

    result = {'items': items, 'batch_full': batch_full, 'list_ended': list_ended}

    if on_batch_ready and (batch_full or list_ended):
        try:
            on_batch_ready('batch_full' if batch_full else 'list_ended')
        except Exception as e:
            result['batch_ready_error'] = f"{type(e).__name__}: {e}"

    # 'counts' считается ПОСЛЕ on_batch_ready — регрессия сессии #149 (живая жалоба
    # владельца): раньше счёт брался ДО отправки, и main.py показывал в окне сундуков
    # уже отправленные (но всё ещё "старым" счётом непустые) записи поверх только что
    # очищенного успешной отправкой списка — выглядело так, будто отправка ничего не
    # почистила, хотя на сервере всё было принято верно.
    conn = init_db(db_path)
    try:
        result['counts'] = get_unsynced_counts(conn)
    finally:
        conn.close()

    return result


EXPORT_MAX_ATTEMPTS = 2


def export_to_api(kingdom, clan, items):
    """Регрессия сессии #149 (живой инцидент владельца 2026-09-25): раньше успех определялся
    ТОЛЬКО HTTP-статусом — сервер один раз ответил 200 OK, но реально принял меньше записей,
    чем было отправлено (без единой ошибки в логах), а код пометил их ВСЕ как отправленные.
    Теперь возвращается 'count' из тела ответа сервера — сколько записей реально принято;
    сверку с len(items) и решение (помечать ли is_synced) делает вызывающий код (main.py),
    не эта функция — она только честно докладывает, что сказал сервер."""
    payload = {
        "hwid": get_hwid(),
        "kingdom": kingdom,
        "clan": clan,
        "timestamp": datetime.datetime.now().isoformat(timespec='seconds'),
        "items": items,
    }
    reason = None
    for _ in range(EXPORT_MAX_ATTEMPTS):
        try:
            response = requests.post(SERVER_URL + API_IMPORT_PATH, json=payload, timeout=45)
        except requests.RequestException as exc:
            reason = f"{type(exc).__name__}: {exc}"
            continue
        if response.status_code == 402:
            return {"success": False, "low_credits": True}
        if 200 <= response.status_code < 300:
            try:
                count = response.json().get("count", len(items))
            except ValueError:
                count = len(items)  # ответ без валидного JSON-тела — не считать это провалом
            return {"success": True, "count": count}
        reason = f"http_{response.status_code}"
    log_error_to_server(f"chest_export_failed after {EXPORT_MAX_ATTEMPTS} attempts: {reason}")
    return {"success": False}
