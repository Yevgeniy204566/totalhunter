"""
exchange_reader.py — OCR диалога биржи наёмников.

Извлекает:
  - Координаты: K (гос), X, Y из красной строки в верхней части диалога
  - Процент выкупа: из зелёной полосы «Прогресс сделок» внизу диалога

Алгоритм:
  1. Скриншот + поиск диалога по характерному заголовку (HSV-маска бежевого фона)
  2. Crop верхней зоны → цветовая маска красного текста → pytesseract
  3. Crop нижней зоны → измерение длины зелёной полосы → % заполнения
  4. Проверка что окно открылось (контрольная точка — заголовок)

Вызывается из engine.py после клика YOLO по бирже.
"""

import re
import time

import cv2
import numpy as np

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import mss
except ImportError:
    mss = None

from coord_manager import coord_manager


# ── Цветовые диапазоны (HSV) ──────────────────────────────────────────────────

# Текст координат: тёмно-оранжевый/коричневый (H≈5-15, S высокое, V низкое)
_RED_LOW1  = np.array([0,  150, 40])
_RED_HIGH1 = np.array([18, 255, 160])
# Второй диапазон на случай более светлого варианта
_RED_LOW2  = np.array([160, 100, 40])
_RED_HIGH2 = np.array([180, 255, 160])

# Зелёная полоса прогресса (в игре жёлто-зелёный, H≈13-30 в OpenCV HSV)
_GREEN_LOW  = np.array([13,  60, 60])
_GREEN_HIGH = np.array([32, 255, 255])

# Бежевый/светлый фон заголовка диалога (для поиска окна)
_DIALOG_BG_LOW  = np.array([15,  20, 180])
_DIALOG_BG_HIGH = np.array([35, 100, 255])

# ── Относительные зоны внутри диалога (от верхнего левого угла) ──────────────
# Координаты — строка в ~15% высоты диалога
_COORD_ROI_REL    = (0.02, 0.05, 0.98, 0.13)   # строка K/X/Y под заголовком
_PROGRESS_ROI_REL = (0.02, 0.57, 0.98, 0.72)   # текст «Прогресс сделок: XX%» + бар

# Минимальный размер диалога в пикселях (защита от ложных срабатываний)
_MIN_DIALOG_W = 200
_MIN_DIALOG_H = 150

# Таймаут ожидания появления диалога (сек)
_DIALOG_TIMEOUT = 3.0


# ─────────────────────────────────────────────────────────────────────────────
# Публичный API
# ─────────────────────────────────────────────────────────────────────────────

def wait_and_read(timeout: float = _DIALOG_TIMEOUT) -> dict | None:
    """
    Ждёт появления диалога биржи и читает данные.
    Возвращает {'kingdom': int, 'x': int, 'y': int, 'percent': int}
    или None если диалог не появился / не удалось распознать.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = _try_read()
        if result:
            return result
        time.sleep(0.3)
    return None


def read_once() -> dict | None:
    """Читает диалог один раз без ожидания."""
    return _try_read()


# ─────────────────────────────────────────────────────────────────────────────
# Внутренняя логика
# ─────────────────────────────────────────────────────────────────────────────

def _grab_screen() -> np.ndarray:
    """Захватывает полный экран в BGR."""
    if mss is None:
        raise RuntimeError("mss not installed")
    with mss.mss() as sct:
        mon = sct.monitors[1]
        raw = sct.grab(mon)
        return cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR)


def _find_dialog(frame: np.ndarray) -> tuple | None:
    """
    Ищет диалог биржи на экране.
    Возвращает (x, y, w, h) прямоугольника диалога или None.

    Метод: ищем крупный прямоугольник с бежевым/кремовым фоном,
    характерным для диалоговых окон в Total Battle.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, _DIALOG_BG_LOW, _DIALOG_BG_HIGH)

    # Морфология для заполнения пробелов
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # Берём самый большой контур
    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)

    if w < _MIN_DIALOG_W or h < _MIN_DIALOG_H:
        return None

    return (x, y, w, h)


def _crop_roi(frame: np.ndarray, dialog: tuple, rel: tuple) -> np.ndarray:
    """Вырезает относительный регион из диалога."""
    dx, dy, dw, dh = dialog
    x1 = int(dx + rel[0] * dw)
    y1 = int(dy + rel[1] * dh)
    x2 = int(dx + rel[2] * dw)
    y2 = int(dy + rel[3] * dh)
    return frame[y1:y2, x1:x2]


def _ocr_coords(roi: np.ndarray) -> tuple | None:
    """
    Применяет маску красного цвета и pytesseract к зоне координат.
    Ищет паттерн вида: K:471 X:383 Y:812 или К:471 X:383 Y:812
    Возвращает (kingdom, x, y) или None.
    """
    if pytesseract is None:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, _RED_LOW1, _RED_HIGH1)
    m2 = cv2.inRange(hsv, _RED_LOW2, _RED_HIGH2)
    mask = cv2.bitwise_or(m1, m2)

    # Белый текст на чёрном фоне
    result = np.zeros_like(roi)
    result[mask > 0] = (255, 255, 255)
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

    # Масштабируем для лучшего OCR
    scale = 3
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    config = "--psm 7 -c tessedit_char_whitelist=KkХхXxYy:0123456789 "
    text = pytesseract.image_to_string(gray, config=config).strip()

    return _parse_coords(text)


def _parse_coords(text: str) -> tuple | None:
    """
    Парсит строку координат.
    Поддерживает форматы:
      K:471 X:383 Y:812
      К:471 X:383 Y:812   (кириллица)
      K:471X:383Y:812     (без пробелов)
    """
    # Нормализуем кириллицу
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
    Fallback: измерение ширины зелёной полосы.
    Возвращает 0-100.
    """
    # Метод 1: OCR текста (надёжнее)
    if pytesseract is not None:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Темный текст на светлом фоне — бинаризуем
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        scale = 3
        thresh = cv2.resize(thresh, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        config = '--psm 6 -c tessedit_char_whitelist=0123456789%: '
        text = pytesseract.image_to_string(thresh, config=config)
        m = re.search(r'(\d{1,3})\s*%', text)
        if m:
            return min(int(m.group(1)), 100)

    # Fallback: поиск строки с макс кол-вом пикселей зелёного бара
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    best = 0
    for ri in range(roi.shape[0]):
        row = hsv[ri, :, :]
        px = row[(row[:, 0] >= 10) & (row[:, 0] <= 24) &
                 (row[:, 1] > 60) & (row[:, 2] > 150)]
        if len(px) > best:
            best = len(px)
    return min(int(best / max(roi.shape[1], 1) * 100), 100)


def _try_read() -> dict | None:
    """Один цикл: скриншот → поиск диалога → OCR."""
    frame = _grab_screen()
    dialog = _find_dialog(frame)
    if dialog is None:
        return None

    coord_roi    = _crop_roi(frame, dialog, _COORD_ROI_REL)
    progress_roi = _crop_roi(frame, dialog, _PROGRESS_ROI_REL)

    coords  = _ocr_coords(coord_roi)
    percent = _measure_progress(progress_roi)

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
# Debug-утилита (запускать вручную: python exchange_reader.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        # Тест на конкретном файле: python exchange_reader.py Биржа_15.04.png
        img_path = sys.argv[1]
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"Не удалось загрузить: {img_path}")
            sys.exit(1)

        dialog = _find_dialog(frame)
        print(f"Диалог: {dialog}")

        if dialog:
            coord_roi    = _crop_roi(frame, dialog, _COORD_ROI_REL)
            progress_roi = _crop_roi(frame, dialog, _PROGRESS_ROI_REL)

            cv2.imwrite('debug_coord_roi.png',    coord_roi)
            cv2.imwrite('debug_progress_roi.png', progress_roi)
            print("Сохранено: debug_coord_roi.png, debug_progress_roi.png")

            coords  = _ocr_coords(coord_roi)
            percent = _measure_progress(progress_roi)
            print(f"Координаты: {coords}")
            print(f"Прогресс:   {percent}%")
        else:
            print("Диалог не найден")
    else:
        # Живой захват с экрана
        print("Ждём диалог биржи (Ctrl+C для выхода)...")
        while True:
            result = read_once()
            if result:
                print(f"Найдено: {result}")
            time.sleep(0.5)
