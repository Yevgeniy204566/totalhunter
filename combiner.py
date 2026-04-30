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
COMBO_GRID_X       = 504   # X левого края первой карточки
COMBO_GRID_Y       = 139   # Y верхнего края первой карточки
COMBO_SLOT_W       = 87    # ширина слота (с отступом)
COMBO_SLOT_H       = 87    # высота слота (с отступом)
COMBO_COLS         = 8     # всего колонок (последняя [7] — всегда пропуск)
COMBO_ROWS_VISIBLE = 6     # строк видимо одновременно

# Подрегион числа внутри слота (x_off, y_off, w, h)
NUM_ROI = (49, 0, 38, 30)  # x_off, y_off, width, height

# Точка клика — левый нижний угол (25% / 85% от слота)
CLICK_X_RATIO = 0.25
CLICK_Y_RATIO = 0.85

# Точка скролла и проверки Anti-Stuck
COMBO_SCROLL_PT  = (939, 400)
COMBO_HEADER_PT  = (970, 84)   # пиксель заголовка окна
COMBO_SCROLL_CLICKS = 3         # pyautogui scroll units (tune if needed)

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
        if not _DEPS_OK:
            raise RuntimeError("CombinerEngine requires numpy, cv2, pyautogui, mss, pytesseract")
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

    def click_card(self, card: CardInfo, n_clicks: int) -> None:
        """Click card n_clicks times with ±5px randomization. Stops early if _stop_requested."""
        for _ in range(n_clicks):
            if self._stop_requested:
                return
            dx = random.randint(-5, 5)
            dy = random.randint(-5, 5)
            pyautogui.click(card.click_x + dx, card.click_y + dy)
            time.sleep(self.delay)

    def stop(self) -> None:
        self._stop_requested = True

    def start(self, delay: float, status_callback: 'Callable[[str], None]') -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_requested = False
        self.delay = delay
        self._thread = threading.Thread(
            target=self._run, args=(status_callback,), daemon=True
        )
        self._thread.start()

    # ── Anti-Stuck ───────────────────────────────────────────

    def _check_window_visible(self) -> bool:
        """True если пиксель заголовка не серый (окно не перекрыто)."""
        try:
            with mss.mss() as sct:
                px = sct.grab({"top": COMBO_HEADER_PT[1], "left": COMBO_HEADER_PT[0],
                               "width": 1, "height": 1})
                px_arr = np.array(px)
                b_val, g_val, r_val = int(px_arr[0, 0, 0]), int(px_arr[0, 0, 1]), int(px_arr[0, 0, 2])
            return not (30 <= r_val <= 90 and 30 <= g_val <= 90 and 30 <= b_val <= 90)
        except Exception:
            return True   # при ошибке — не блокируем

    # ── Scroll ───────────────────────────────────────────────

    def _scroll_down(self) -> None:
        pyautogui.moveTo(COMBO_SCROLL_PT[0], COMBO_SCROLL_PT[1])
        pyautogui.scroll(-COMBO_SCROLL_CLICKS)
        time.sleep(1.0)

    # ── Main loop ────────────────────────────────────────────

    def _run(self, status_callback: 'Callable[[str], None]') -> None:
        while not self._stop_requested:
            # Anti-stuck: wait for window to be visible
            for _ in range(3):
                if self._stop_requested:
                    return
                if self._check_window_visible():
                    break
                time.sleep(2.0)
            else:
                status_callback("Окно перекрыто — стоп")
                return

            grid = self._capture_grid()

            for row_idx in range(COMBO_ROWS_VISIBLE):
                if self._stop_requested:
                    return
                cards = self.scan_row(grid, row_idx)
                for card in cards:
                    if self._stop_requested:
                        return
                    if card.count < 4:
                        continue
                    n_clicks = card.count // 4
                    status_callback(f"Ряд {row_idx + 1}, кол {card.col + 1} — {n_clicks} кликов")
                    self.click_card(card, n_clicks)

            # Capture post-combine state as baseline, then scroll and compare
            before = self._capture_grid()
            self._scroll_down()
            after = self._capture_grid()

            if not _images_differ(before, after):
                status_callback("Готово — конец списка")
                return

        status_callback("Остановлено")
