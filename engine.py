import os
import json
import time
import threading
import winsound
import numpy as np
import pyautogui
from ultralytics import YOLO

from navigator import PacmanEngine
from auth import heartbeat as _heartbeat, get_hwid
import nav_logger
nav_logger.install()

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
            print(f"[TH v1.2.6] YOLO device (pt): {_device}")

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
        self._roy_client   = None
        self.on_last_exchange_callback = None  # (result: dict) → обновляет GUI владельца

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
        if use_beacon:
            from navigator_beacon import CoastalSnakeNavigatorBeacon
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
            original_cb = self.on_found_callback

            def _roy_found_wrapper(*args, **kwargs):
                if original_cb:
                    original_cb(*args, **kwargs)
                threading.Thread(target=self._roy_on_found, daemon=True).start()

            self._pacman.on_found_callback = _roy_found_wrapper
        else:
            self._pacman.on_found_callback = self.on_found_callback

        self.is_running = True
        self._pacman.start()
        self._start_heartbeat()
        if self.roy_enabled:
            self._start_roy_scan()

    def stop(self):
        self.is_running = False
        if self._pacman:
            self._pacman.stop()

    def _roy_on_found(self):
        """OCR диалога биржи → GUI-карточка владельца + отправка в Рой (если % < 90)."""
        try:
            from roy.exchange_reader import wait_and_read
            result = wait_and_read(timeout=4.0)
            if result:
                # Показываем координаты владельцу всегда (любой %)
                if self.on_last_exchange_callback:
                    self.on_last_exchange_callback(result)
                # В общий РОЙ — только если биржа ещё не выкуплена
                if result['percent'] < 90:
                    self._roy_client.report(
                        kingdom=result['kingdom'],
                        x=result['x'],
                        y=result['y'],
                        percent=result['percent'],
                    )
        except Exception:
            pass

    def _start_roy_scan(self):
        """Proof of Scan: каждые 30 сек фиксирует активность (+45 сек баланса)."""
        def _loop():
            while self.is_running:
                self._roy_client.scan()
                for _ in range(30):
                    if not self.is_running:
                        break
                    time.sleep(1)
        threading.Thread(target=_loop, daemon=True).start()

    def _start_heartbeat(self):
        """Фоновый поток: пингует сервер каждые 2 минуты пока бот запущен."""
        def _loop():
            while self.is_running:
                _heartbeat()
                # Спим по 10 сек кусками — чтобы быстро реагировать на stop()
                for _ in range(12):  # 12 × 10 сек = 2 мин
                    if not self.is_running:
                        break
                    time.sleep(10)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
