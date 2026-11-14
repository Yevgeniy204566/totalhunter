"""Лог сбора сундуков: logs/chest_YYYYMMDD_HHMMSS.log (по образцу crypt_*.log).

Зачем: у владельца после нескольких Старт/Стоп отправка/сбор молча переставали работать, а следов не
оставалось. Лог пишет этапы сбора и отправки; ключевые события (report) дополнительно уходят на сервер
через /log_error — не чаще SERVER_REPORT_LIMIT за запуск, в фоне (сбор не ждёт сеть).
Правила: лог НИКОГДА не роняет сбор; ники и имена игроков в лог не пишутся."""
import datetime
import os
import threading
import traceback

KEEP_LOGS = 10
SERVER_REPORT_LIMIT = 40

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_state = {"file": None, "reports": 0}
_lock = threading.Lock()


def _default_log_dir() -> str:
    return os.path.join(_SCRIPT_DIR, "logs")


def current_file():
    return _state["file"]


def _rotate(log_dir: str) -> None:
    names = sorted(n for n in os.listdir(log_dir) if n.startswith("chest_") and n.endswith(".log"))
    for old in names[:-KEEP_LOGS]:
        try:
            os.remove(os.path.join(log_dir, old))
        except OSError:
            pass


def start_run(log_dir: str = None) -> None:
    """Новый файл на каждый запуск сбора; счётчик отправок на сервер обнуляется."""
    with _lock:
        _state["reports"] = 0
        try:
            log_dir = log_dir or _default_log_dir()
            os.makedirs(log_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(log_dir, f"chest_{ts}.log")
            n = 1
            while os.path.exists(path):   # два запуска в одну секунду не должны слиться
                n += 1
                path = os.path.join(log_dir, f"chest_{ts}_{n}.log")
            open(path, "a", encoding="utf-8").close()
            _state["file"] = path
            _rotate(log_dir)
        except Exception:
            _state["file"] = None


def log(level: str, msg: str) -> None:
    path = _state["file"]
    if not path:
        return
    try:
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with _lock, open(path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{level}] {msg}\n")
    except Exception:
        pass


def log_exc(msg: str) -> None:
    """Сообщение + полный traceback текущего исключения."""
    log("ERROR", f"{msg}\n{traceback.format_exc()}")


def _send_to_server(text: str) -> None:
    from auth import log_error_to_server
    log_error_to_server(text)


def _spawn(fn, *args) -> None:
    threading.Thread(target=fn, args=args, daemon=True).start()


def report(msg: str, level: str = "INFO") -> None:
    """В файл всегда; на сервер — не больше SERVER_REPORT_LIMIT раз за запуск, в фоновом потоке."""
    log(level, msg)
    with _lock:
        if _state["reports"] >= SERVER_REPORT_LIMIT:
            return
        _state["reports"] += 1
    try:
        _spawn(_send_to_server, f"chest: {msg}")
    except Exception:
        pass
