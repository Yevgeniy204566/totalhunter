"""
roy_client.py — HTTP-клиент для Системы РОЙ (вызывается из бота).
"""

import threading
import requests

SERVER_URL = "https://api.total-hunter.com"
_TIMEOUT   = 5


class RoyClient:
    def __init__(self, hwid: str):
        self.hwid = hwid

    def register(self, kingdom: int) -> None:
        """Сохраняет намерение охотника на сервере (серый кружок). Fire-and-forget."""
        def _send():
            try:
                requests.post(f"{SERVER_URL}/roy/register", json={
                    "hwid": self.hwid, "kingdom": kingdom,
                }, timeout=_TIMEOUT)
            except Exception:
                pass
        threading.Thread(target=_send, daemon=True).start()

    def report(self, kingdom: int, x: int, y: int, percent: int,
               on_success=None) -> None:
        """Отправляет координаты биржи в пул Роя.
        НЕ daemon-поток — HTTP-запрос должен завершиться до выхода процесса.
        on_success() вызывается в том же треде если сервер вернул success=True.
        """
        def _send():
            try:
                r = requests.post(f"{SERVER_URL}/roy/report", json={
                    "hwid": self.hwid, "kingdom": kingdom,
                    "x": x, "y": y, "percent": percent,
                }, timeout=_TIMEOUT)
                if on_success and r.json().get("success"):
                    try:
                        on_success()
                    except Exception:
                        pass
            except Exception:
                pass
        t = threading.Thread(target=_send)
        t.daemon = False  # ждём завершения HTTP-запроса перед выходом процесса
        t.start()

    def scan(self, kingdom: int | None = None) -> bool:
        """Фиксирует 30 сек активного сканирования (+45 сек баланса).
        Если передан kingdom — обновляет live-счётчик ГОСа на сервере.
        Возвращает True если сервер принял запрос.
        """
        payload: dict = {"hwid": self.hwid}
        if kingdom is not None:
            payload["kingdom"] = kingdom
        try:
            r = requests.post(f"{SERVER_URL}/roy/scan", json=payload, timeout=_TIMEOUT)
            return r.json().get("success", False)
        except Exception as e:
            print(f"[ROY] scan() ERROR: {e!r}")
            return False

    def stop_session(self, kingdom: int) -> None:
        """Сигнал серверу об остановке поиска в ГОСе. Fire-and-forget."""
        def _send():
            try:
                requests.post(f"{SERVER_URL}/roy/stop",
                              json={"hwid": self.hwid, "kingdom": kingdom},
                              timeout=_TIMEOUT)
            except Exception:
                pass
        threading.Thread(target=_send, daemon=True).start()

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
