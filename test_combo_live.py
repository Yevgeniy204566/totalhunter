"""
test_combo_live.py — живая диагностика комбинирования.

Запуск:
    python test_combo_live.py

После запуска у тебя 10 секунд чтобы переключиться на игру
и открыть окно Комбинирования. Скрипт сделает скриншот,
наложит сетку + OCR и сохранит combo_live_debug.png
"""
import time
import sys
import cv2
import numpy as np
import mss

# Загружаем калибровку
from coord_manager import coord_manager
try:
    coord_manager.load("profiles/profile_client.json")
    print("Калибровка загружена: profile_client.json")
except Exception:
    print("Калибровка по умолчанию (1920x1080)")

from combiner import (
    CombinerEngine,
    COMBO_GRID_X, COMBO_GRID_Y,
    COMBO_SLOT_W, COMBO_SLOT_H,
    COMBO_COLS, COMBO_ROWS_VISIBLE,
    CLICK_X_RATIO, CLICK_Y_RATIO,
    NUM_ROI,
    parse_number,
)

DELAY = 12  # секунд до скриншота

print(f"\nОткрой Комбинирование в игре, скриншот через {DELAY} сек...")
print("Countdown:", end="", flush=True)
for i in range(DELAY, 0, -1):
    print(f" {i}", end="", flush=True)
    time.sleep(1)
print(" GO!")

engine = CombinerEngine()
grid = engine._capture_grid()

# Строим дебаг-картинку в ref-масштабе
debug = grid.copy()
xo, yo, nw, nh = NUM_ROI

print("\n=== OCR по карточкам ===")
for row in range(COMBO_ROWS_VISIBLE):
    for col in range(COMBO_COLS - 1):
        sx = col * COMBO_SLOT_W
        sy = row * COMBO_SLOT_H

        # Рамка слота
        cv2.rectangle(debug, (sx, sy),
                      (sx + COMBO_SLOT_W - 1, sy + COMBO_SLOT_H - 1),
                      (255, 100, 0), 1)

        # NUM_ROI
        cv2.rectangle(debug, (sx + xo, sy + yo),
                      (sx + xo + nw, sy + yo + nh),
                      (0, 200, 255), 1)

        # OCR
        roi = grid[sy + yo: sy + yo + nh, sx + xo: sx + xo + nw]
        text = engine._zoom_ocr(roi) if roi.size > 0 else ""
        count = parse_number(text)

        # Точка клика
        cx = int(sx + COMBO_SLOT_W * CLICK_X_RATIO)
        cy = int(sy + COMBO_SLOT_H * CLICK_Y_RATIO)
        color = (0, 255, 0) if count >= 4 else (0, 80, 255)
        cv2.circle(debug, (cx, cy), 4, color, -1)

        # Текст OCR на картинке
        label = f"{count}" if count else "?"
        cv2.putText(debug, label, (sx + 2, sy + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1)

        if count > 0:
            print(f"  [{row},{col}] OCR='{text.strip()}' = {count} | "
                  f"click=({sx+cx},{sy+cy})")

out = "combo_live_debug.png"
cv2.imwrite(out, debug)
print(f"\nSaved: {out}")
print("Зелёные точки = карточки с count>=4 (будут кликнуты)")
print("Красные точки = count<4 (пропуск)")
print("Циан рамки    = NUM_ROI регион OCR")
