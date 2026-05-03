"""Тест OCR масла — привязка к Point B из текущего профиля."""
import time, cv2, traceback
import numpy as np
import pytesseract
from mss import mss
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from coord_manager import coord_manager, REF_B
from crypt_hunter import (
    _OIL_DX_ANCHOR, _OIL_DY, _OIL_SECTION_W, _OIL_ICON_W, _OIL_NUM_W, _OIL_H,
    parse_oil_value,
)

# Загружаем последний использованный профиль
import json, os
cfg_path = os.path.join(os.path.dirname(__file__), 'gui_config.json')
try:
    with open(cfg_path, encoding='utf-8') as f:
        cfg = json.load(f)
    last = cfg.get('last_calibration_profile', 'client')
    profiles = {'client': 'profiles/profile_client.json',
                'chrome': 'profiles/profile_chrome.json',
                'firefox': 'profiles/profile_firefox.json'}
    pfile = profiles.get(last, 'profiles/profile_client.json')
    coord_manager.load(pfile)
    print(f"Профиль: {last} | Point B = {coord_manager._point_b}")
except Exception as e:
    print(f"Профиль не загружен ({e}), используем эталон Point B={REF_B}")

bx, by = coord_manager._point_b
sx = coord_manager.scale_x
sy = abs(coord_manager.scale_y)
print(f"scale_x={sx:.3f}  scale_y={sy:.3f}")

def region_for(section_idx):
    x = bx + int((_OIL_DX_ANCHOR + section_idx * _OIL_SECTION_W + _OIL_ICON_W) * sx)
    y = by + int(_OIL_DY * sy)
    return (x, y, int(_OIL_NUM_W * sx), int(_OIL_H * sy))

def grab(r):
    x, y, w, h = r
    with mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
    return np.array(shot)[:, :, :3]

def ocr(section_idx, tag):
    try:
        r = region_for(section_idx)
        img = grab(r)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, (r[2]*6, r[3]*6), interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(f"oil_test_{tag}.png", thresh)
        text = pytesseract.image_to_string(
            thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789.,MmKk')
        val = parse_oil_value(text)
        return val, text.strip(), None
    except Exception:
        return 0, "", traceback.format_exc()

print("\nПереключись на игру! Захват через 10 секунд:")
for i in range(10, 0, -1):
    print(f"  {i}...", flush=True)
    time.sleep(1)

lines = []
for idx, tag, label in [(0,"ordinary","🟢 обычное"),
                         (1,"epic",    "🔵 эпическое"),
                         (2,"rare",    "🟣 редкое")]:
    val, raw, err = ocr(idx, tag)
    r = region_for(idx)
    if err:
        lines.append(f"{label}: ERROR region={r}\n{err}")
    else:
        lines.append(f"{label}: region={r}  raw='{raw}'  → {val:,}")

result = "\n".join(lines)
with open("oil_test_result.txt", "w", encoding="utf-8") as f:
    f.write(result)
print("Готово — читаю oil_test_result.txt сам")
