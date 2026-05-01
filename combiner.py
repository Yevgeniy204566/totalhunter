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

from coord_manager import coord_manager

# ══════════════════════════════════════════════════════════════
#  КОНСТАНТЫ СЕТКИ  —  эталон 1920×1080
#  Anchor: центр клика карточки [col=0, row=0] = (673, 416)
#  GRID_X = anchor_x - SLOT_W//2, GRID_Y = anchor_y - SLOT_H//2
#  Все координаты -> coord_manager.to_screen() / to_region()
# ══════════════════════════════════════════════════════════════
COMBO_GRID_X       = 630   # X левого края первой карточки (ref 1920×1080)
COMBO_GRID_Y       = 372   # Y начала первой строки карточек (пропуск 2 строк описания)
COMBO_SLOT_W       = 87    # ширина слота
COMBO_SLOT_H       = 88    # высота слота
COMBO_COLS         = 7     # 6 рабочих колонок + 1 синяя (последняя пропускается)
COMBO_ROWS_VISIBLE = 5     # видимых строк карточек (подтверждено пользователем)

# ROI вариант А: расширен для надёжного захвата цифры
NUM_ROI = (12, 40, 52, 24)  # калиброван пользователем: цифра в (644,415)..(692,431)  # узкая полоса x=20..67, y=28..60 — только зона цифры

CLICK_X_RATIO = 0.5   # центр карточки по X
CLICK_Y_RATIO = 0.5   # центр карточки по Y

# Точка скролла и проверки Anti-Stuck (ref 1920×1080)
COMBO_SCROLL_PT   = (934, 400)
COMBO_HEADER_PT   = (970, 84)
COMBO_SCROLL_CLICKS = 27   # ~3 строки (264px): строка 4 станет строкой 1 следующего цикла
SAFE_ZONE           = (700, 180)  # курсор уходит выше окна (Anti-Tooltip)
COMBO_MAX_CLICKS  = 1000   # лимит кликов на карточку (защита от OCR-ошибок)

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
    """Parse OCR string '4.1k'->4100, '500'->500. Returns 0 on failure. Max = thousands."""
    s = text.strip().lower().replace(',', '.')
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(k?)$', s)
    if not m:
        return 0
    try:
        val = float(m.group(1))
        if m.group(2) == 'k':
            val *= 1_000
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

    def _get_verified_number(self, crop: 'np.ndarray', row: int, col: int) -> int:
        """Strict Consensus OCR по протоколу Архитектора (Gemini).
        Метод А: Otsu. Метод Б: Contrast Stretch(2.0) + Adaptive.
        Совпадение: parse_number(A) == parse_number(B) > 0.
        Spectrum Shift: dilate 1px, max 3 итерации. Иначе -> 0.
        """
        h, w = crop.shape[:2]
        big = cv2.resize(crop, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        cfg = '--psm 7 -c tessedit_char_whitelist=0123456789kM.'
        kernel = np.ones((2, 2), np.uint8)

        def _method_a(g):
            """Base: Grayscale -> Otsu (стабильный)."""
            inv = cv2.bitwise_not(g)
            _, t = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return pytesseract.image_to_string(t, config=cfg).strip()

        def _method_b(g):
            """New Fixed: Grayscale -> GaussianBlur(3,3) -> THRESH_BINARY_INV(127)."""
            blurred = cv2.GaussianBlur(g, (3, 3), 0)
            _, t = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)
            return pytesseract.image_to_string(t, config=cfg).strip()

        # Spectrum Shift — +50 первым
        shifts = [50, 0, 25, -25, -50]
        a_readings = []
        b_readings = []

        for iteration, shift in enumerate(shifts):
            shifted = np.clip(gray.astype(np.int32) + shift, 0, 255).astype(np.uint8)
            text_a = _method_a(shifted)
            text_b = _method_b(shifted)
            na = parse_number(text_a)
            nb = parse_number(text_b)

            # Consensus: оба совпали
            if text_a and text_b and text_a == text_b and na > 0:
                print(f"[OCR] Slot {row},{col} iter={iteration} shift={shift:+d} | A:'{text_a}' B:'{text_b}' | Match:{na} CONSENSUS")
                return na

            if na > 0:
                a_readings.append(na)
            if nb > 0:
                b_readings.append(nb)

            print(f"[OCR] Slot {row},{col} iter={iteration} shift={shift:+d} | A:'{text_a}' B:'{text_b}' | Match:0")

        from collections import Counter

        # WEIGHTED_A: A стабильно читает одно число 3+/5
        if a_readings:
            most_a, freq_a = Counter(a_readings).most_common(1)[0]
            if freq_a >= 3:
                print(f"[OCR] Slot {row},{col} WEIGHTED_A: {most_a} x{freq_a}/5")
                return most_a

        # WEIGHTED_B: B стабильно читает одно число 2+/5 (Double-Hit Stability)
        if b_readings:
            most_b, freq_b = Counter(b_readings).most_common(1)[0]
            if freq_b >= 2:
                print(f"[OCR] Slot {row},{col} WEIGHTED_B: {most_b} x{freq_b}/5")
                return most_b

        # B_ONLY удалён по протоколу Архитектора (AP-1: один хит = шум)
        return 0

    def _zoom_ocr(self, img_bgr: 'np.ndarray') -> str:
        """Оставлен для совместимости с тестами — делегирует в _get_verified_number."""
        n = self._get_verified_number(img_bgr, -1, -1)
        return str(n) if n > 0 else ''

    def calibrate_roi(self) -> None:
        """Сохраняет 5 вариантов ROI с шагом 5px по Y для ручного выбора лучшего."""
        grid = self._capture_grid()
        xo, _, nw, nh = NUM_ROI
        for offset in range(5):
            y_off = 45 + offset * 5   # 45, 50, 55, 60, 65
            roi = grid[y_off:y_off+nh, xo:xo+nw]
            big = cv2.resize(roi, (roi.shape[1]*8, roi.shape[0]*8), interpolation=cv2.INTER_NEAREST)
            text = self._zoom_ocr(roi) if roi.size > 0 else ""
            cv2.putText(big, f"y={y_off} '{text.strip()}'", (4, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imwrite(f"roi_calib_y{y_off}.png", big)

    def _debug_save_roi(self, row: int, col: int, path: str = "debug_roi.png") -> str:
        """Сохранить ROI карточки [row, col] для диагностики OCR."""
        grid = self._capture_grid()
        xo, yo, nw, nh = NUM_ROI
        sx, sy = col * COMBO_SLOT_W, row * COMBO_SLOT_H
        roi = grid[sy+yo:sy+yo+nh, sx+xo:sx+xo+nw]
        big = cv2.resize(roi, (roi.shape[1]*8, roi.shape[0]*8), interpolation=cv2.INTER_NEAREST)
        text = self._zoom_ocr(roi)
        cv2.putText(big, f"'{text.strip()}'", (4, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.imwrite(path, big)
        return text.strip()

    def _capture_grid(self, y_offset: int = 0) -> 'np.ndarray':
        """Screenshot видимой сетки. y_offset сдвигает захват для динамического поиска строк."""
        ref_w = COMBO_SLOT_W * COMBO_COLS
        ref_h = COMBO_SLOT_H * COMBO_ROWS_VISIBLE
        sx, sy, sw, sh = coord_manager.to_region(COMBO_GRID_X, COMBO_GRID_Y + y_offset, ref_w, ref_h)
        with mss.mss() as sct:
            raw = sct.grab({"top": sy, "left": sx, "width": sw, "height": sh})
        img = np.array(raw)[:, :, :3]
        if img.shape[:2] != (ref_h, ref_w):
            img = cv2.resize(img, (ref_w, ref_h))
        return img

    def _find_best_y_offset(self) -> int:
        """После скролла ищем Y смещение где карточки выровнены (OCR находит числа)."""
        best_offset = 0
        best_score = 0
        for y_off in [0, 22, 44, 66, 11, 33, 55, 77]:
            grid = self._capture_grid(y_off)
            score = 0
            xo, yo, nw, nh = NUM_ROI
            for col in range(min(3, COMBO_COLS - 1)):  # быстрая проверка первых 3 колонок
                for row in range(COMBO_ROWS_VISIBLE):
                    sx = col * COMBO_SLOT_W
                    sy = row * COMBO_SLOT_H
                    roi = grid[sy+yo:sy+yo+nh, sx+xo:sx+xo+nw]
                    if roi.size == 0:
                        continue
                    n = self._get_verified_number(roi, row, col)
                    if n > 0:
                        score += 1
            if score > best_score:
                best_score = score
                best_offset = y_off
        return best_offset

    def scan_row(self, grid_img: 'np.ndarray', row_idx: int,
                 y_offset: int = 0) -> 'list[CardInfo]':
        """Читает ряд сетки. y_offset — смещение после скролла для точного клика."""
        cards: list[CardInfo] = []
        xo, yo, nw, nh = NUM_ROI
        for col in range(COMBO_COLS - 1):
            sx = col * COMBO_SLOT_W
            sy = row_idx * COMBO_SLOT_H
            roi = grid_img[sy + yo : sy + yo + nh, sx + xo : sx + xo + nw]
            if roi.size == 0:
                continue
            count = self._get_verified_number(roi, row_idx, col)
            ref_x = COMBO_GRID_X + sx + int(COMBO_SLOT_W * CLICK_X_RATIO)
            ref_y = COMBO_GRID_Y + y_offset + sy + int(COMBO_SLOT_H * CLICK_Y_RATIO)
            abs_x, abs_y = coord_manager.to_screen(ref_x, ref_y)
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
        return True

    def _hide_cursor(self) -> None:
        """Anti-Tooltip: уводим курсор выше окна с небольшим рандомом."""
        base_x, base_y = coord_manager.to_screen(*SAFE_ZONE)
        rx = base_x + random.randint(-60, 60)
        ry = base_y + random.randint(-30, 30)
        pyautogui.moveTo(rx, ry, duration=0.2)
        time.sleep(0.1)

    def _read_beacon(self, grid: 'np.ndarray') -> 'tuple[int, int]':
        """Шаг 2: маяк с последней строки — ищем первую непустую ячейку слева направо."""
        last_row = COMBO_ROWS_VISIBLE - 1
        xo, yo, nw, nh = NUM_ROI
        sy = last_row * COMBO_SLOT_H
        for col in range(COMBO_COLS - 1):
            sx = col * COMBO_SLOT_W
            roi = grid[sy+yo:sy+yo+nh, sx+xo:sx+xo+nw]
            val = self._fast_ocr(roi)
            if val > 0:
                y_screen = COMBO_GRID_Y + last_row * COMBO_SLOT_H + int(COMBO_SLOT_H * CLICK_Y_RATIO)
                print(f"[BEACON] beacon: row={last_row} col={col} val={val} y={y_screen}")
                return val, y_screen
        return 0, 0

    def _fast_ocr(self, roi: 'np.ndarray') -> int:
        """Быстрый OCR одним методом (без spectrum shift) для поиска маяка."""
        if roi.size == 0:
            return 0
        h, w = roi.shape[:2]
        big = cv2.resize(roi, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        inv = cv2.bitwise_not(gray)
        _, thresh = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cfg = '--psm 7 -c tessedit_char_whitelist=0123456789k.'
        text = pytesseract.image_to_string(thresh, config=cfg).strip()
        return parse_number(text)

    def _find_beacon_offset(self, beacon_val: int, y_start: int) -> int:
        """Быстрый поиск маяка: только 3 оффсета, 1 быстрый OCR каждый."""
        if beacon_val == 0:
            return 0
        xo, yo, nw, nh = NUM_ROI
        for y_off in [0, 44, 22]:   # стандартный -> половина -> четверть строки
            grid = self._capture_grid(y_off)
            for row_idx in range(COMBO_ROWS_VISIBLE):
                sy = row_idx * COMBO_SLOT_H
                roi = grid[sy+yo:sy+yo+nh, xo:xo+nw]
                val = self._fast_ocr(roi)
                if val == beacon_val:
                    print(f"[BEACON] found={val} y_off={y_off} row={row_idx}")
                    return y_off
        print(f"[BEACON] {beacon_val} not found -> y_off=0")
        return 0

    # ── Scroll ───────────────────────────────────────────────

    def _scroll_down(self) -> None:
        sx, sy = coord_manager.to_screen(*COMBO_SCROLL_PT)
        pyautogui.moveTo(sx, sy)
        pyautogui.scroll(-COMBO_SCROLL_CLICKS)
        time.sleep(0.8)

    # ── Main loop ────────────────────────────────────────────

    def _scroll_to_top(self) -> None:
        """Прокрутить список карточек в самый верх перед стартом."""
        sx, sy = coord_manager.to_screen(*COMBO_SCROLL_PT)
        pyautogui.moveTo(sx, sy)
        for _ in range(40):
            pyautogui.scroll(20)
            time.sleep(0.08)
        time.sleep(0.8)

    def _run(self, status_callback: 'Callable[[str], None]') -> None:
        max_cycles = 200
        cycle = 0
        current_y_off = 0  # текущее Y-смещение захвата (обновляется маяком)
        while not self._stop_requested and cycle < max_cycles:
            cycle += 1
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

            self._hide_cursor()
            grid = self._capture_grid(current_y_off)

            for row_idx in range(COMBO_ROWS_VISIBLE):
                if self._stop_requested:
                    return
                cards = self.scan_row(grid, row_idx, current_y_off)
                for card in cards:
                    if self._stop_requested:
                        return
                    if card.count < 4:
                        continue
                    n_clicks = min(card.count // 4, COMBO_MAX_CLICKS)
                    status_callback(f"Ряд {row_idx + 1}, кол {card.col + 1} — {n_clicks} кликов")
                    self.click_card(card, n_clicks)
                    self._hide_cursor()  # Anti-Tooltip после каждого клика

            # Шаг 2: зафиксировать маяк перед скроллом
            self._hide_cursor()
            grid_pre = self._capture_grid(current_y_off)
            beacon_val, beacon_y = self._read_beacon(grid_pre)

            time.sleep(0.8)
            before = self._capture_grid(current_y_off)
            self._scroll_down()
            after = self._capture_grid(current_y_off)

            # Шаг 3: найти маяк после скролла -> вычислить новый y_offset
            new_y_off = self._find_beacon_offset(beacon_val, beacon_y)
            if new_y_off != current_y_off:
                status_callback(f"Beacon: смещение +{new_y_off}px")
            current_y_off = new_y_off

            if not _images_differ(before, after):
                status_callback("Готово — конец списка")
                return

        status_callback("Остановлено")
