"""
roy_client.py — HTTP-клиент для Системы РОЙ (вызывается из бота).
"""

import threading
import requests

SERVER_URL = "http://34.68.86.57:8000"
_TIMEOUT   = 5


class RoyClient:
    def __init__(self, hwid: str):
        self.hwid = hwid

    def report(self, kingdom: int, x: int, y: int, percent: int) -> None:
        """Отправляет координаты биржи в пул Роя. Fire-and-forget."""
        def _send():
            try:
                requests.post(f"{SERVER_URL}/roy/report", json={
                    "hwid": self.hwid, "kingdom": kingdom,
                    "x": x, "y": y, "percent": percent,
                }, timeout=_TIMEOUT)
            except Exception:
                pass
        threading.Thread(target=_send, daemon=True).start()

    def scan(self) -> None:
        """Фиксирует 30 сек активного сканирования (+45 сек баланса)."""
        try:
            requests.post(f"{SERVER_URL}/roy/scan",
                          json={"hwid": self.hwid}, timeout=_TIMEOUT)
        except Exception:
            pass

    def get_pool(self, consume: bool = False) -> list:
        """Возвращает список актуальных координат от других участников Роя."""
        try:
            r = requests.get(f"{SERVER_URL}/roy/pool",
                             params={"hwid": self.hwid, "consume": str(consume).lower()},
                             timeout=_TIMEOUT)
            data = r.json()
            return data.get("pool", []) if data.get("success") else []
        except Exception:
            return []

    def get_balance(self) -> int:
        """Текущий баланс времени доступа к Рою в секундах."""
        try:
            r = requests.get(f"{SERVER_URL}/roy/balance/{self.hwid}", timeout=_TIMEOUT)
            return r.json().get("balance_sec", 0)
        except Exception:
            return 0
