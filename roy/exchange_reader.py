"""
exchange_reader.py — OCR диалога биржи наёмников.

Извлекает:
  - Координаты: K (гос), X, Y из красной строки в верхней части диалога
  - Процент выкупа: из текста «Прогресс сделок: XX%»

Алгоритм:
  1. Захват фиксированного ROI через coord_manager (масштабирование по профилю)
  2. Запуск pytesseract на захваченном регионе
  3. Парсинг результата регулярным выражением

Координаты ROI захардкожены в reference-системе (1920×1080),
верифицированы по скриншотам Биржа_15.04.png (диалог: x=656,y=335,w=611,h=393).
Масштабируются через coord_manager.to_region() по профилю пользователя.
Никакого динамического поиска окна — только жёсткие координаты.
"""

import re
import time
import os as _os
import datetime as _datetime

import cv2
import numpy as np

_LOG_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'roy_debug.log')

def _log(msg: str):
    line = f"{_datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]} [OCR] {msg}"
    print(line)
    try:
        with open(_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except ImportError:
    pytesseract = None

try:
    import mss
except ImportError:
    mss = None

from coord_manager import coord_manager


# ── Hardcoded ROI в reference-системе (1920×1080) ────────────────────────────
# Диалог биржи (Биржа_15.04.png, 3 скриншота): x=656, y=335, w=611, h=393
# Строка K:X:Y — +20px запас с каждой стороны от точного положения текста
_COORD_X_REF    = 636
_COORD_Y_REF    = 330
_COORD_W_REF    = 651
_COORD_H_REF    = 115

# Прогресс сделок (текст + зелёный бар, ~57-75% высоты диалога) + 20px запас
_PROGRESS_X_REF = 636
_PROGRESS_Y_REF = 540
_PROGRESS_W_REF = 651
_PROGRESS_H_REF = 120

# Таймаут ожидания появления диалога (сек)
_DIALOG_TIMEOUT = 4.0


# ─────────────────────────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────────────────────────

def wait_and_read(timeout: float = _DIALOG_TIMEOUT) -> dict | None:
    """
    Ждёт появления диалога биржи и читает данные.
    Возвращает {'kingdom': int, 'x': int, 'y': int, 'percent': int}
    или None если диалог не открылся / координаты не распознаны.
    """
    _log(f"wait_and_read: старт, timeout={timeout}с")
    if mss is None:
        _log("wait_and_read: ОШИБКА — mss не установлен!")
        return None
    if pytesseract is None:
        _log("wait_and_read: ОШИБКА — pytesseract не установлен!")
        return None
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        result = _try_read()
        if result:
            _log(f"wait_and_read: успех на попытке #{attempt} → {result}")
            return result
        time.sleep(0.3)
    _log(f"wait_and_read: таймаут после {attempt} попыток — координаты не распознаны")
    return None


def read_once() -> dict | None:
    """Читает диалог один раз без ожидания."""
    return _try_read()


# ─────────────────────────────────────────────────────────────────────────────
# Внутренняя логика
# ─────────────────────────────────────────────────────────────────────────────

def _grab_region(x_ref: int, y_ref: int, w_ref: int, h_ref: int) -> np.ndarray:
    """Захватывает регион экрана по reference-координатам через coord_manager."""
    sx, sy, sw, sh = coord_manager.to_region(x_ref, y_ref, w_ref, h_ref)
    _log(f"_grab_region: ref=({x_ref},{y_ref},{w_ref},{h_ref}) → screen=({sx},{sy},{sw},{sh})")
    with mss.mss() as sct:
        region = {'left': sx, 'top': sy, 'width': max(sw, 1), 'height': max(sh, 1)}
        raw = sct.grab(region)
        return cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR)


def _ocr_coords(roi: np.ndarray) -> tuple | None:
    """
    Читает координаты K/X/Y из захваченного региона.
    Возвращает (kingdom, x, y) или None.
    """
    if pytesseract is None:
        return None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    # Threshold 180 isolates dark text on the light dialog background
    _, gray = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

    try:
        text = pytesseract.image_to_string(gray, config='--psm 11', timeout=3).strip()
    except Exception as e:
        _log(f"_ocr_coords: pytesseract ERROR: {e!r}")
        return None
    _log(f"_ocr_coords: сырой текст = {repr(text)}")
    result = _parse_coords(text)
    _log(f"_ocr_coords: парсинг → {result}")
    return result


def _parse_coords(text: str) -> tuple | None:
    """
    Парсит строку координат.
    Поддерживает форматы:
      K:471 X:383 Y:812
      К:471 X:383 Y:812   (кириллица)
      K:471X:383Y:812     (без пробелов)
    """
    text = text.upper().replace('К', 'K').replace('Х', 'X').replace('У', 'Y')
    text = text.replace(' ', '').replace('\n', '')

    pattern = r'K[:\s]*(\d+)[^\d]*X[:\s]*(\d+)[^\d]*Y[:\s]*(\d+)'
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _measure_progress(roi: np.ndarray) -> int:
    """
    Читает процент из текста «Прогресс сделок: XX%» через pytesseract.
    Fallback: ширина зелёной полосы.
    Возвращает 0-100.
    """
    if pytesseract is not None:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh = cv2.resize(thresh, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        config = '--psm 6 -c tessedit_char_whitelist=0123456789%: '
        try:
            text = pytesseract.image_to_string(thresh, config=config, timeout=3)
        except Exception:
            text = ""
        m = re.search(r'(\d{1,3})\s*%', text)
        if m:
            return min(int(m.group(1)), 100)

    # Fallback: поиск строки с наибольшим числом жёлто-зелёных пикселей бара
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    best = 0
    for ri in range(roi.shape[0]):
        row = hsv[ri, :, :]
        px = row[(row[:, 0] >= 13) & (row[:, 0] <= 32) &
                 (row[:, 1] > 60) & (row[:, 2] > 150)]
        if len(px) > best:
            best = len(px)
    return min(int(best / max(roi.shape[1], 1) * 100), 100)


def _try_read() -> dict | None:
    """Один цикл: захват фиксированных ROI → OCR координат и прогресса."""
    coord_roi    = _grab_region(_COORD_X_REF,    _COORD_Y_REF,    _COORD_W_REF,    _COORD_H_REF)
    progress_roi = _grab_region(_PROGRESS_X_REF, _PROGRESS_Y_REF, _PROGRESS_W_REF, _PROGRESS_H_REF)

    _dbg = _os.path.dirname(_LOG_PATH)
    try:
        cv2.imwrite(_os.path.join(_dbg, 'roy_dbg_coord_roi.png'),    coord_roi)
        cv2.imwrite(_os.path.join(_dbg, 'roy_dbg_progress_roi.png'), progress_roi)
    except Exception:
        pass

    coords  = _ocr_coords(coord_roi)
    percent = _measure_progress(progress_roi)
    _log(f"_try_read: coords={coords} percent={percent}%")

    if coords is None:
        return None

    kingdom, x, y = coords
    return {
        'kingdom': kingdom,
        'x':       x,
        'y':       y,
        'percent': percent,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Debug-утилита (запускать из C:\BattleBot: python roy/exchange_reader.py Биржа_15.04.png)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        img_path = sys.argv[1]
        img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"Не удалось загрузить: {img_path}")
            sys.exit(1)

        print(f"Изображение: {img.shape[1]}x{img.shape[0]}")
        print(f"ROI координат: x={_COORD_X_REF}, y={_COORD_Y_REF}, w={_COORD_W_REF}, h={_COORD_H_REF}")

        coord_roi    = img[_COORD_Y_REF:_COORD_Y_REF+_COORD_H_REF,
                           _COORD_X_REF:_COORD_X_REF+_COORD_W_REF]
        progress_roi = img[_PROGRESS_Y_REF:_PROGRESS_Y_REF+_PROGRESS_H_REF,
                           _PROGRESS_X_REF:_PROGRESS_X_REF+_PROGRESS_W_REF]

        cv2.imwrite('debug_coord_roi.png',    coord_roi)
        cv2.imwrite('debug_progress_roi.png', progress_roi)
        print("Сохранено: debug_coord_roi.png, debug_progress_roi.png")

        coords  = _ocr_coords(coord_roi)
        percent = _measure_progress(progress_roi)
        print(f"Координаты: {coords}")
        print(f"Прогресс:   {percent}%")
    else:
        print("Ждём диалог биржи (Ctrl+C для выхода)...")
        while True:
            result = read_once()
            if result:
                print(f"Найдено: {result}")
            time.sleep(0.5)
