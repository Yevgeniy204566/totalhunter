"""
Проверка калибровки — читает текущие координаты каждые 2 секунды.
Запусти, переключись на игру, подвигай карту вручную мышкой
и смотри как меняются координаты X/Y.
"""
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

import numpy as np
from navigator import PositionReader
from calibration import grab_screen

reader = PositionReader(crop_box=(0, 990, 300, 1080))

print("Читаю координаты. Переключись на игру и подвигай карту вручную.")
print("Ctrl+C для остановки.\n")

prev = None
for i in range(30):
    screen = grab_screen()
    pos = reader.read(screen)
    if pos:
        if prev and pos != prev:
            dx = pos[0] - prev[0]
            dy = pos[1] - prev[1]
            print(f"X={pos[0]:4d}  Y={pos[1]:4d}    (ΔX={dx:+d}  ΔY={dy:+d})")
        else:
            print(f"X={pos[0]:4d}  Y={pos[1]:4d}")
        prev = pos
    else:
        print("[ координаты не читаются ]")
    time.sleep(2)
