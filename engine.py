import os
import json
import time
import threading
import winsound
import numpy as np
from ultralytics import YOLO

from navigator import PacmanEngine
from auth import heartbeat as _heartbeat


class HuntEngine:
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(script_dir, 'exchange.pt')
        self.model = YOLO(self.model_path)

        files_in_dir = os.listdir(script_dir)
        sound_file = next((f for f in files_in_dir if f.lower().endswith('.wav')), None)
        self.sound_path = os.path.join(script_dir, sound_file) if sound_file else None

        self.is_running = False
        self.on_found_callback = None
        self._pacman: PacmanEngine | None = None

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
        max_pitch_delta: float = 15.0,
        max_footprint_overlap: float = 0.5,
    ):
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
            max_pitch_delta=max_pitch_delta,
            max_footprint_overlap=max_footprint_overlap,
        )
        self._pacman.on_found_callback = self.on_found_callback

        self.is_running = True
        self._pacman.start()
        self._start_heartbeat()

    def stop(self):
        self.is_running = False
        if self._pacman:
            self._pacman.stop()

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
