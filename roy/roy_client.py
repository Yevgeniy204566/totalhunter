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

    def report_scout_find(self, kingdom: int, x: int, y: int) -> bool:
        """Публикует находку Биржи 2.0 на сайт (раздел РОЙ). Fire-and-forget в отдельном треде,
        consumer не ждёт ответа. kingdom<=0 (поле в GUI пусто) — сервер такое не показывает,
        запрос не шлём. Возвращает True, если тред запущен."""
        if kingdom <= 0:
            print(f"[ROY] scout-find skipped: kingdom={kingdom}")
            return False

        def _send():
            try:
                r = requests.post(f"{SERVER_URL}/roy/scout-find", json={
                    "hwid": self.hwid, "kingdom": kingdom, "x": x, "y": y,
                }, timeout=_TIMEOUT)
                if not r.json().get("success"):
                    print(f"[ROY] scout-find rejected: HTTP {r.status_code}")
            except Exception as e:
                print(f"[ROY] scout-find ERROR: {e!r}")
        t = threading.Thread(target=_send)
        t.daemon = False  # как в report(): запрос должен завершиться до выхода процесса; timeout requests — 5 с на подключение и на чтение отдельно, суммарного лимита нет
        t.start()
        return True

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

    def idle(self) -> bool:
        """Фиксирует 60 сек простоя при включённом тумблере РОЙ (−30 сек баланса).
        Возвращает True если сервер принял запрос.
        """
        try:
            r = requests.post(f"{SERVER_URL}/roy/idle", json={"hwid": self.hwid}, timeout=_TIMEOUT)
            return r.json().get("success", False)
        except Exception as e:
            print(f"[ROY] idle() ERROR: {e!r}")
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
