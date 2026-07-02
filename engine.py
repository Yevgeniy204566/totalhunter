import os
import json
import time
import threading
import datetime as _dt
import winsound
import numpy as np
import pyautogui
from ultralytics import YOLO

from navigator import PacmanEngine
from auth import heartbeat as _heartbeat, get_hwid
from version import VERSION
import nav_logger
nav_logger.install()

_ROY_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roy_debug.log')

def _roy_log(msg: str):
    import datetime as _dtt
    line = f"{_dtt.datetime.now().strftime('%H:%M:%S.%f')[:-3]} [ROY] {msg}"
    print(line)
    try:
        with open(_ROY_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _is_trade_routes_active() -> bool:
    """Вычисляет активность ивента Торговые Пути напрямую, без зависимости от GUI-флага.
    Синхронизировано с сервером (server/roy.py) и GUI (main.py):
      _TR_ANCHOR_TS  = 1780333200  # 2026-06-01 17:00:00 UTC
      _TR_CYCLE_H    = 144         # 24ч ивент + 120ч пауза = 144ч полный цикл
      _TR_DURATION_H = 24          # длительность ивента
    Чтобы сдвинуть расписание — менять _TR_ANCHOR_TS здесь, в main.py и в server/roy.py.
    """
    _TR_ANCHOR_TS  = 1780333200   # 2026-06-01 17:00:00 UTC
    _TR_CYCLE_SEC  = 144 * 3600   # 144 часа = 24ч ивент + 120ч пауза
    _TR_DUR_SEC    = 24  * 3600   # 24 часа — длительность ивента

    now_ts = time.time()
    offset = (now_ts - _TR_ANCHOR_TS) % _TR_CYCLE_SEC
    active = offset < _TR_DUR_SEC

    secs_left = int(_TR_DUR_SEC - offset) if active else int(_TR_CYCLE_SEC - offset)
    h, m = secs_left // 3600, (secs_left % 3600) // 60
    status = f"ИДЁТ, осталось {h}ч {m:02d}мин" if active else f"пауза, до старта {h}ч {m:02d}мин"
    _roy_log(f"Ивент Торговые Пути: {status}")
    return active

# Убираем глобальную задержку PyAutoGUI — антидетект обеспечивается move_wait в навигаторе
pyautogui.PAUSE = 0.0


class HuntEngine:
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        enc_path = os.path.join(script_dir, 'exchange.pte')
        pt_path  = os.path.join(script_dir, 'exchange.pt')
        if os.path.exists(enc_path):
            from model_crypto import yolo_from_encrypted
            self.model = yolo_from_encrypted(enc_path)
            self.model_path = enc_path
        else:
            import torch
            self.model_path = pt_path
            self.model = YOLO(pt_path)
            try:
                _device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.model.to(_device)
            except Exception:
                self.model.to('cpu')
                _device = 'cpu'
            print(f"[TH v{VERSION}] YOLO device (pt): {_device}")

        import sys
        _base = getattr(sys, '_MEIPASS', script_dir)
        files_in_dir = os.listdir(_base)
        sound_file = next((f for f in files_in_dir if f.lower().endswith('.wav')), None)
        self.sound_path = os.path.join(_base, sound_file) if sound_file else None

        self.is_running = False
        self.on_found_callback = None
        self._pacman: PacmanEngine | None = None

        # Roy — отключён по умолчанию, включается из GUI
        self.roy_enabled   = False
        self.roy_kingdom   = 0     # ГОС для live-счётчика (0 = не задан)
        self._roy_client   = None
        self.on_last_exchange_callback = None  # (result: dict) → обновляет GUI владельца
        self.event_active  = False  # True только пока идёт ивент Торговые Пути
        self._mm_cx        = 90    # координаты центра миникарты (джойстик)
        self._mm_cy        = 925
        self._last_start_kwargs: dict = {}
        self.on_engine_restart_callback = None  # (state: 'stopped'|'starting') → обновляет GUI
        self.on_pool_refresh_callback   = None  # (pool: list) → обновляет список пула в GUI
        self._bg_gen: int = 0  # инкрементируется на каждом start() — старые треды видят изменение
        self.on_exchange_found_callback = None  # () → main.py.after(10000, _programmatic_restart)
        self._initial_yolo_block_sec: float = 0.0  # >0 → блокирует YOLO на N сек после start()
        self._bg_threads: list = []  # все фоновые треды — для явного join при stop()

    def start(
        self,
        conf: float,
        center_x: int        = 90,
        center_y: int        = 925,
        joystick_step: int   = 13,
        scan_interval: float = 0.6,
        move_wait: float     = 2.0,
        navigation_enabled: bool = True,
        max_inland_steps: int   = 5,
        ocean_land_ratio: float = 0.03,
        min_water_px: int       = 500,
        footprint_ttl: float    = 120.0,
        diagonal_blind_coeff: float = 0.5,
        coast_detect_radius: int = 50,
        return_delta_px: int   = 0,
        smooth_alpha:    float = 0.5,
        use_beacon:      bool  = False,
        pixels_per_step: int   = 20,
    ):
        self._last_start_kwargs = dict(
            conf=conf, center_x=center_x, center_y=center_y,
            joystick_step=joystick_step, scan_interval=scan_interval,
            move_wait=move_wait, navigation_enabled=navigation_enabled,
            max_inland_steps=max_inland_steps, ocean_land_ratio=ocean_land_ratio,
            min_water_px=min_water_px, footprint_ttl=footprint_ttl,
            diagonal_blind_coeff=diagonal_blind_coeff,
            coast_detect_radius=coast_detect_radius,
            return_delta_px=return_delta_px, smooth_alpha=smooth_alpha,
            use_beacon=use_beacon, pixels_per_step=pixels_per_step,
        )
        self._mm_cx = center_x
        self._mm_cy = center_y

        if use_beacon:
            try:
                from navigator_beacon import CoastalSnakeNavigatorBeacon
            except ImportError:
                use_beacon = False
        if use_beacon:
            nav = CoastalSnakeNavigatorBeacon(
                center_x=center_x,
                center_y=center_y,
                step=joystick_step,
                max_inland_steps=max_inland_steps,
                ocean_land_ratio=ocean_land_ratio,
                min_water_px=min_water_px,
                footprint_ttl=footprint_ttl,
                diagonal_blind_coeff=diagonal_blind_coeff,
                coast_detect_radius=coast_detect_radius,
                return_delta_px=return_delta_px,
                pixels_per_step=pixels_per_step,
                smooth_alpha=smooth_alpha,
            )
            self._pacman = PacmanEngine(
                center_x=center_x,
                center_y=center_y,
                step=joystick_step,
                conf=conf,
                scan_interval=scan_interval,
                sound_path=self.sound_path or 'Logo_exchange.wav',
                yolo_model=self.model,
                move_wait=move_wait,
                navigation_enabled=navigation_enabled,
                max_inland_steps=max_inland_steps,
                ocean_land_ratio=ocean_land_ratio,
                min_water_px=min_water_px,
                footprint_ttl=footprint_ttl,
                diagonal_blind_coeff=diagonal_blind_coeff,
                coast_detect_radius=coast_detect_radius,
                return_delta_px=return_delta_px,
                smooth_alpha=smooth_alpha,
            )
            self._pacman.joystick = nav   # inject beacon navigator
        else:
            self._pacman = PacmanEngine(
                center_x=center_x,
                center_y=center_y,
                step=joystick_step,
                conf=conf,
                scan_interval=scan_interval,
                sound_path=self.sound_path or 'Logo_exchange.wav',
                yolo_model=self.model,
                move_wait=move_wait,
                navigation_enabled=navigation_enabled,
                max_inland_steps=max_inland_steps,
                ocean_land_ratio=ocean_land_ratio,
                min_water_px=min_water_px,
                footprint_ttl=footprint_ttl,
                diagonal_blind_coeff=diagonal_blind_coeff,
                coast_detect_radius=coast_detect_radius,
                return_delta_px=return_delta_px,
                smooth_alpha=smooth_alpha,
            )
        # Roy: оборачиваем callback и запускаем scan-цикл
        if self.roy_enabled:
            from roy.roy_client import RoyClient
            self._roy_client = RoyClient(hwid=get_hwid())
            self._pacman.on_found_callback = self._build_roy_wrapper(self.on_found_callback)
        else:
            self._pacman.on_found_callback = self.on_found_callback

        self._pacman.restart_callback = self.on_exchange_found_callback
        self.is_running = True
        self._bg_gen += 1
        if self._initial_yolo_block_sec > 0:
            self._pacman._yolo_unblock_time = time.time() + self._initial_yolo_block_sec
            _roy_log(f"[ENGINE] start() — YOLO включится через {self._initial_yolo_block_sec:.0f}с")
            self._initial_yolo_block_sec = 0.0
        else:
            _roy_log("[ENGINE] start() — YOLO активен сразу")
        self._pacman.start()
        _roy_log(f"[ENGINE] PacmanEngine запущен | bg_gen={self._bg_gen} | move_wait={self._last_start_kwargs.get('move_wait')}")
        self._start_heartbeat()
        if self.roy_enabled:
            self._start_roy_scan()

    def stop(self):
        _roy_log(f"[ENGINE] stop() — is_running=False, bg_gen={self._bg_gen}, активных тредов={len(getattr(self,'_bg_threads',[]))}")
        self.is_running = False
        if self._pacman:
            self._pacman.stop()
        # Ждём завершения всех фоновых тредов (max 2с каждый)
        for t in getattr(self, '_bg_threads', []):
            if t.is_alive():
                t.join(timeout=2.0)
                _roy_log(f"[ENGINE] тред {t.name} {'завершён' if not t.is_alive() else 'ещё жив (зомби)'}")
        if hasattr(self, '_bg_threads'):
            self._bg_threads.clear()
        if self.roy_enabled and self._roy_client and self.roy_kingdom:
            self._roy_client.stop_session(self.roy_kingdom)
        _roy_log("[ENGINE] stop() завершён")

    def _build_roy_wrapper(self, original_cb):
        """Возвращает wrapper: вызывает original_cb в try/except, затем _roy_on_found."""
        def _wrapper(*args, **kwargs):
            _roy_log(">>> on_found_callback сработал — запускаю ROY OCR")
            if original_cb:
                try:
                    original_cb(*args, **kwargs)
                except Exception as e:
                    _roy_log(f"original_cb ERROR: {e!r}")
            self._roy_on_found()
        return _wrapper

    def _roy_on_found(self):
        """OCR диалога биржи → GUI-карточка владельца + отправка в Рой (если % < 90)."""
        _roy_log("_roy_on_found: старт OCR (timeout=4.0с)")
        try:
            from roy.exchange_reader import wait_and_read
            from debug_reporter import report_ocr_result
            result = wait_and_read(timeout=4.0)
            _roy_log(f"_roy_on_found: результат OCR = {result}")
            report_ocr_result(get_hwid(), result)
            if result:
                if self.on_last_exchange_callback:
                    try:
                        self.on_last_exchange_callback(result)
                    except Exception as e:
                        _roy_log(f"on_last_exchange_callback ERROR: {e!r}")
                if result['percent'] < 90 and not (self.roy_enabled and self.event_active):
                    _roy_log(f"Биржа {result['percent']}% — РОЙ выключен или ивент не активен, в пул не отправляем")
                elif result['percent'] < 90:
                    _roy_log(f"Отправляю в пул → K={result['kingdom']} X={result['x']} Y={result['y']} {result['percent']}%")
                    _cb = self._after_report_success if self.on_pool_refresh_callback else None
                    self._roy_client.report(
                        kingdom=result['kingdom'],
                        x=result['x'],
                        y=result['y'],
                        percent=result['percent'],
                        on_success=_cb,
                    )
                    _roy_log("report() отправлен")
                else:
                    _roy_log(f"Биржа выкуплена ({result['percent']}%) — в пул не отправляем")
            else:
                _roy_log("_roy_on_found: OCR вернул None — диалог не найден или текст не распознан")
        except Exception as e:
            _roy_log(f"_roy_on_found ERROR: {e!r}")

    def _after_report_success(self) -> None:
        """Вызывается из треда report() после успешного ответа сервера.
        Запрашивает актуальный пул и передаёт в GUI-callback.
        """
        if not self.on_pool_refresh_callback:
            return
        try:
            pool = self._roy_client.get_pool(consume=False)
            self.on_pool_refresh_callback(pool)
        except Exception as e:
            _roy_log(f"_after_report_success ERROR: {e!r}")

    def _start_roy_scan(self):
        """Proof of Scan: каждые 30 сек фиксирует активность (+45 сек баланса).
        Два условия для засчитывания: ивент активен И миникарта изменилась ≥15%.
        """
        _SIZE     = 180
        _DIFF_THR = 0.15   # 15% пикселей должны измениться
        _PIX_THR  = 30     # порог яркости на пиксель

        def _grab():
            from mss import mss as _mss
            off = _SIZE // 2
            region = {'left': self._mm_cx - off, 'top': self._mm_cy - off,
                      'width': _SIZE, 'height': _SIZE}
            with _mss() as sct:
                return np.array(sct.grab(region), dtype=np.int16)

        gen = self._bg_gen

        def _loop():
            frame_prev = _grab()
            while self.is_running and self._bg_gen == gen:
                for _ in range(30):
                    if not self.is_running or self._bg_gen != gen:
                        return
                    time.sleep(1)

                frame_curr = _grab()
                diff_frac  = np.any(
                    np.abs(frame_curr - frame_prev) > _PIX_THR, axis=-1
                ).mean()
                frame_prev = frame_curr

                if not (self.roy_enabled and self.event_active):
                    _roy_log(f"scan() SKIP — roy_enabled={self.roy_enabled} event_active={self.event_active}")
                    continue

                ok = self._roy_client.scan(kingdom=self.roy_kingdom or None)
                _roy_log(f"scan() → {'OK +45с' if ok else 'FAIL'} | diff={diff_frac:.1%}")

        t_roy = threading.Thread(target=_loop, daemon=True, name="RoyScan")
        self._bg_threads.append(t_roy)
        t_roy.start()
        _roy_log(f"[ENGINE] RoyScan тред запущен | gen={gen}")

    def _start_heartbeat(self):
        """Фоновый поток: пингует сервер каждые 2 минуты пока бот запущен."""
        self._bg_gen += 1
        gen = self._bg_gen
        def _loop():
            while self.is_running and self._bg_gen == gen:
                _heartbeat()
                for _ in range(12):  # 12 × 10 сек = 2 мин
                    if not self.is_running or self._bg_gen != gen:
                        return
                    time.sleep(10)
        t = threading.Thread(target=_loop, daemon=True, name="Heartbeat")
        self._bg_threads.append(t)
        t.start()
        _roy_log(f"[ENGINE] Heartbeat тред запущен | gen={gen}")
