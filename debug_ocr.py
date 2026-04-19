"""
Дебаг: захватывает скриншот прямо сейчас и сохраняет зоны OCR.
Запусти, СРАЗУ переключись на игру, подожди 5 сек — потом смотри файлы.
"""
import time
import sys
print("Открой игру, встань на карту.")
print("Нажми Enter — затем СРАЗУ переключись на игру (3 секунды).\n")
input(">>> Enter: ")
print("3..."); time.sleep(1)
print("2..."); time.sleep(1)
print("1..."); time.sleep(1)
print("Снимаю!\n")

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import numpy as np
from PIL import Image
from calibration import grab_screen

screen = grab_screen()
img = Image.fromarray(screen)
w, h = img.size
print(f"Размер экрана: {w}x{h}")

# Сохраняем весь скриншот
img.save('debug_fullscreen.png')
print("Сохранён debug_fullscreen.png")

# Сохраняем все варианты кропов
crops = [
    ('crop_base',    0, h-90,  300, h),
    ('crop_wider',   0, h-105, 350, h),
    ('crop_bottom',  0, h-120, 400, h),
    ('crop_quarter', 0, h//4*3, 400, h),
]
for name, x1, y1, x2, y2 in crops:
    y1 = max(0, y1)
    crop = img.crop((x1, y1, x2, y2))
    crop_big = crop.resize((crop.width*4, crop.height*4), Image.NEAREST)
    crop_big.save(f'debug_{name}.png')

    text = pytesseract.image_to_string(crop_big, config='--psm 12').strip().replace('\n', ' ')
    print(f"  {name}: [{text[:80]}]")

print("\nПроверь файлы debug_*.png")
