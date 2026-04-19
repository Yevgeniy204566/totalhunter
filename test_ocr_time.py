"""
test_ocr_time.py — диагностика OCR времени марша Картера.

Запуск: python test_ocr_time.py
Открой диалог ускорения в игре, скрипт снимет скриншот через 3 сек.
Все файлы сохраняются в ту же папку, что и этот скрипт.
"""
import time
import sys
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

def out(path):
    return os.path.join(HERE, path)

try:
    import cv2
    import numpy as np
    import pytesseract
    import mss
except ImportError as e:
    print(f"ОШИБКА ИМПОРТА: {e}")
    print("Установи: pip install opencv-python pytesseract mss")
    sys.exit(1)

REGION = (980, 295, 340, 80)
SCALE  = 4
PSMS   = ('--psm 6', '--psm 7', '--psm 13')


def parse_time(text: str) -> float:
    text = text.upper()
    text = text.replace('M', 'М').replace('C', 'С').replace('H', 'Ч')
    h = re.search(r'(\d+)\s*Ч', text)
    m = re.search(r'(\d+)\s*М', text)
    s = re.search(r'(\d+)\s*С', text)
    hours   = float(h.group(1)) if h else 0.0
    minutes = float(m.group(1)) if m else 0.0
    seconds = float(s.group(1)) if s else 0.0
    return hours * 3600 + minutes * 60 + seconds


def grab_region(region):
    x, y, w, h = region
    with mss.mss() as sct:
        raw = sct.grab({"left": x, "top": y, "width": w, "height": h})
    img = np.array(raw)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def main():
    print("=" * 60)
    print("Диагностика OCR времени марша Картера")
    print(f"Регион: {REGION}  (x, y, w, h)")
    print(f"Файлы будут сохранены в: {HERE}")
    print("Открой диалог ускорения в игре.")
    print("Скриншот через 3 секунды...")
    print("=" * 60)
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    try:
        img_bgr = grab_region(REGION)
    except Exception as e:
        print(f"ОШИБКА скриншота: {e}")
        sys.exit(1)

    cv2.imwrite(out("ocr_time_region.png"), img_bgr)
    print(f"\nСохранено: ocr_time_region.png  ({img_bgr.shape[1]}x{img_bgr.shape[0]} px)")

    gray   = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv       = cv2.bitwise_not(thresh)

    cv2.imwrite(out("ocr_time_thresh.png"),     thresh)
    cv2.imwrite(out("ocr_time_inv.png"),        inv)
    cv2.imwrite(out("ocr_time_raw_scaled.png"), scaled)
    print("Сохранено: ocr_time_thresh.png, ocr_time_inv.png, ocr_time_raw_scaled.png")

    variants = [("thresh", thresh), ("inv", inv), ("raw", scaled)]

    print("\n" + "-" * 60)
    print(f"{'Вариант':<10} {'PSM':<12} {'Текст OCR':<30} {'Секунды':>8}")
    print("-" * 60)

    best = None
    for name, img_v in variants:
        for psm in PSMS:
            try:
                text = pytesseract.image_to_string(img_v, config=psm).strip()
            except Exception as e:
                text = f"[ошибка: {e}]"
            secs = parse_time(text)
            short = text.replace('\n', ' ')[:28]
            marker = "  <-- УСПЕХ" if secs > 0 else ""
            print(f"{name:<10} {psm:<12} {short!r:<30} {secs:>8.1f}{marker}")
            if secs > 0 and best is None:
                best = (name, psm, text, secs)

    print("-" * 60)

    if best:
        name, psm, text, secs = best
        m, s = divmod(int(secs), 60)
        h2, m = divmod(m, 60)
        fmt = (f"{h2}ч " if h2 else "") + (f"{m}м " if m else "") + f"{s}с"
        print(f"\nПРОЧИТАНО: {secs:.0f} сек ({fmt.strip()})")
        print(f"Вариант: {name}, {psm}")
        print(f"Текст: {text!r}")
    else:
        print("\nНЕ ПРОЧИТАНО ни одним вариантом.")
        print("=> Открой ocr_time_region.png и проверь что регион захватывает цифры времени.")
        print("=> Если регион пустой/чёрный — диалог не был открыт в момент скриншота.")

    print(f"\nВсе файлы в: {HERE}")
    return 0 if best else 1


if __name__ == "__main__":
    sys.exit(main())
