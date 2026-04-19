"""
Отладка поиска склепов в меню.
Запустить когда открыто меню Дозорной башни → «Склепы и арены».
"""
import mss
import numpy as np
import cv2
from ultralytics import YOLO
import os

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH       = os.path.join(SCRIPT_DIR, 'targets', 'crypts.pt')
MENU_SCAN_REGION = (597, 242, 721, 575)
WT_GOTO_BTN_X    = 1208

_GUI_NAMES = (
    [f"Ordinary_{i}" for i in range(1, 13)] +
    [f"Epic_{i}"     for i in range(2, 19)] +
    ['R_1', 'R_2']
)
YOLO_TO_GUI  = {f"crypt_{i}": name for i, name in enumerate(_GUI_NAMES)}
ALL_SELECTED = set(_GUI_NAMES)

print(f"Загружаю модель: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

# Полный скриншот
with mss.mss() as sct:
    raw = sct.grab(sct.monitors[1])
img = np.array(raw)
img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

mx, my, mw, mh = MENU_SCAN_REGION

for conf_threshold in [0.7, 0.5, 0.3, 0.1]:
    results = model(img_bgr, conf=conf_threshold, verbose=False)
    found_all, found_in_menu = [], []

    for r in results:
        if not r.boxes:
            continue
        for box in r.boxes:
            coords    = box.xyxy.tolist()[0]
            cx        = int((coords[0] + coords[2]) / 2)
            cy        = int((coords[1] + coords[3]) / 2)
            yolo_name = r.names[int(box.cls.tolist()[0])]
            gui_name  = YOLO_TO_GUI.get(yolo_name, f"?{yolo_name}")
            confidence= float(box.conf.tolist()[0])
            in_menu   = mx <= cx <= mx + mw and my <= cy <= my + mh
            found_all.append((gui_name, confidence, cx, cy, in_menu))
            if in_menu:
                found_in_menu.append((gui_name, confidence, cy))

    if found_all:
        print(f"\n=== conf={conf_threshold} — всего {len(found_all)} объектов, в меню {len(found_in_menu)} ===")
        for name, conf, cx, cy, in_menu in found_all:
            tag = "[МЕНЮ]" if in_menu else "[карта]"
            print(f"  {tag} {name}  conf={conf:.2f}  центр=({cx},{cy})")
        if found_in_menu:
            print(f"\nБот кликнул бы «Перейти» по: {[(n, f'y={cy}') for n,_,cy in found_in_menu]}")
        out = results[0].plot()
        cv2.imwrite(os.path.join(SCRIPT_DIR, 'debug_fullscreen_boxes.jpg'), out)
        print("Скриншот с боксами: debug_fullscreen_boxes.jpg")
        break
    else:
        print(f"conf={conf_threshold}: ничего не найдено")
