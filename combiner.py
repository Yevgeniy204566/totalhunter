# combiner.py
"""
CombinerEngine — автокомбинирование материалов в окне «Комбинирование».
Разрешение: 1920×1080. Константы сетки откалиброваны по скринам.
"""
import re
import time
import random
import threading
from dataclasses import dataclass
from typing import Callable

try:
    import numpy as np
    import pyautogui
    import mss
    import cv2
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

# ══════════════════════════════════════════════════════════════
#  КОНСТАНТЫ СЕТКИ  (откалибровать если нужно)  1920×1080
# ══════════════════════════════════════════════════════════════
COMBO_GRID_X       = 548   # X левого края первой карточки
COMBO_GRID_Y       = 248   # Y верхнего края первой карточки
COMBO_SLOT_W       = 99    # ширина слота (с отступом)
COMBO_SLOT_H       = 92    # высота слота (с отступом)
COMBO_COLS         = 8     # всего колонок (последняя [7] — всегда пропуск)
COMBO_ROWS_VISIBLE = 4     # строк видимо одновременно

# Подрегион числа внутри слота (x_off, y_off, w, h)
NUM_ROI = (5, 65, 82, 20)  # x_off, y_off, width, height

# Точка клика — левый нижний угол (25% / 85% от слота)
CLICK_X_RATIO = 0.25
CLICK_Y_RATIO = 0.85

# Точка скролла и проверки Anti-Stuck
COMBO_SCROLL_PT  = (960, 430)
COMBO_HEADER_PT  = (960, 175)   # пиксель заголовка окна

GRID_DIFF_THRESHOLD = 0.03  # 3% — скролл меняет картинку, шум — нет

# ══════════════════════════════════════════════════════════════
#  DATA
# ══════════════════════════════════════════════════════════════

@dataclass
class CardInfo:
    row: int
    col: int
    count: int       # 0 = skip
    click_x: int
    click_y: int


# ══════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

def _images_differ(a: 'np.ndarray', b: 'np.ndarray') -> bool:
    """True если изображения достаточно разные (скролл прошёл)."""
    if a.shape != b.shape:
        return True
    diff = np.abs(a.astype(np.int32) - b.astype(np.int32))
    return float(diff.mean()) / 255.0 > GRID_DIFF_THRESHOLD


# ══════════════════════════════════════════════════════════════
#  ЧИСТЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

def parse_number(text: str) -> int:
    """Parse OCR string '4.1k'->4100, '1.2M'->1200000, '500'->500. Returns 0 on failure."""
    s = text.strip().lower().replace(',', '.')
    m = re.match(r'^(\d+(?:\.\d+)?)\s*([km]?)$', s)
    if not m:
        return 0
    try:
        val = float(m.group(1))
        suffix = m.group(2)
        if suffix == 'k':
            val *= 1_000
        elif suffix == 'm':
            val *= 1_000_000
        return int(val)
    except (ValueError, OverflowError):
        return 0


# ══════════════════════════════════════════════════════════════
#  CombinerEngine
# ══════════════════════════════════════════════════════════════

class CombinerEngine:
    def __init__(self):
        self.delay: float = 0.1
        self._stop_requested: bool = False
        self._thread: 'threading.Thread | None' = None

    # ── OCR ──────────────────────────────────────────────────

    def _zoom_ocr(self, img_bgr: 'np.ndarray') -> str:
        """Upscale x2, invert, OTSU threshold, tesseract digits+suffixes. Assumes light text on dark card background."""
        h, w = img_bgr.shape[:2]
        big = cv2.resize(img_bgr, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        inv = cv2.bitwise_not(gray)
        _, thresh = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cfg = '--psm 7 -c tessedit_char_whitelist=0123456789kKmM.,'
        return pytesseract.image_to_string(thresh, config=cfg).strip()

    def _capture_grid(self) -> 'np.ndarray':
        """Screenshot всей видимой сетки (BGR)."""
        with mss.mss() as sct:
            mon = {
                "top":    COMBO_GRID_Y,
                "left":   COMBO_GRID_X,
                "width":  COMBO_SLOT_W * COMBO_COLS,
                "height": COMBO_SLOT_H * COMBO_ROWS_VISIBLE,
            }
            raw = sct.grab(mon)
            return np.array(raw)[:, :, :3]

    def scan_row(self, grid_img: 'np.ndarray', row_idx: int) -> 'list[CardInfo]':
        """Читает ряд сетки, возвращает список CardInfo. Последний столбец пропускается."""
        cards: list[CardInfo] = []
        xo, yo, nw, nh = NUM_ROI
        for col in range(COMBO_COLS - 1):   # последняя колонка = высшее качество, пропуск
            sx = col * COMBO_SLOT_W
            sy = row_idx * COMBO_SLOT_H
            roi = grid_img[sy + yo : sy + yo + nh, sx + xo : sx + xo + nw]
            if roi.size == 0:
                continue
            text = self._zoom_ocr(roi)
            count = parse_number(text)
            abs_x = COMBO_GRID_X + sx + int(COMBO_SLOT_W * CLICK_X_RATIO)
            abs_y = COMBO_GRID_Y + sy + int(COMBO_SLOT_H * CLICK_Y_RATIO)
            cards.append(CardInfo(row=row_idx, col=col, count=count,
                                  click_x=abs_x, click_y=abs_y))
        return cards
