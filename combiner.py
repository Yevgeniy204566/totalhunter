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
NUM_ROI = (5, 65, 82, 20)

# Точка клика — левый нижний угол (25% / 85% от слота)
CLICK_X_RATIO = 0.25
CLICK_Y_RATIO = 0.85

# Точка скролла и проверки Anti-Stuck
COMBO_SCROLL_PT  = (960, 430)
COMBO_HEADER_PT  = (960, 175)   # пиксель заголовка окна


# ══════════════════════════════════════════════════════════════
#  ЧИСТЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════

def parse_number(text: str) -> int:
    """Parse OCR string '4.1k'->4100, '1.2M'->1200000, '500'->500. Returns 0 on failure."""
    s = text.strip().lower().replace(',', '.')
    m = re.match(r'^([\d.]+)\s*([km]?)$', s)
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
