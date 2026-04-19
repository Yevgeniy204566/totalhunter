"""
Дебаг OCR времени марша.
Как использовать:
  1. Открой игру, кликни на склеп на карте — должен открыться диалог с временем марша
  2. Запусти этот скрипт
  3. Нажми Enter — СРАЗУ переключись на игру (3 сек)
  4. Смотри debug_time_*.png и вывод в консоль
"""
import time, re, os
import pytesseract
import cv2
import numpy as np
import mss

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Регион как в боте (1920x1080 координаты)
REGION = (820, 773, 280, 42)   # x, y, w, h

print("Открой диалог склепа в игре (должно быть видно время марша).")
input("Нажми Enter, затем СРАЗУ переключись на игру (3 сек)...\n")
for i in (3, 2, 1):
    print(f"{i}..."); time.sleep(1)
print("Снимаю!\n")

# Скриншот
with mss.mss() as sct:
    mon = {'left': REGION[0], 'top': REGION[1], 'width': REGION[2], 'height': REGION[3]}
    raw = sct.grab(mon)
    img = np.array(raw)[:, :, :3]  # BGR

# Полный скриншот для контекста
with mss.mss() as sct:
    full_raw = sct.grab(sct.monitors[1])
    full_img = np.array(full_raw)[:, :, :3]
    cv2.imwrite('debug_time_fullscreen.png', full_img)
    print("debug_time_fullscreen.png — весь экран")

# Сохраняем зону как есть
cv2.imwrite('debug_time_region.png', img)
print(f"debug_time_region.png — зона {REGION}")

# Обработка
gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
scaled = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
_, thresh   = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
inv_thresh  = cv2.bitwise_not(thresh)

cv2.imwrite('debug_time_thresh.png',   thresh)
cv2.imwrite('debug_time_inverted.png', inv_thresh)
print("debug_time_thresh.png / debug_time_inverted.png — обработанные\n")

# OCR все варианты
variants = [('thresh', thresh), ('inverted', inv_thresh), ('scaled', scaled)]
print(f"{'Вариант':<12} {'PSM':<6} {'OCR результат':<50} {'parse_time'}")
print('-' * 90)

def parse_time(text):
    colon_pos = text.find(':')
    if colon_pos > 0:
        before = [int(n) for n in re.findall(r'\d+', text[:colon_pos])]
        after  = [int(n) for n in re.findall(r'\d+', text[colon_pos+1:])]
        mins_ok = [n for n in before if n <= 30]
        secs_ok = [n for n in after  if n <= 59]
        if mins_ok and secs_ok:
            return mins_ok[-1] * 60 + secs_ok[0]
    nums = [int(n) for n in re.findall(r'\d+', text)]
    mins_ok = [n for n in nums if n <= 30]
    secs_ok = [n for n in nums if n <= 59]
    if mins_ok and len(secs_ok) >= 2:
        m_val = mins_ok[0]
        s_val = next((n for n in secs_ok if n != m_val), None)
        if s_val is not None:
            return m_val * 60 + s_val
    if nums and nums[0] <= 59:
        return float(nums[0])
    return 0.0

for vname, variant in variants:
    for psm in ('--psm 6', '--psm 7', '--psm 13'):
        text = pytesseract.image_to_string(variant, config=psm)
        raw  = text.strip().replace('\n', ' ')[:48]
        t    = parse_time(text)
        mark = '  <-- УСПЕХ' if t > 0 else ''
        print(f"{vname:<12} {psm:<6} {repr(raw):<50} {t:.0f}с{mark}")

print("\nСкинь этот вывод и файл debug_time_region.png в чат.")
