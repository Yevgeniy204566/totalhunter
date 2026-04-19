import cv2, numpy as np, mss
from PIL import ImageGrab

# Метод 1: PIL ImageGrab
img_pil = ImageGrab.grab()
img1 = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
cv2.imwrite('snap_pil.png', img1)
print(f"snap_pil.png — PIL, размер {img1.shape[1]}x{img1.shape[0]}")

# Метод 2: mss все мониторы
with mss.mss() as sct:
    for i, mon in enumerate(sct.monitors):
        print(f"  monitor[{i}]: {mon}")
    img_mss = np.array(sct.grab(sct.monitors[1]))
    img2 = cv2.cvtColor(img_mss, cv2.COLOR_BGRA2BGR)
    cv2.imwrite('snap_mss.png', img2)
    print(f"snap_mss.png — mss[1], размер {img2.shape[1]}x{img2.shape[0]}")
