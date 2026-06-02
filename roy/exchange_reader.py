"""
exchange_reader.py — OCR диалога биржи наёмников.

Извлекает:
  - Координаты: K (гос), X, Y из красной строки в верхней части диалога
  - Процент выкупа: из текста «Прогресс сделок: XX%»

Алгоритм:
  1. Захват центральных 60% экрана (monitors[1]) — диалог всегда центрирован
  2. Верхняя половина захвата → OCR координат K/X/Y
  3. Нижняя половина захвата → OCR прогресса
  4. Парсинг результата регулярным выражением

Не зависит от калибровки coord_manager — работает на любом разрешении.
"""

import re
import time
import os as _os
import datetime as _datetime

import cv2
import numpy as np

_LOG_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'roy_debug.log')
_DBG_DIR   = _os.path.dirname(_LOG_PATH)

def _log(msg: str):
    line = f"{_datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]} [OCR] {msg}"
    print(line)
    try:
        with open(_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

try:
    import sys
    import shutil
    import pytesseract

    def _find_tesseract() -> str | None:
        # Релиз (PyInstaller): tesseract_bin лежит рядом с TotalHunter.exe
        if getattr(sys, 'frozen', False):
            bundled = _os.path.join(_os.path.dirname(sys.executable),
                                    "tesseract_bin", "tesseract.exe")
            if _os.path.isfile(bundled):
                return bundled
            # В релизе нет системного поиска — только сборка
            return None

        # Dev-режим: автопоиск в системе (PATH → стандартные пути)
        found = shutil.which("tesseract")
        if found:
            return found
        for path in [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'D:\Program Files\Tesseract-OCR\tesseract.exe',
            r'D:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]:
            if _os.path.isfile(path):
                return path
        return None

    _tess_path = _find_tesseract()
    if _tess_path:
        pytesseract.pytesseract.tesseract_cmd = _tess_path
    else:
        if getattr(sys, 'frozen', False):
            _log("КРИТИЧЕСКАЯ ОШИБКА: tesseract_bin не найден рядом с TotalHunter.exe. "
                 "Проверьте целостность сборки — папка tesseract_bin должна быть рядом с EXE.")
        else:
            _log("КРИТИЧЕСКАЯ ОШИБКА: Tesseract OCR не найден на ПК. "
                 "Установите Tesseract для работы модуля РОЙ. "
                 "Скачайте: https://github.com/UB-Mannheim/tesseract/wiki")
        pytesseract = None

except ImportError:
    pytesseract = None

try:
    import mss
except ImportError:
    mss = None

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
    # Пауза перед первым захватом — игра успевает полностью отрисовать диалог
    time.sleep(0.6)
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

def _grab_center_roi() -> tuple[np.ndarray, np.ndarray]:
    """
    Захватывает центральные 60% первичного монитора (monitors[1]).
    Диалог биржи всегда центрирован → попадает в кадр на любом разрешении,
    без зависимости от калибровки coord_manager.
    Возвращает (coord_roi, progress_roi): верхняя и нижняя половины захвата.
    """
    with mss.mss() as sct:
        mon    = sct.monitors[1]
        left   = mon["left"] + int(mon["width"]  * 0.20)
        top    = mon["top"]  + int(mon["height"] * 0.20)
        width  = int(mon["width"]  * 0.60)
        height = int(mon["height"] * 0.60)
        region = {"left": left, "top": top, "width": max(width, 1), "height": max(height, 1)}
        _log(f"_grab_center_roi: mon={mon['width']}x{mon['height']} → {region}")
        raw  = sct.grab(region)
        full = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR)

    mid          = full.shape[0] // 2
    coord_roi    = full[:mid, :]   # верхняя половина — K:X:Y
    progress_roi = full[mid:, :]   # нижняя половина — прогресс сделок
    return coord_roi, progress_roi


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
    """Один цикл: захват центра экрана → OCR координат и прогресса."""
    coord_roi, progress_roi = _grab_center_roi()

    try:
        cv2.imwrite(_os.path.join(_DBG_DIR, 'roy_dbg_coord_roi.png'),    coord_roi)
        cv2.imwrite(_os.path.join(_DBG_DIR, 'roy_dbg_progress_roi.png'), progress_roi)
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

        h, w = img.shape[:2]
        x0 = int(w * 0.20); y0 = int(h * 0.20)
        x1 = int(w * 0.80); y1 = int(h * 0.80)
        print(f"Изображение: {w}x{h}, центр 60%: x={x0}-{x1}, y={y0}-{y1}")

        center       = img[y0:y1, x0:x1]
        mid          = center.shape[0] // 2
        coord_roi    = center[:mid, :]
        progress_roi = center[mid:, :]

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
