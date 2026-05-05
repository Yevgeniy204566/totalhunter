# crypt_hunter.py
"""
CryptHunter — автосбор склепов через меню Дозорной башни.
Все координаты — константы вверху файла (калибровать под экран).
Разрешение: 1920×1080
"""
import re
import os
import time
import random
import threading
from datetime import datetime

# Heavy game-automation imports — only needed by CryptHunter methods
try:
    import numpy as np
    import pyautogui
    import mss
    import cv2
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    from ultralytics import YOLO
    _GAME_DEPS_AVAILABLE = True
except ImportError:
    _GAME_DEPS_AVAILABLE = False

# Visual button detection (language-independent)
try:
    from button_finder import find_colored_button
    from coord_manager import coord_manager as _cm
    scale_coord        = _cm.to_screen
    scale_region       = _cm.to_region
    scale_dialog       = _cm.to_screen_dialog
    scale_dialog_region = _cm.to_region_dialog
    _VISUAL_NAV_AVAILABLE = True
except ImportError:
    _VISUAL_NAV_AVAILABLE = False

# Template matching (works in browser + any window size)
try:
    from template_finder import find_at_ref, find_in_screen_region
    _TEMPLATE_AVAILABLE = True
except ImportError:
    _TEMPLATE_AVAILABLE = False



# ══════════════════════════════════════════════════════════════
#  КООРДИНАТЫ (откалиброваны 2026-04-09)  1920×1080
# ══════════════════════════════════════════════════════════════

# Иконка Дозорной башни на нижней панели
WT_ICON            = (693, 949)

# Вкладки в боковом меню диалога башни
WT_CRYPTS_TAB      = (684, 462)    # «Склепы и арены» (не менялась)
WT_ARENA_TAB       = (1223, 355)   # «Арена» (для сброса поиска)

# Зона прокрутки списка склепов
WT_SCROLL_AREA     = (1040, 613)

# X-координата кнопки «Перейти» (фиксированная, Y = Y склепа из YOLO)
WT_GOTO_BTN_X      = 1218

# Диалог склепа (после клика на карте)
CRYPT_STUDY_BTN    = (1137, 785)   # кнопка «Исследовать»
CRYPT_OPEN_BTN     = (963, 779)    # кнопка «Открыть» (только R-типы)
# ACCEL_CLOSE_CLICK убран — окно закрывается автоматически когда Картер добирается до склепа

# Время марша — читается в диалоге склепа (там же где масло)
MARCH_TIME_REGION  = (820, 773, 280, 42)   # (x, y, w, h) — строка времени в диалоге склепа

# Ускорение марша
CARTER_EVENT_BAR   = (1239, 122)   # полоса события Картера вверху экрана
ACCEL_USE_BTN      = (1125, 466)   # кнопка «Использовать» в диалоге ускорения
ACCEL_TIME_REGION  = (980, 295, 340, 80)  # OCR времени внутри Carter overlay (y≈295)

# Центральный регион экрана где появляется диалог масла
# Фикс: сужен чтобы не перекрываться с Carter overlay (y<340) и диалогом склепа
OIL_DIALOG_REGION = (700, 340, 460, 280)   # (x, y, w, h) в 1920×1080

# Привязка панели масла к Point B (серебро) — 1920×1080
# Серебро и масло на одном горизонтальном уровне.
# Одно смещение до начала первой секции (718, 78), дальше — фиксированный шаг.
# Point B = (1149, 88) → якорь масла: dx = 718-1149 = -431, dy = 78-88 = -10
_OIL_DX_ANCHOR  = -431    # смещение по X от Point B до начала зелёной секции
_OIL_DY         = -10     # смещение по Y от Point B (масло чуть выше)
_OIL_SECTION_W  =  96     # ширина одной секции (иконка + число)
_OIL_ICON_W     =  41     # смещение от начала секции до числа (иконка до x=759)
_OIL_NUM_W      =  76     # ширина числа
_OIL_H          =  23     # высота строки
OIL_MIN_AMOUNT  = 70_000  # стоп если нужного масла < 70k

# Индексы секций: 0=зелёное(обычное), 1=синее(эпическое), 2=фиолетовое(редкое)
_OIL_IDX = {"ordinary": 0, "epic": 1, "rare": 2}

# Маппинг GUI-имени склепа → тип масла
def _crypt_oil_type(gui_name: str) -> str:
    if gui_name.startswith("Ordinary"):
        return "ordinary"   # зелёное
    elif gui_name.startswith("Epic"):
        return "epic"       # синее
    return "rare"           # фиолетовое (R_1, R_2)


def parse_oil_value(text: str) -> int:
    """Парсит '5.84M', '758K', '8900', ',5.84M', '55.76M' → целое число.
    Артефакт иконки даёт лишнюю цифру перед числом (55.76M вместо 5.76M) — обрезаем."""
    import re as _re
    t = text.strip()
    # Убираем артефакт: одна лишняя цифра перед "X.XXM" → "55.76M" → "5.76M"
    t = _re.sub(r'^\d(\d[.,]\d)', r'\1', t)
    # Убираем прочие нечисловые символы в начале (запятая, пробел)
    m = _re.search(r"(\d+[.,]\d+|\d+)\s*([MmKk]?)", t)
    if not m:
        return 0
    num_str = m.group(1).replace(",", ".")
    suffix = m.group(2).upper()
    val = float(num_str)
    if suffix == "M":
        return int(val * 1_000_000)
    if suffix == "K":
        return int(val * 1_000)
    return int(val)


# ══════════════════════════════════════════════════════════════
#  ЧИСТЫЕ ФУНКЦИИ (легко тестировать)
# ══════════════════════════════════════════════════════════════




# ══════════════════════════════════════════════════════════════
#  Путь к модели
# ══════════════════════════════════════════════════════════════
_SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
_MODEL_ENC     = os.path.join(_SCRIPT_DIR, 'targets', 'crypts.pte')
_MODEL_PLAIN   = os.path.join(_SCRIPT_DIR, 'targets', 'crypts.pt')
MODEL_PATH     = _MODEL_ENC if os.path.exists(_MODEL_ENC) else _MODEL_PLAIN
_LOG_DIR       = os.path.join(_SCRIPT_DIR, 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  ЭКСПЕРИМЕНТАЛЬНЫЕ ФИЧИ — поставить False чтобы отключить
# ══════════════════════════════════════════════════════════════
_EXP_DIALOG_GATE  = True   # перед кликом «Исследовать» проверяет что диалог открыт
_EXP_OIL_BLUE_THR = 3000   # был 50; поднят чтобы не срабатывать на синие объекты карты

# Типы редких склепов — требуют «Открыть» перед «Исследовать»
RARE_CRYPT_TYPES = {'R_1', 'R_2'}

# ══════════════════════════════════════════════════════════════
#  Маппинг: crypt_0..crypt_30  →  имена GUI
#  Порядок совпадает с main.py: Ordinary_1-12, Epic_2-18, R_1-2
# ══════════════════════════════════════════════════════════════
_GUI_NAMES = (
    [f"Ordinary_{i}" for i in range(1, 13)] +   # crypt_0  .. crypt_11
    [f"Epic_{i}"     for i in range(2, 19)] +   # crypt_12 .. crypt_28
    ['R_1', 'R_2']                              # crypt_29, crypt_30
)
YOLO_TO_GUI: dict[str, str] = {f"crypt_{i}": name for i, name in enumerate(_GUI_NAMES)}
# Обратный маппинг — используется при отладке
GUI_TO_YOLO: dict[str, str] = {v: k for k, v in YOLO_TO_GUI.items()}

# ══════════════════════════════════════════════════════════════
#  Зона сканирования меню (x, y, w, h) — только список склепов
#  Не трогает игровое поле. Откалибровать если нужно.
# ══════════════════════════════════════════════════════════════
MENU_SCAN_REGION = (597, 242, 721, 575)  # (x, y, w, h) — ровно окно меню склепов

# Порог детекции «меню не сдвинулось» (среднее пиксельное отличие / 255)
MENU_DIFF_THRESHOLD = 0.03  # 3% — скролл меняет ≥30% пикселей; шум/анимация < 1%


def _images_differ(a: 'np.ndarray', b: 'np.ndarray', threshold: float = MENU_DIFF_THRESHOLD) -> bool:
    """
    Возвращает True если изображения достаточно разные (меню сдвинулось).
    Возвращает False если они почти одинаковые (меню не двигалось = конец списка).
    """
    if a.shape != b.shape:
        return True
    import numpy as _np
    diff = _np.abs(a.astype(_np.int32) - b.astype(_np.int32))
    return float(diff.mean()) / 255.0 > threshold


# ══════════════════════════════════════════════════════════════
#  CryptHunter
# ══════════════════════════════════════════════════════════════

class CryptHunter:
    """Автосбор склепов через меню Дозорной башни."""

    def __init__(self):
        if MODEL_PATH.endswith('.pte'):
            from model_crypto import yolo_from_encrypted
            self._model = yolo_from_encrypted(MODEL_PATH)
        else:
            self._model = YOLO(MODEL_PATH)
        self.lang = "RU"
        self.is_running = False
        self._thread: threading.Thread | None = None
        self.on_found_callback  = None   # fn(crypt_type: str)
        self.on_status_callback = None   # fn(message: str)
        self.on_stop_callback   = None   # fn(reason: str)
        self.on_oil_callback    = None   # fn(ordinary: int, epic: int, rare: int)
        self.oil_check_enabled  = True   # если False — оба механизма масла отключены

        self._log_file: str | None = None

        # Параметры — устанавливаются через start()
        self._selected:       list[str] = []
        self._conf:           float     = 0.7
        self._accelerations:  int       = 3
        self._break_sec:      int       = 10
        self._scroll_speed:   float     = 0.5
        self._max_march_sec:  float     = 900.0

        # Регион, исключённый из YOLO-поиска (координаты окна бота при always-on-top)
        self._exclusion_region: tuple | None = None

    def start(
        self,
        selected_crypts:    list[str],
        conf:               float = 0.7,
        accelerations:      int   = 3,
        break_sec:          int   = 10,
        scroll_speed:       float = 0.5,
        max_march_min:      float = 15.0,
        on_found_callback         = None,
        on_status_callback        = None,
        on_stop_callback          = None,
        on_countdown_callback     = None,
        on_oil_callback           = None,
    ):
        """Запустить охоту в отдельном потоке."""
        self._selected       = selected_crypts
        self._conf           = conf
        self._accelerations  = accelerations
        self._break_sec      = max(3, int(break_sec))
        self._scroll_speed   = max(0.0, float(scroll_speed))
        self._max_march_sec  = max(300.0, float(max_march_min) * 60.0)
        self.on_found_callback      = on_found_callback
        self.on_status_callback     = on_status_callback
        self.on_stop_callback       = on_stop_callback
        self.on_countdown_callback  = on_countdown_callback
        self.on_oil_callback        = on_oil_callback

        _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = os.path.join(_LOG_DIR, f"crypt_{_ts}.log")
        self._log("INFO", f"=== CryptHunter start | selected={selected_crypts} conf={conf} accel={accelerations} ===")

        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_exclusion_region(self, region: tuple | None) -> None:
        """
        Задать регион экрана, исключённый из YOLO-поиска на карте.
        Используется при режиме «поверх всех окон», чтобы бот не видел
        иконки склепов в собственном UI.
        region: (x, y, w, h) в пикселях экрана, или None — отключить.
        """
        self._exclusion_region = region

    def stop(self):
        """Остановить охоту."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _log(self, level: str, msg: str):
        if not self._log_file:
            return
        try:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{ts}] [{level}] {msg}\n")
        except Exception:
            pass

    def _save_debug_screenshot(self, img: 'np.ndarray', tag: str):
        ts = datetime.now().strftime("%H%M%S_%f")[:-3]
        fname = os.path.join(_LOG_DIR, f"{tag}_{ts}.png")
        try:
            cv2.imwrite(fname, img)
            self._log("DEBUG", f"screenshot → {fname}")
        except Exception as e:
            self._log("ERROR", f"screenshot save failed: {e}")

    def _oil_screen_region(self, section_idx: int) -> tuple:
        """
        Вычисляет экранный регион числа масла по индексу секции (0/1/2).
        Якорь = Point B (серебро) из текущего калибровочного профиля.
        Работает для Client / Browser 1 / Browser 2 автоматически.
        """
        if _VISUAL_NAV_AVAILABLE:
            bx, by = _cm._point_b
            sx = _cm.scale_x
            sy = abs(_cm.scale_y)
        else:
            bx, by = REF_B
            sx = sy = 1.0
        x = bx + int((_OIL_DX_ANCHOR + section_idx * _OIL_SECTION_W + _OIL_ICON_W) * sx)
        y = by + int(_OIL_DY * sy)
        pad = int(10 * sx)
        return (x - pad, y, int(_OIL_NUM_W * sx) + pad, int(_OIL_H * sy))

    def _ocr_oil_region(self, section_idx: int) -> int:
        """OCR одного числа масла по индексу секции (0=обычное,1=эпическое,2=редкое)."""
        region = self._oil_screen_region(section_idx)
        img = self._screenshot(region)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        w, h = region[2], region[3]
        blur = cv2.GaussianBlur(gray, (0, 0), 3)
        sharp = cv2.addWeighted(gray, 2.0, blur, -1.0, 0)
        big = cv2.resize(sharp, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4)
        _, thresh = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789.,MmKk')
        return parse_oil_value(text)

    def _read_oil_panel(self) -> dict:
        """
        OCR трёх регионов масла (иконки вырезаны).
        Возвращает {'ordinary': int, 'epic': int, 'rare': int}.
        """
        ordinary = self._ocr_oil_region(0)
        epic     = self._ocr_oil_region(2)
        rare     = self._ocr_oil_region(1)
        self._log("INFO", f"oil panel: ordinary={ordinary:,} epic={epic:,} rare={rare:,}")
        if self.on_oil_callback:
            try:
                self.on_oil_callback(ordinary, epic, rare)
            except Exception:
                pass
        return {"ordinary": ordinary, "epic": epic, "rare": rare}

    def _check_oil_level(self, crypt_type: str) -> bool:
        """
        Читает панель масла и проверяет нужный тип для данного склепа.
        Возвращает True если масла достаточно, False если < OIL_MIN_AMOUNT.
        """
        oil_type = _crypt_oil_type(crypt_type)
        levels   = self._read_oil_panel()
        amount   = levels.get(oil_type, 0)
        self._status(f"Масло [{oil_type}]: {amount:,} (мин {OIL_MIN_AMOUNT:,})")
        if amount < OIL_MIN_AMOUNT:
            self._emergency_stop(f"OIL_LOW: {oil_type}={amount:,} < {OIL_MIN_AMOUNT:,}")
            return False
        return True

    def _status(self, msg: str):
        self._log("INFO", msg)
        if self.on_status_callback:
            self.on_status_callback(msg)

    def _emergency_stop(self, reason: str):
        self.is_running = False
        self._log("STOP", f"EMERGENCY STOP: {reason}")
        try:
            self._save_debug_screenshot(self._screenshot(), "emergency_stop")
        except Exception:
            pass
        self._status(f"СТОП: {reason}")
        if self.on_stop_callback:
            self.on_stop_callback(reason)

    def _run(self):
        """Основной цикл — крутится пока is_running."""
        while self.is_running:
            try:
                self._run_cycle()
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                if self.lang == "EN":
                    self._status(f"Cycle error: {e} — retry in 10s")
                else:
                    self._status(f"Ошибка цикла: {e} — повтор через 10 сек")
                try:
                    from auth import log_error_to_server
                    log_error_to_server(err)
                except Exception:
                    pass
                # Не останавливаемся — ждём и пробуем снова
                for _ in range(100):   # 10 сек с проверкой is_running каждые 0.1 сек
                    if not self.is_running:
                        break
                    time.sleep(0.1)

    # ─── Базовые helpers ──────────────────────────────────────

    def _click(self, x: int, y: int, jitter: int = 6, raw: bool = False):
        """
        Человеческий клик: плавное движение мыши → нажатие с задержкой.
        jitter — разброс попадания в пикселях (для маленьких кнопок: 2).
        raw=True — координаты уже экранные (YOLO/template), не масштабировать.
        """
        if not raw and _VISUAL_NAV_AVAILABLE:
            x, y = scale_coord(x, y)
        if jitter > 0:
            x += random.randint(-jitter, jitter)
            y += random.randint(-jitter, jitter)
        # Плавное движение мыши (неспешный взрослый: 0.25–0.55 сек)
        move_duration = random.uniform(0.25, 0.55)
        pyautogui.moveTo(x, y, duration=move_duration)
        # Небольшая пауза перед нажатием (человек прицеливается)
        time.sleep(random.uniform(0.05, 0.15))
        # Нажать и отпустить с реалистичной длительностью
        pyautogui.mouseDown()
        time.sleep(random.uniform(0.07, 0.14))
        pyautogui.mouseUp()

    def _random_pause(self, lo: float = 0.6, hi: float = 1.2):
        """Случайная пауза между действиями (неспешный взрослый)."""
        self._interruptible_sleep(random.uniform(lo, hi))

    def _interruptible_sleep(self, seconds: float):
        """Sleep, который прерывается мгновенно при ESC (is_running=False)."""
        deadline = time.monotonic() + seconds
        while self.is_running and time.monotonic() < deadline:
            time.sleep(0.05)


    def _screenshot(self, region: tuple | None = None) -> np.ndarray:
        """
        Скриншот экрана. region = (x, y, w, h) или None = весь экран.
        Если задан exclusion_region (окно бота поверх всех) — закрашивает
        область окна чёрным, чтобы template matching не видел UI бота.
        Возвращает BGR numpy array.
        """
        with mss.mss() as sct:
            if region:
                x, y, w, h = region
                monitor = {"left": x, "top": y, "width": w, "height": h}
            else:
                monitor = sct.monitors[1]
            raw = sct.grab(monitor)
        img = np.array(raw)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Маскируем область окна бота (always-on-top режим).
        # Только для полноэкранных скриншотов — региональные OCR-скрины
        # не пересекаются с окном бота при правильном позиционировании (x=0).
        if self._exclusion_region and region is None:
            ex, ey, ew, eh = self._exclusion_region
            ih, iw = img.shape[:2]
            x1, y1 = max(0, ex), max(0, ey)
            x2, y2 = min(iw, ex + ew), min(ih, ey + eh)
            if x2 > x1 and y2 > y1:
                img[y1:y2, x1:x2] = 0  # чёрная маска — YOLO и template не видят бота

        return img

    def _ocr_region(self, region: tuple) -> str:
        """
        OCR заданной области экрана. region = (x, y, w, h).
        Возвращает распознанный текст.
        """
        img = self._screenshot(region)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return pytesseract.image_to_string(thresh, config='--psm 7')

    # ─── Меню Дозорной башни ─────────────────────────────────

    def _open_watchtower(self):
        """Открыть меню Дозорной башни."""
        self._status("Открываю Дозорную башню...")
        pos = None
        if _TEMPLATE_AVAILABLE:
            # Ищем pipe.png в фиксированном регионе экрана (не через scale_coord —
            # он зависит от позиции окна Chrome которая может быть любой).
            # Регион: широкая полоса вокруг известного положения иконки.
            search_region = (
                WT_ICON[0] - 200, WT_ICON[1] - 150,
                400, 300,
            )
            pos = find_in_screen_region('pipe.png', search_region, threshold=0.60)
            if pos:
                self._status(f"  [template] pipe.png → {pos}")
            else:
                self._status("  [template] pipe.png не найден — использую координаты")
        if pos is not None:
            self._click(*pos, jitter=5, raw=True)
        else:
            self._click(*WT_ICON, jitter=5)
        self._random_pause()

    def _select_crypts_tab(self):
        """Кликнуть «Склепы и арены» в боковом меню башни."""
        self._status("Выбираю вкладку «Склепы и арены»...")
        pos = None
        if _TEMPLATE_AVAILABLE:
            search_region = (
                WT_CRYPTS_TAB[0] - 200, WT_CRYPTS_TAB[1] - 150,
                400, 300,
            )
            pos = find_in_screen_region('tab_crypts.png', search_region, threshold=0.60)
            if pos:
                self._status(f"  [template] tab_crypts.png → {pos}")
            else:
                self._status("  [template] tab_crypts.png не найден — использую координаты")
        if pos is not None:
            self._click(*pos, jitter=5, raw=True)
        else:
            self._click(*WT_CRYPTS_TAB, jitter=5)
        self._random_pause()

    def _reset_search(self):
        """
        Сбросить поиск склепов на начало.
        Два клика по «Арена» с паузой 1 сек между ними.
        """
        self._status("Конец списка — кликаю Арену для сброса...")
        self._click(*WT_ARENA_TAB, jitter=3)
        self._interruptible_sleep(random.uniform(0.9, 1.1))
        self._click(*WT_ARENA_TAB, jitter=3)
        self._random_pause(0.5, 0.8)

    # ─── YOLO режим 1: поиск в меню ──────────────────────────

    def _scroll_and_find(
        self,
        selected: list[str],
        max_scrolls: int = 0,
    ) -> str | None:
        """
        Скроллит список склепов в меню и ищет YOLO-детекцию нужного типа.
        Сканирует только MENU_SCAN_REGION — не смотрит на игровое поле.
        Возвращает GUI-имя найденного типа или None если дошли до конца.
        """
        self._status("Ищу склеп в меню...")
        # Переводим мышь в зону списка — туда куда будет идти скролл
        pyautogui.moveTo(WT_SCROLL_AREA[0], WT_SCROLL_AREA[1],
                         duration=random.uniform(0.3, 0.5))
        self._random_pause(0.3, 0.5)

        # Зона меню в экранных координатах (для фильтрации YOLO).
        ms_x, ms_y, ms_w, ms_h = MENU_SCAN_REGION

        # Зона поиска кнопки «Перейти» — правый столбец меню
        goto_col_ref_x = 1080
        goto_col_ref_w = 270

        prev_menu_snap:  'np.ndarray | None' = None
        no_move_count = 0   # сколько раз подряд меню не сдвинулось
        scroll_idx = 0

        while self.is_running:

            # Ждём после скролла: scroll_speed сек + 0.2 сек минимальный буфер для нейронки.
            # _interruptible_sleep гарантирует мгновенный выход при остановке бота.
            self._interruptible_sleep(self._scroll_speed + 0.2)

            img = self._screenshot()

            # Детект конца списка по неподвижности меню.
            # Вырезаем только зону меню для сравнения (не весь экран).
            menu_snap = img[ms_y:ms_y + ms_h, ms_x:ms_x + ms_w].copy()
            if prev_menu_snap is not None:
                if not _images_differ(prev_menu_snap, menu_snap):
                    no_move_count += 1
                    if no_move_count >= 3:
                        self._status(
                            f"Конец списка: меню не двигается "
                            f"({scroll_idx} скроллов)"
                        )
                        return None
                else:
                    no_move_count = 0
            prev_menu_snap = menu_snap

            scroll_idx += 1
            self._status(f"Ищу склеп... скролл {scroll_idx}")
            results = self._model(img, conf=self._conf, verbose=False)

            for r in results:
                if not r.boxes:
                    continue
                for box in r.boxes:
                    coords = box.xyxy.tolist()[0]
                    cx     = int((coords[0] + coords[2]) / 2)
                    cy     = int((coords[1] + coords[3]) / 2)

                    # Фильтр: иконка должна быть внутри окна меню
                    if not (ms_x <= cx <= ms_x + ms_w and ms_y <= cy <= ms_y + ms_h):
                        continue

                    # Фильтр: не засчитывать детекции внутри окна самого бота
                    if self._exclusion_region:
                        ex, ey, ew, eh = self._exclusion_region
                        if ex <= cx <= ex + ew and ey <= cy <= ey + eh:
                            continue

                    yolo_name = r.names[int(box.cls.tolist()[0])]
                    gui_name  = YOLO_TO_GUI.get(yolo_name, yolo_name)
                    if gui_name not in selected:
                        continue

                    # ── Доскролл если склеп у нижнего края меню ─────────────
                    # YOLO может найти склеп когда он виден лишь наполовину снизу.
                    # Скроллим ещё -2 (вниз) — контент сдвинется вверх и нижний
                    # склеп откроется целиком, кнопка «Перейти» будет полностью видна.
                    nudge_threshold = ms_y + int(ms_h * 0.72)  # нижние 28% меню
                    if cy > nudge_threshold:
                        self._status(f"  Доскролл: склеп у края (cy={cy})...")
                        pyautogui.scroll(-2)
                        self._interruptible_sleep(0.35)
                        if not self.is_running:
                            return None
                        # Перефотографируем и уточняем cy после подмотки
                        img = self._screenshot()
                        re_results = self._model(img, conf=self._conf, verbose=False)
                        for rr in re_results:
                            if not rr.boxes:
                                continue
                            for rbox in rr.boxes:
                                rc = rbox.xyxy.tolist()[0]
                                rcx = int((rc[0] + rc[2]) / 2)
                                rcy = int((rc[1] + rc[3]) / 2)
                                if not (ms_x <= rcx <= ms_x + ms_w
                                        and ms_y <= rcy <= ms_y + ms_h):
                                    continue
                                rname = rr.names[int(rbox.cls.tolist()[0])]
                                if YOLO_TO_GUI.get(rname, rname) == gui_name:
                                    cy = rcy  # обновлённая позиция после подмотки
                                    break
                            else:
                                continue
                            break

                    # Ищем кнопку «Перейти» рядом с иконкой.
                    # Если template не нашёл — всё равно кликаем по позиции (cy+17).
                    goto_pos = None
                    if _TEMPLATE_AVAILABLE:
                        btn_region = (goto_col_ref_x, cy - 35, goto_col_ref_w, 70)
                        goto_pos = find_in_screen_region('transition.png', btn_region,
                                                         threshold=0.70)
                        if goto_pos is None:
                            self._status(f"  transition.png не найден — клик по позиции")
                    if goto_pos is None:
                        sc_x = scale_coord(WT_GOTO_BTN_X, 0)[0] if _VISUAL_NAV_AVAILABLE else WT_GOTO_BTN_X
                        goto_pos = (sc_x, cy + 17)

                    self._status(f"Найден: {gui_name} — кнопка «Перейти» → {goto_pos}")
                    self._click(*goto_pos, jitter=2, raw=True)
                    self._random_pause(0.8, 1.5)
                    return gui_name

            pyautogui.scroll(-3); time.sleep(0.05); pyautogui.scroll(-3); time.sleep(0.05); pyautogui.scroll(-3)
            if max_scrolls > 0 and scroll_idx >= max_scrolls:
                return None

        return None

    # ─── YOLO режим 2: детект на карте ───────────────────────

    def _detect_on_map(self, crypt_type: str, attempts: int = 8) -> bool:
        """
        YOLO ищет на карте склеп того же типа что нашли в меню.
        Берёт бокс ближайший к центру экрана (игра телепортирует туда).
        """
        import mss as _mss
        screen_cx, screen_cy = 960, 540  # центр 1920×1080
        yolo_target = GUI_TO_YOLO.get(crypt_type)  # например "crypt_7"

        self._status(f"Ищу {crypt_type} на карте...")
        for _ in range(attempts):
            if not self.is_running:
                return False

            img = self._screenshot()
            results = self._model(img, conf=self._conf, verbose=False)

            best_box = None
            best_dist = float('inf')

            for r in results:
                if not r.boxes:
                    continue
                for box in r.boxes:
                    yolo_name = r.names[int(box.cls.tolist()[0])]
                    # Только нужный тип
                    if yolo_name != yolo_target:
                        continue
                    coords = box.xyxy.tolist()[0]
                    cx = int((coords[0] + coords[2]) / 2)
                    cy = int((coords[1] + coords[3]) / 2)
                    dist = ((cx - screen_cx) ** 2 + (cy - screen_cy) ** 2) ** 0.5
                    # Исключаем детекции внутри окна бота (always-on-top)
                    if self._exclusion_region:
                        ex, ey, ew, eh = self._exclusion_region
                        if ex <= cx <= ex + ew and ey <= cy <= ey + eh:
                            continue

                    if dist < best_dist:
                        best_dist = dist
                        best_box = (cx, cy)

            if best_box:
                self._status(f"{crypt_type} найден на карте — кликаю")
                self._click(best_box[0], best_box[1], jitter=4, raw=True)
                self._random_pause(0.8, 1.2)
                return True

            self._random_pause(1.0, 1.5)
        return False


    def _find_dialog_button(self, ref: tuple, pick: str) -> tuple | None:
        """
        Уточняет позицию кнопки через template в узком регионе вокруг ref.
        Если template не нашёл — возвращает None, caller кликнет по ref напрямую.

        HSV намеренно НЕ используется: при двух зелёных кнопках рядом
        ('Открыть' + 'Исследовать') HSV находит обе и промахивается.

        ref:  (x, y) откалиброванные координаты кнопки
        pick: не используется (оставлен для совместимости)
        """
        if _TEMPLATE_AVAILABLE:
            sc = scale_dialog(*ref) if _VISUAL_NAV_AVAILABLE else ref
            tight = (sc[0] - 100, sc[1] - 35, 200, 70)
            pos = find_in_screen_region('btn_issledovat.png', tight, threshold=0.65)
            if pos:
                self._status(f"  [tmpl] кнопка уточнена → {pos}")
                return pos

        return None  # caller кликнет по ref напрямую — координата откалибрована

    def _send_captain(self, crypt_type: str) -> bool:
        """Нажать «Исследовать». Возвращает False если появился диалог масла."""
        self._random_pause()

        # Проверяем масло ДО клика — читаем прямо с панели HUD
        if self.oil_check_enabled and not self._check_oil_level(crypt_type):
            return False

        if _EXP_DIALOG_GATE and _TEMPLATE_AVAILABLE:
            # [EXP] Шаг 1: убеждаемся что диалог открыт перед кликом
            sc_btn = scale_dialog(*CRYPT_STUDY_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_STUDY_BTN
            gate_region = (sc_btn[0] - 150, sc_btn[1] - 60, 300, 120)
            found = find_in_screen_region('btn_issledovat.png', gate_region, threshold=0.60)
            if found:
                self._log("INFO", f"[EXP] btn_issledovat найден → {found} (кликаем по эталону)")
                self._status("Диалог открыт — нажимаю «Исследовать»...")
                sc = scale_dialog(*CRYPT_STUDY_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_STUDY_BTN
                self._click(*sc, raw=True)
            else:
                self._log("WARN", "[EXP] btn_issledovat НЕ найден — диалог не открыт, рестарт цикла")
                self._status("[EXP] Диалог склепа не обнаружен — рестарт")
                return False

            self._interruptible_sleep(1.5)
        else:
            self._status("Нажимаю «Исследовать»...")
            sc = scale_dialog(*CRYPT_STUDY_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_STUDY_BTN
            self._click(*sc, raw=True)
            self._interruptible_sleep(1.5)
            if self.oil_check_enabled and self._check_oil_dialog():
                self._emergency_stop("OIL_LOW: масло закончилось")
                return False

        self._random_pause(0.3, 0.8)
        return True

    # ─── Ускорение марша ──────────────────────────────────────

    def _click_captain_event(self) -> bool:
        """
        Кликнуть по полосе события Картера вверху экрана (кнопка «Ускорить»).
        Возвращает True если диалог ускорения открылся, False — рестарт цикла.
        """
        self._status("Кликаю по полосе Картера...")
        self._random_pause(1.5, 2.0)
        pos = None
        if _TEMPLATE_AVAILABLE:
            pos = find_at_ref('btn_uskorit.png',
                              ref_cx=CARTER_EVENT_BAR[0], ref_cy=CARTER_EVENT_BAR[1],
                              rw=400, rh=80)
            if pos:
                self._status(f"  [tmpl] Ускорить → {pos}")
        if pos is None:
            pos = self._find_button(
                ref_region=(900, 85, 500, 60),
                color='purple', pick='largest',
                fallback=CARTER_EVENT_BAR,
            )
        cx = pos[0] + random.randint(-6, 6)  # jitter только по X (полоса узкая)
        self._click(cx, pos[1], jitter=0, raw=True)
        self._interruptible_sleep(1.1)
        return True

    def _accelerate(self, applied: int) -> None:
        """Нажимает «Использовать» applied раз."""
        if applied == 0:
            return
        sc_use = scale_dialog(*ACCEL_USE_BTN) if _VISUAL_NAV_AVAILABLE else ACCEL_USE_BTN
        for i in range(applied):
            if not self.is_running:
                return
            self._status(f"Ускорение {i + 1}/{applied}")
            self._click(*sc_use, raw=True)
            self._random_pause(0.8, 1.2)

    def _verify_action(self, name: str, verify_fn, timeout: float = 3.0) -> bool:
        """
        Опрашивает verify_fn() каждые 0.5с до timeout секунд.
        Возвращает True если подтверждено, False если timeout или is_running=False.
        """
        if not self.is_running:
            return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_running:
                return False
            if verify_fn():
                self._status(f"  ✓ {name} — подтверждено")
                return True
            self._interruptible_sleep(0.5)
        self._status(f"  ✗ {name} — не подтверждено за {timeout:.0f}с → рестарт")
        return False

    def _close_dialog(self):
        """Окно закрывается автоматически когда Картер добирается до склепа — ничего не делаем."""
        pass

    def _find_button(
        self,
        ref_region: tuple,
        color: str,
        pick: str,
        fallback: tuple,
    ) -> tuple[int, int]:
        """
        Try to find button by color in ref_region (1920×1080 coords).
        Falls back to scale_coord(*fallback) if not found or visual nav unavailable.

        ref_region: (x, y, w, h) in 1920×1080 reference coordinates
        color:      'green' or 'purple'
        pick:       'rightmost' | 'leftmost' | 'topmost' | 'largest'
        fallback:   (x, y) hardcoded reference coordinates
        """
        if _VISUAL_NAV_AVAILABLE:
            region = scale_region(*ref_region)
            pos = find_colored_button(region, color, pick)
            if pos:
                self._status(f"  [visual] {color}/{pick} → {pos}")
                return pos
            self._status(f"  [visual] не найдено — использую fallback")
        if _VISUAL_NAV_AVAILABLE:
            return scale_coord(*fallback)
        return fallback

    def _detect_oil_buttons(self, img_bgr: 'np.ndarray') -> bool:
        """
        Ищет зелёные (использовать) или синие (купить) кнопки в BGR-изображении.
        Возвращает True если найдено ≥ 100 таких пикселей → масляный диалог.
        HSV scale: H 0-180, S 0-255, V 0-255 (OpenCV convention).
        """
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        # Зелёная кнопка «Использовать» (масло на складе)
        green_mask = cv2.inRange(
            hsv,
            np.array([35,  80,  80]),
            np.array([85, 255, 220]),
        )
        # Синяя кнопка «Купить» (покупка масла)
        blue_mask = cv2.inRange(
            hsv,
            np.array([100,  80,  80]),
            np.array([130, 255, 230]),
        )
        green_px = int(green_mask.sum() // 255)
        blue_px  = int(blue_mask.sum() // 255)
        # Требуем ОБЕ кнопки: Carter overlay имеет только зелёную
        result = green_px >= 500 and blue_px >= _EXP_OIL_BLUE_THR
        self._log("DEBUG", f"oil_buttons: green={green_px} (thr≥500) blue={blue_px} (thr≥{_EXP_OIL_BLUE_THR}) → {result}")
        return result

    def _check_oil_dialog(self) -> bool:
        """
        Делает скриншот центра экрана и проверяет наличие кнопок диалога масла.
        Вызывается из _send_captain() через 1.5с после клика «Исследовать».
        Не зависит от языка игры — ищет цвет кнопок, не текст.
        """
        img = self._screenshot(OIL_DIALOG_REGION)
        detected = self._detect_oil_buttons(img)
        if detected:
            self._save_debug_screenshot(img, "oil_region")
            self._save_debug_screenshot(self._screenshot(), "oil_fullscreen")
            self._log("WARN", f"oil dialog DETECTED at OIL_DIALOG_REGION={OIL_DIALOG_REGION}")
        return detected

    # ─── Полный цикл ─────────────────────────────────────────

    def _run_cycle(self):
        """Один полный цикл: открыть башню → найти → отправить → ждать."""
        # [1] Открываем башню (вкладку «Склепы и арены» пользователь открывает вручную)
        self._open_watchtower()

        # [3-4] Ищем нужный склеп (с ресетами если нужно)
        crypt_type = None
        while crypt_type is None and self.is_running:
            crypt_type = self._scroll_and_find(self._selected)
            if crypt_type is None and self.is_running:
                wait = 30.0
                self._status(f"Конец списка — жду {wait:.0f} сек...")
                self._interruptible_sleep(wait)
                self._reset_search()

        if not self.is_running:
            return

        # [5] Игра телепортирует на карту. Ждём загрузки.
        self._interruptible_sleep(2.0)

        # [6] YOLO на карте — ищем тот же тип, ближайший к центру
        if not self._detect_on_map(crypt_type):
            self._status("Склеп не найден на карте — начинаю сначала")
            return  # РЕСТАРТ

        # [6.5] Для R-типов: открываем склеп (пустой диалог, только кнопка «Открыть»)
        # После клика появляется обычный диалог с маслом и временем марша
        if crypt_type in RARE_CRYPT_TYPES:
            self._status("Редкий склеп — нажимаю «Открыть»")
            sc_open = scale_dialog(*CRYPT_OPEN_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_OPEN_BTN
            self._click(*sc_open, raw=True)
            time.sleep(0.4)
            pyautogui.moveTo(sc_open[0], sc_open[1] - random.randint(450, 550))

        # [7] Отправляем Капитана
        if not self._send_captain(crypt_type):
            self._status("Капитан не отправлен — перезапуск цикла")
            return

        if not self.is_running:
            return

        # [10] Ускорение N раз (из ползунка), если N > 0
        n = self._accelerations
        if n > 0:
            if not self._click_captain_event():
                self._status("Диалог ускорения не открылся — перезапуск цикла")
                return
            self._accelerate(n)

        # [11] Ждать Картера: T_one_way = T_max / 2^N, ждём туда+обратно
        t_one_way = self._max_march_sec / (2 ** n) if n > 0 else self._max_march_sec
        _buf = int(self._break_sec * random.uniform(0.8, 1.2))
        wait_time = t_one_way * 2
        total_wait = int(wait_time) + _buf
        _march_one_way = int(t_one_way)
        if self.lang == "EN":
            self._status(f"Waiting Carter: {_march_one_way}s there + {_march_one_way}s back + {_buf}s pause")
        else:
            self._status(f"Ждём Картера: {_march_one_way}с туда + {_march_one_way}с обратно + {_buf}с пауза")
        for remaining in range(total_wait, 0, -1):
            if not self.is_running:
                break
            try:
                if self.on_countdown_callback:
                    self.on_countdown_callback(remaining, total_wait, _march_one_way, _buf)
            except Exception:
                pass
            self._interruptible_sleep(1.0)
        # Сбросить countdown
        try:
            if self.on_countdown_callback:
                self.on_countdown_callback(0, total_wait, _march_one_way, _buf)
        except Exception:
            pass

        if not self.is_running:
            return

        # Картер вернулся — сообщаем GUI и списываем кредит
        # Оборачиваем в try чтобы ошибка callback не убила цикл
        try:
            if self.on_found_callback:
                self.on_found_callback(crypt_type)
        except Exception:
            pass

        # Короткая пауза перед следующим циклом
        self._random_pause(1.5, 3.0)
