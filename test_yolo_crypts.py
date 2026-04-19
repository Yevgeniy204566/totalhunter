"""
Быстрый тест: делает скриншот и прогоняет YOLO crypts.pt.
Запустить когда открыто меню Дозорной башни со списком склепов.
"""
import mss
import numpy as np
import cv2
from ultralytics import YOLO
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Проверяем обе копии модели
models_to_test = [
    os.path.join(SCRIPT_DIR, 'crypts.pt'),
    os.path.join(SCRIPT_DIR, 'targets', 'crypts.pt'),
]

for model_path in models_to_test:
    if not os.path.exists(model_path):
        print(f"НЕТ ФАЙЛА: {model_path}")
        continue

    size_mb = os.path.getsize(model_path) / 1024 / 1024
    print(f"\n{'='*50}")
    print(f"Тестирую: {model_path}")
    print(f"Размер: {size_mb:.1f} MB")

    model = YOLO(model_path)
    print(f"Классы модели ({len(model.names)}): {list(model.names.values())}")

    # Скриншот
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
    img = np.array(raw)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # Детекция с низким порогом чтобы увидеть хоть что-то
    for conf in [0.7, 0.5, 0.3, 0.1]:
        results = model(img, conf=conf, verbose=False)
        detections = []
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    cls_name = r.names[int(box.cls.tolist()[0])]
                    confidence = float(box.conf.tolist()[0])
                    detections.append(f"{cls_name} ({confidence:.2f})")
        if detections:
            print(f"  conf={conf}: НАЙДЕНО → {detections}")
            # Сохраняем скриншот с боксами
            out_img = results[0].plot()
            save_path = os.path.join(SCRIPT_DIR, f'debug_detection_conf{int(conf*100)}.jpg')
            cv2.imwrite(save_path, out_img)
            print(f"  Скриншот с боксами: {save_path}")
            break
        else:
            print(f"  conf={conf}: ничего не найдено")
