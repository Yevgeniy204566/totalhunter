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
    from tesseract_setup import configure_pytesseract
    configure_pytesseract(pytesseract)
    from ultralytics import YOLO
    _GAME_DEPS_AVAILABLE = True
except ImportError:
    _GAME_DEPS_AVAILABLE = False

# Координатная система (2-точечная калибровка). Цветовое распознавание
# для кликов по игровым кнопкам не используется — только координаты
# (см. ANTI-PATTERNS.md). Исключение — YOLO для поиска склепов в списке/на
# карте, она живёт отдельно в _scroll_and_find/_detect_on_map.
try:
    from coord_manager import coord_manager as _cm
    scale_coord        = _cm.to_screen
    scale_region       = _cm.to_region
    scale_dialog       = _cm.to_screen_dialog
    scale_dialog_region = _cm.to_region_dialog
    _VISUAL_NAV_AVAILABLE = True
except ImportError:
    _VISUAL_NAV_AVAILABLE = False


def scale_ui_coord(ref_x: int, ref_y: int, ref_w: int = 1920, ref_h: int = 1080):
    """Пропорциональное масштабирование статичных UI-кнопок (не карта).
    Используется для WT_ICON, вкладок меню и т.п. — элементов которые
    не зависят от калибровки карты, а просто пропорциональны разрешению."""
    sw, sh = pyautogui.size()
    return int(ref_x * sw / ref_w), int(ref_y * sh / ref_h)




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

# ══════════════════════════════════════════════════════════════
#  Путь к модели
# ══════════════════════════════════════════════════════════════
_SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
_MODEL_ENC     = os.path.join(_SCRIPT_DIR, 'targets', 'crypts.pte')
_MODEL_PLAIN   = os.path.join(_SCRIPT_DIR, 'targets', 'crypts.pt')
MODEL_PATH     = _MODEL_ENC if os.path.exists(_MODEL_ENC) else _MODEL_PLAIN
_LOG_DIR       = os.path.join(_SCRIPT_DIR, 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)

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

# Сколько пустых вырезок MENU_SCAN_REGION подряд терпим прежде чем сдаться.
# Если регион постоянно (не разово) вне границ скриншота — сломанная калибровка/
# разрешение конкретного игрока, а не кадровый глюк — без лимита _scroll_and_find
# крутил бы скролл молча и бесконечно, никогда не находя конец списка.
EMPTY_MENU_CROP_STREAK_LIMIT = 5



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

        self._log_file: str | None = None

        # Параметры — устанавливаются через start()
        self._selected:       list[str] = []
        self._conf:           float     = 0.7
        self._accelerations:  int       = 3
        self._break_sec:      int       = 10
        self._scroll_speed:   float     = 0.5
        self._max_march_sec:  float     = 120.0
        self._swing1:         int       = 0
        self._swing2:         int       = 0
        self._speed_delta:    float     = 0.0

        # Периодический сброс списка склепов (Арена x2), независимо от конца
        # списка — см. _reset_search(). None = выключено.
        self._periodic_reset_sec:     float | None = None
        self._next_periodic_reset_at: float | None = None

        # Регион, исключённый из YOLO-поиска (координаты окна бота при always-on-top)
        self._exclusion_region: tuple | None = None

        # Счётчик провалов детекции на карте — для пропуска проблемного склепа
        self._detect_fail_streak: int = 0

    def start(
        self,
        selected_crypts:    list[str],
        conf:               float = 0.7,
        accelerations:      int   = 3,
        break_sec:          int   = 10,
        scroll_speed:       float = 0.5,
        max_march_sec:      float = 120.0,
        swing1:             int   = 0,
        swing2:             int   = 0,
        speed_delta:        float = 0.0,
        periodic_reset_sec: int | None = None,
        on_found_callback         = None,
        on_status_callback        = None,
        on_stop_callback          = None,
        on_countdown_callback     = None,
    ):
        """Запустить охоту в отдельном потоке."""
        self._selected       = selected_crypts
        self._conf           = conf
        self._accelerations  = accelerations
        self._break_sec      = max(3, int(break_sec))
        self._scroll_speed   = max(0.0, float(scroll_speed))
        # Пол/потолок должны совпадать со слайдером UI (10-600 сек) — см. ANTI-PATTERNS.md
        # про молчаливое зажимание значений вне диапазона слайдера.
        self._max_march_sec  = max(10.0, min(600.0, float(max_march_sec)))
        self._swing1         = int(swing1)
        self._swing2         = int(swing2)
        self._speed_delta    = float(speed_delta)
        self._periodic_reset_sec = int(periodic_reset_sec) if periodic_reset_sec else None
        self._next_periodic_reset_at = (
            time.monotonic() + self._periodic_reset_sec if self._periodic_reset_sec else None
        )
        self.on_found_callback      = on_found_callback
        self.on_status_callback     = on_status_callback
        self.on_stop_callback       = on_stop_callback
        self.on_countdown_callback  = on_countdown_callback

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
            except pyautogui.FailSafeException:
                # Not a code bug — PyAutoGUI's own safety net: the user's real cursor is
                # resting in a screen corner, so it refuses to move/click at all. Reporting
                # this to log_error_to_server would just add noise to the crash stats.
                self._status("Mouse safety stop: move your cursor away from the screen corner — retry in 10s")
                for _ in range(100):
                    if not self.is_running:
                        break
                    time.sleep(0.1)
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
        """Случайная пауза между действиями. speed_delta > 0 = быстрее, < 0 = медленнее."""
        lo_adj = max(0.1, lo - self._speed_delta)
        hi_adj = max(0.2, hi - self._speed_delta)
        self._interruptible_sleep(random.uniform(lo_adj, hi_adj))

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
        bx, by = scale_ui_coord(*WT_ICON)
        ox, oy = _cm.get_ui_offset("wt_icon") if _VISUAL_NAV_AVAILABLE else (0, 0)
        self._click(bx + ox, by + oy, jitter=5, raw=True)
        self._random_pause()

    def _select_crypts_tab(self):
        """Кликнуть «Склепы и арены» в боковом меню башни."""
        self._click(*scale_ui_coord(*WT_CRYPTS_TAB), jitter=5, raw=True)
        self._random_pause()

    def _reset_search(self):
        """
        Сбросить поиск склепов на начало.
        Два клика по «Арена» с паузой 1 сек между ними.
        """
        # self._status("Конец списка — кликаю Арену для сброса...")
        ox, oy = _cm.get_ui_offset("arena_reset") if _VISUAL_NAV_AVAILABLE else (0, 0)
        ax, ay = scale_ui_coord(*WT_ARENA_TAB)
        self._click(ax + ox, ay + oy, jitter=3, raw=True)
        self._interruptible_sleep(random.uniform(0.9, 1.1))
        self._click(ax + ox, ay + oy, jitter=3, raw=True)
        self._random_pause(0.5, 0.8)
        # Список уже в начале — независимо от причины сброса (конец списка,
        # pre_skip, периодика), откладываем следующий периодический сброс
        # на полный интервал вперёд, а не оставляем его "просроченным".
        if self._periodic_reset_sec:
            self._next_periodic_reset_at = time.monotonic() + self._periodic_reset_sec

    def _pre_skip(self):
        """Прокрутить список вниз на 3 тика — пропустить проблемный склеп (~5 позиций).

        Если непризнанный склеп — последний в списке, скролл здесь превращается
        в no-op (список уже упёрся в конец): _scroll_and_find() тут же находит
        тот же самый склеп заново и бот зацикливается на нём (см. лог
        crypt_20260908_092836.log). Проверяем это тем же способом, что и конец
        списка в _scroll_and_find — сравниваем кроп MENU_SCAN_REGION до/после
        скролла — и если список не сдвинулся, сразу сбрасываем поиск (Арена x2)
        вместо повторного выбора того же склепа.
        """
        self._status("Пропускаю склеп (3 скролла вниз)...")
        _sx, _sy = scale_ui_coord(*WT_SCROLL_AREA)
        pyautogui.moveTo(_sx, _sy, duration=random.uniform(0.3, 0.5))
        self._interruptible_sleep(0.3)

        ms_x, ms_y, ms_w, ms_h = scale_region(*MENU_SCAN_REGION) if _VISUAL_NAV_AVAILABLE else MENU_SCAN_REGION
        before_img = self._screenshot()
        before_crop = before_img[ms_y:ms_y + ms_h, ms_x:ms_x + ms_w]

        _sc = _cm.scroll_clicks if _VISUAL_NAV_AVAILABLE else 3
        for _ in range(3):
            pyautogui.scroll(-_sc); time.sleep(0.05)
            pyautogui.scroll(-_sc); time.sleep(0.05)
            pyautogui.scroll(-_sc)
            self._interruptible_sleep(0.25)

        after_img = self._screenshot()
        after_crop = after_img[ms_y:ms_y + ms_h, ms_x:ms_x + ms_w]
        if (before_crop.size > 0 and after_crop.size > 0
                and before_crop.shape == after_crop.shape
                and cv2.absdiff(before_crop, after_crop).mean() < 2.0):
            # Список не сдвинулся — мы уже были в конце. Тот же склеп иначе
            # будет выбран снова на следующем _scroll_and_find().
            self._reset_search()

        self._detect_fail_streak = 0

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
        Конец списка определяется визуально: если меню не сдвинулось после скролла.
        """
        # self._status("Ищу склеп в меню...")
        # Переводим мышь в зону списка — туда куда будет идти скролл
        _sx, _sy = scale_ui_coord(*WT_SCROLL_AREA)
        pyautogui.moveTo(_sx, _sy, duration=random.uniform(0.3, 0.5))
        self._random_pause(0.3, 0.5)

        # Зона меню в экранных координатах (для фильтрации YOLO).
        ms_x, ms_y, ms_w, ms_h = scale_region(*MENU_SCAN_REGION) if _VISUAL_NAV_AVAILABLE else MENU_SCAN_REGION

        scroll_idx = 0
        prev_menu_crop: 'np.ndarray | None' = None
        empty_crop_streak = 0

        while self.is_running:

            # Ждём после скролла: scroll_speed сек + 0.2 сек минимальный буфер для нейронки.
            # _interruptible_sleep гарантирует мгновенный выход при остановке бота.
            self._interruptible_sleep(self._scroll_speed + 0.2)

            img = self._screenshot()

            # Конец списка: если меню не изменилось после скролла — список встал
            curr_menu_crop = img[ms_y:ms_y + ms_h, ms_x:ms_x + ms_w]
            # Вырезка может оказаться пустой (MENU_SCAN_REGION вылез за границы
            # реального скриншота при нестандартном разрешении/масштабе калибровки) —
            # cv2.absdiff() на двух пустых массивах тихо возвращает None вместо ошибки,
            # и .mean() падает AttributeError. Не считаем это концом списка — но если
            # вырезка пустая постоянно (не разовый глюк кадра), а не разово, сдаёмся
            # после EMPTY_MENU_CROP_STREAK_LIMIT попыток, а не крутим скролл вечно.
            if curr_menu_crop.size == 0:
                empty_crop_streak += 1
                if empty_crop_streak >= EMPTY_MENU_CROP_STREAK_LIMIT:
                    return None
            else:
                empty_crop_streak = 0
                if (prev_menu_crop is not None
                        and curr_menu_crop.shape == prev_menu_crop.shape):
                    diff = cv2.absdiff(curr_menu_crop, prev_menu_crop)
                    if diff.mean() < 2.0:
                        return None
            prev_menu_crop = curr_menu_crop.copy()

            scroll_idx += 1
            # self._status(f"Ищу склеп... скролл {scroll_idx}")
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
                        pass
                        # self._status(f"  Доскролл: склеп у края (cy={cy})...")
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

                    # +17 — вертикальный сдвиг от центра иконки склепа до кнопки
                    # «Перейти» в той же строке, измерен на 1920x1080. cy сам по
                    # себе уже в реальных экранных пикселях (взят с живого
                    # скриншота) — маштабировать нужно только сам сдвиг, иначе
                    # на 2K/4K клик всё сильнее промахивается мимо кнопки.
                    sc_x = scale_ui_coord(WT_GOTO_BTN_X, 0)[0]
                    _row_dy = scale_ui_coord(0, 17)[1]
                    ox, oy = _cm.get_ui_offset("crypt_select") if _VISUAL_NAV_AVAILABLE else (0, 0)
                    goto_pos = (sc_x + ox, cy + _row_dy + oy)

                    # self._status(f"Найден: {gui_name} — кнопка «Перейти» → {goto_pos}")
                    self._click(*goto_pos, jitter=2, raw=True)
                    self._random_pause(0.8, 1.5)
                    return gui_name

            _sc = _cm.scroll_clicks if _VISUAL_NAV_AVAILABLE else 3
            pyautogui.scroll(-_sc); time.sleep(0.05); pyautogui.scroll(-_sc); time.sleep(0.05); pyautogui.scroll(-_sc)
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
        import pyautogui as _pag
        _sw, _sh = _pag.size()
        screen_cx, screen_cy = _sw // 2, _sh // 2
        yolo_target = GUI_TO_YOLO.get(crypt_type)  # например "crypt_7"

        # self._status(f"Ищу {crypt_type} на карте...")
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
                pass
                # self._status(f"{crypt_type} найден на карте — кликаю")
                self._click(best_box[0], best_box[1], jitter=4, raw=True)
                self._random_pause(0.8, 1.2)
                return True

            self._random_pause(1.0, 1.5)
        return False



    def _open_rare_crypt(self) -> None:
        """R-типы: пустой диалог с одной кнопкой «Открыть» — нажать её.
        После клика появляется обычный диалог с маслом и временем марша."""
        sc_open = scale_dialog(*CRYPT_OPEN_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_OPEN_BTN
        ox, oy = _cm.get_ui_offset("crypt_open") if _VISUAL_NAV_AVAILABLE else (0, 0)
        self._click(sc_open[0] + ox, sc_open[1] + oy, jitter=2, raw=True)
        time.sleep(0.4)
        pyautogui.moveTo(sc_open[0], sc_open[1] - random.randint(450, 550))

    def _send_captain(self, crypt_type: str) -> bool:
        """Нажать «Исследовать»."""
        self._random_pause()

        sc = scale_dialog(*CRYPT_STUDY_BTN) if _VISUAL_NAV_AVAILABLE else CRYPT_STUDY_BTN
        ox, oy = _cm.get_ui_offset("carter") if _VISUAL_NAV_AVAILABLE else (0, 0)
        self._click(sc[0] + ox, sc[1] + oy, jitter=2, raw=True)
        self._interruptible_sleep(1.5)

        self._random_pause(0.3, 0.8)
        return True

    # ─── Ускорение марша ──────────────────────────────────────

    def _click_captain_event(self) -> bool:
        """
        Кликнуть по полосе события Картера вверху экрана (кнопка «Ускорить»).
        Возвращает True если диалог ускорения открылся, False — рестарт цикла.
        """
        # self._status("Кликаю по полосе Картера...")
        self._random_pause(1.5, 2.0)
        ox, oy = _cm.get_ui_offset("top_accel") if _VISUAL_NAV_AVAILABLE else (0, 0)
        bx, by = scale_ui_coord(*CARTER_EVENT_BAR)
        cx = bx + ox + random.randint(-6, 6)  # jitter только по X (полоса узкая)
        self._click(cx, by + oy, jitter=0, raw=True)
        self._interruptible_sleep(1.1)
        return True

    def _accelerate(self, applied: int) -> None:
        """Нажимает «Использовать» applied раз."""
        if applied == 0:
            return
        sc_use = scale_ui_coord(*ACCEL_USE_BTN)
        ox, oy = _cm.get_ui_offset("march_accel") if _VISUAL_NAV_AVAILABLE else (0, 0)
        use_x, use_y = sc_use[0] + ox, sc_use[1] + oy
        for i in range(applied):
            if not self.is_running:
                return
            self._click(use_x, use_y, jitter=2, raw=True)
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
                pass
                # self._status(f"  ✓ {name} — подтверждено")
                return True
            self._interruptible_sleep(0.5)
        # self._status(f"  ✗ {name} — не подтверждено за {timeout:.0f}с → рестарт")
        return False

    def _close_dialog(self):
        """Окно закрывается автоматически когда Картер добирается до склепа — ничего не делаем."""
        pass



    # ─── Полный цикл ─────────────────────────────────────────

    def _run_cycle(self):
        """Один полный цикл: открыть башню → найти → отправить → ждать."""
        # [1] Открываем башню (вкладку «Склепы и арены» пользователь открывает вручную)
        self._open_watchtower()

        # [1.5] Периодический сброс списка (Арена x2) — независимо от конца
        # списка. Срабатывает ДО поиска, чтобы каждый цикл начинался с уже
        # актуального (не уехавшего вниз) списка. Точность таймера не
        # критична — проверяется раз за цикл, поэтому реальный интервал
        # может быть чуть больше заданного.
        if self._next_periodic_reset_at is not None and time.monotonic() >= self._next_periodic_reset_at:
            self._status("Periodic reset (Arena ×2)...")
            self._reset_search()

        # Если предыдущий цикл провалил детекцию на карте — пропустить проблемный склеп
        if self._detect_fail_streak > 0:
            self._pre_skip()

        # [3-4] Ищем нужный склеп (с ресетами если нужно)
        crypt_type = None
        while crypt_type is None and self.is_running:
            crypt_type = self._scroll_and_find(self._selected)
            if crypt_type is None and self.is_running:
                wait = 30.0
                self._status(f"End of list — waiting {wait:.0f}s...")
                self._interruptible_sleep(wait)
                self._status("Resetting list (Arena ×2)...")
                self._reset_search()

        if not self.is_running:
            return

        # [5] Игра телепортирует на карту. Ждём загрузки.
        self._interruptible_sleep(2.0)

        # [6] YOLO на карте — ищем тот же тип, ближайший к центру
        if not self._detect_on_map(crypt_type):
            self._detect_fail_streak += 1
            # self._status("Склеп не найден на карте — начинаю сначала")
            return  # РЕСТАРТ

        # [6.5] Для R-типов: открываем склеп (пустой диалог, только кнопка «Открыть»)
        if crypt_type in RARE_CRYPT_TYPES:
            self._open_rare_crypt()

        # [7] Отправляем Капитана
        if not self._send_captain(crypt_type):
            pass
            # self._status("Капитан не отправлен — перезапуск цикла")
            return
        self._detect_fail_streak = 0   # склеп найден и отправлен — сбрасываем счётчик

        if not self.is_running:
            return

        # [10] Ускорение N раз (из ползунка), если N > 0
        n = self._accelerations
        if n > 0:
            pass
            if not self._click_captain_event():
                pass
                # self._status("Диалог ускорения не открылся — перезапуск цикла")
                return
            self._accelerate(n)

        # [11] Ждать Картера: T_one_way = T_max / 2^N, ждём туда+обратно
        t_one_way = self._max_march_sec / (2 ** n) if n > 0 else self._max_march_sec
        _buf = int(self._break_sec * random.uniform(0.8, 1.2))
        wait_time = t_one_way * 2
        total_wait = int(wait_time) + _buf
        _march_one_way = int(t_one_way)
        self._status(f"Carter: {_march_one_way}s + {_march_one_way}s + {_buf}s")
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
