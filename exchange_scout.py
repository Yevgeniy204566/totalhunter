"""
exchange_scout.py — Биржа 2.0 (Exchange Scout).

Три этапа (решение владельца 2026-09-21, сессия #147):
  1. ЗМЕЙКА    — навигация по карте + полные screenshots → pending/ (ЕДИНАЯ очередь, без папок сессий)
  2. YOLO      — фоновый consumer: pending → YOLO → found (только кадры с биржей)
  3. КООРДИНАТЫ — found → ROI #13 (exchange_coord_roi) → OCR → X/Y → spend_credit → RoyClient

Этот файл реализуется поэтапно, TDD. Текущее состояние — Этап 1: структура сессии (уникальный sid,
подпапки) и атомарная запись кадра (cv2.imencode → .tmp → os.replace) — внутренний механизм надёжности
Этапа 1, чтобы Этап 2 никогда не читал недописанный JPEG.
"""
import json
import os
import re
import threading
import time

import cv2

from exchange_mode_settings import SCOUT_QUEUE_PAUSE_THRESHOLD, SCOUT_PAUSE_MINUTES

# Всё в очереди и в found старше 30 минут удаляется (решение владельца 2026-09-18/21: биржи живут
# 30–40 минут, старые кадры бессмысленны, мусор копить нельзя).
QUEUE_TTL_SEC = 30 * 60
# Скрины, которые пользователь кладёт в очередь руками (PNG из Windows и т. п.), тоже принимаются.
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
_SWEPT_ROOTS = ("pending", "found", "errors")   # errors — остаток прежней схемы «папка на сессию»

SESSION_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_[0-9a-f]{4}$")


def generate_session_id() -> str:
    """Уникальный (в паре с create_session_dirs) идентификатор сессии: временная метка + 4 hex-символа
    из os.urandom(2). Секундной метки одной было бы недостаточно (два старта в одну секунду дали бы
    один sid) — суффикс резко снижает частоту коллизии, а контрактную уникальность даёт retry
    в create_session_dirs, не сам по себе случайный суффикс."""
    import time

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    suffix = os.urandom(2).hex()
    return f"{timestamp}_{suffix}"


def frame_added_time(path: str) -> float:
    """Когда файл появился в папке: время создания (на Windows — момент копирования/записи), а не
    время изменения — скрин, который пользователь скопировал в очередь, считается добавленным сейчас."""
    st = os.stat(path)
    return getattr(st, "st_birthtime", None) or st.st_ctime


def list_queue(directory: str) -> list:
    """Полные пути изображений очереди (включая подпапки), старые первыми по времени добавления.
    `.tmp` и прочее, что не картинка, в очередь не попадает."""
    found = []
    if not os.path.isdir(directory):
        return found
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                path = os.path.join(root, name)
                try:
                    found.append((frame_added_time(path), path))
                except OSError:
                    continue           # файл исчез между листингом и stat — гонка с другим удалением
    found.sort()
    return [path for _t, path in found]


def count_queue(directory: str) -> int:
    return len(list_queue(directory))


def cleanup_expired(sessions_root: str, ttl_sec: float = QUEUE_TTL_SEC, now=None) -> tuple:
    """Удаляет всё старше `ttl_sec` в pending/found/errors и опустевшие старые папки. Корневые папки
    остаются. Папка с ещё свежим файлом не удаляется. Возвращает (удалено файлов, удалено папок)."""
    now = time.time() if now is None else now
    files_removed = dirs_removed = 0
    for sub in _SWEPT_ROOTS:
        base = os.path.join(sessions_root, sub)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base, topdown=False):
            for name in files:
                path = os.path.join(root, name)
                try:
                    if now - frame_added_time(path) > ttl_sec:
                        os.remove(path)
                        files_removed += 1
                except OSError:
                    continue
            if root == base:
                continue
            try:
                if not os.listdir(root) and now - frame_added_time(root) > ttl_sec:
                    os.rmdir(root)
                    dirs_removed += 1
            except OSError:
                continue
    return files_removed, dirs_removed


def save_frame_atomic(frame, final_path: str) -> bool:
    """Этап 1 — безопасная запись кадра. Кодирует в память (cv2.imencode, не привязано к имени файла),
    пишет байты во временный файл БЕЗ '.jpg' в имени (не должен попадать в скан Этапа 2, который
    смотрит только *.jpg), затем атомарно переименовывает в final_path. При любом сбое (encode или
    запись) final_path не появляется вообще — половинчатого кадра не остаётся.

    Возвращает True при успехе, False при любом сбое (encode вернул False/бросил исключение, запись
    в .tmp не удалась)."""
    try:
        ok, encoded = cv2.imencode(".jpg", frame)
    except cv2.error:
        return False
    if not ok:
        return False

    base, _ext = os.path.splitext(final_path)
    tmp_path = base + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(encoded.tobytes())
    except OSError:
        return False

    os.replace(tmp_path, final_path)
    return True


def producer_step(navigator, frame, is_water: bool, pending_dir: str, frame_id: int,
                  name_prefix: str = "") -> None:
    """Одна итерация Этапа 1 (ЗМЕЙКА). Тот же паттерн, что уже работает в 1.0 (`PacmanEngine._run`,
    navigator.py:1006-1040), БЕЗ YOLO — producer только двигается и сохраняет полный кадр, нейросеть
    (Этап 2) читает эти кадры отдельно, фоново, с диска. `navigator` — уже существующий
    `CoastalSnakeNavigator`, не переписывается: вызывается его собственный `step(is_water=, frame=)`.

    Сбой сохранения кадра (диск и т. п.) не останавливает навигацию — движение и запись независимы,
    как и в 1.0 (там сбой записи отдельного кадра тоже не останавливает бота)."""
    navigator.step(is_water=is_water, frame=frame)
    frame_path = os.path.join(pending_dir, f"{name_prefix}{frame_id:06d}.jpg")
    save_frame_atomic(frame, frame_path)


def frame_has_exchange(model, frame, conf: float) -> bool:
    """Этап 2 (YOLO) — тот же вызов, что уже работает в 1.0 (navigator.py:1025-1032):
    imgsz=1280 (золотое правило YOLO FULLSCREEN, CLAUDE.md), наличие — len(r.boxes) > 0.
    Модель не переписывается и не заменяется — только вызывается тем же способом."""
    results = model.predict(frame, conf=conf, imgsz=1280, verbose=False)
    for r in results:
        if len(r.boxes) > 0:
            return True
    return False


def consumer_step(model, conf: float, src_path: str, found_dir: str) -> bool:
    """Одна итерация Этапа 2 — фонового consumer'а, полностью независимого от Этапа 1 (змейка не
    ждёт результат YOLO, поэтому её скорость не зависит от инференса). Читает кадр из `pending`,
    прогоняет через YOLO: нет биржи — кадр удаляется, есть биржа — атомарно переносится в `found`
    под тем же именем. Возвращает True, если кадр перенесён (найдена биржа), False иначе.

    Отсутствующий src_path (гонка с TTL/другим consumer'ом — механизм Части B, не нужен для самой
    работы этой функции) — не сбой, а легитимный пропуск кандидата. **Найдено тестами:** ванильный
    `cv2.imread` на отсутствующем файле молча возвращает `None`, но `ultralytics` (используется этим же
    процессом для YOLO) глобально патчит `cv2.imread` на чтение через `np.fromfile`, которое на
    отсутствующем файле бросает `FileNotFoundError` вместо `None` — оба случая обязаны трактоваться
    одинаково."""
    try:
        frame = cv2.imread(src_path)
    except (FileNotFoundError, OSError):
        return False
    if frame is None:
        return False

    if not frame_has_exchange(model, frame, conf):
        try:
            os.remove(src_path)
        except FileNotFoundError:
            pass
        return False

    dst_path = os.path.join(found_dir, os.path.basename(src_path))
    try:
        os.replace(src_path, dst_path)
    except FileNotFoundError:
        return False
    return True


def scale_crop_box(crop_box, screen_size, frame_shape):
    """Область чтения координат (calibration #13) задана в ЭКРАННЫХ пикселях — для кадра того же
    размера, что экран, это то, что нужно. Скрин другого разрешения (например 1920x1080 при экране
    2560x1440) пересчитывается линейно: раньше область оказывалась за пределами картинки, координаты не
    читались и в РОЙ ничего не попадало. Результат всегда внутри кадра."""
    screen_w, screen_h = screen_size
    frame_h, frame_w = frame_shape[:2]
    x1, y1, x2, y2 = crop_box
    if screen_w > 0 and screen_h > 0:
        kx, ky = frame_w / screen_w, frame_h / screen_h
        x1, x2 = round(x1 * kx), round(x2 * kx)
        y1, y2 = round(y1 * ky), round(y2 * ky)
    x1, x2 = max(0, min(frame_w, x1)), max(0, min(frame_w, x2))
    y1, y2 = max(0, min(frame_h, y1)), max(0, min(frame_h, y2))
    return (x1, y1, x2, y2)


def append_result_journal(sessions_root: str, entry: dict) -> None:
    """Журнал результатов находок `scout_results.jsonl` (по строке на кадр): что нашла нейросеть,
    прочитаны ли координаты, списаны ли ◆, ушло ли в РОЙ, либо текст ошибки. Без него результат обработки
    нигде не виден. Не входит в чистку по TTL. Сбой записи журнала цепочку не ломает."""
    try:
        row = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), **entry}
        with open(os.path.join(sessions_root, "scout_results.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_exchange_coords(frame, crop_box):
    """Этап 3 — координаты. Тонкая обёртка над уже существующим `PositionReader` (navigator.py:30,
    не переписывается и не заменяется). `crop_box` приходит снаружи — источник значения (калибровка
    #13 `exchange_coord_roi`) резолвится вызывающим кодом (GUI, у которого есть `coord_manager` и
    реестр целей), не этим модулем — так же, как `position_crop_box` уже специфицирован параметром
    конструктора движка в Части A (файл 14, §4.4), а не вычисляется внутри него.

    Возвращает (x, y) или None, если OCR не смог прочитать координаты (C-12 — это не сбой, просто
    находка без координат)."""
    from navigator import PositionReader

    reader = PositionReader(crop_box=crop_box)
    return reader.read(frame)


_KXY_PATTERN = re.compile(r'K\s*[:.]?\s*(\d+)\s+X\s*[:.]?\s*(\d+)\s+Y\s*[:.]?\s*(\d+)', re.IGNORECASE)


def read_exchange_position(frame, crop_box):
    """То же ОДНО распознавание, что и раньше (`PositionReader`, первая попытка, давшая результат), но
    шаблон требует ВСЕ ТРИ числа: панель показывает `K: 233  X: 898  Y: 548`, королевство берётся с
    экрана (а не из настроек — иначе экран с другим королевством ушёл бы на сайт под чужим номером).
    Возвращает (K, X, Y) либо None, если все три числа не прочитались."""
    from navigator import PositionReader

    reader = PositionReader(crop_box=crop_box)

    def _parse(text):
        m = _KXY_PATTERN.search(text)
        if not m:
            return None
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    reader._parse_ocr = _parse
    return reader.read(frame)


def panel_crop_image(frame, crop_box, margin: int = 4):
    """Вырезка панели координат — ровно та область, из которой читался текст (с небольшим полем),
    не выходит за кадр. Уходит в debug-Telegram рядом с распознанными цифрами."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = crop_box
    x1, y1 = max(0, x1 - margin), max(0, y1 - margin)
    x2, y2 = min(w, x2 + margin), min(h, y2 + margin)
    return frame[y1:y2, x1:x2].copy()


def process_found_frame(frame, crop_box, kingdom: int, hunt_type: str, spend_fn, roy_client,
                        publish: bool = True) -> dict:
    """Этап 3 — склейка: OCR → существующий механизм списания → существующий RoyClient. Ни списание,
    ни публикация не переизобретаются — `spend_fn`/`roy_client` инжектируются вызывающим кодом (сейчас
    это `auth.spend_credit` и `roy.roy_client.RoyClient`, уже реализованы и работают в 1.0/проде).

    Порядок по контракту Части A/A-М: списание происходит ВСЕГДА (цена не зависит от результата OCR,
    C-17 монетизации), публикация — только если списание подтверждено успешным И координаты прочитаны
    (P-01, спека №1)."""
    position = read_exchange_position(frame, crop_box)
    coords_ok = position is not None
    found_kingdom, x, y = position if coords_ok else (None, None, None)

    spend_result = spend_fn(hunt_type)
    charged = bool(spend_result and spend_result.get("success"))

    published = False
    if publish and charged and coords_ok:
        published = bool(roy_client.report_scout_find(kingdom=found_kingdom, x=x, y=y))

    return {"coords_ok": coords_ok, "kingdom": found_kingdom, "x": x, "y": y,
            "charged": charged, "published": published}


class ExchangeScoutEngine:
    """Собирает Этапы 1 (ЗМЕЙКА) и 2 (фоновый YOLO) в реальные потоки — тот же паттерн, что уже
    работает в 1.0 (`PacmanEngine`, `navigator.py:988-1000`): producer двигается и пишет кадры,
    consumer фоново читает их и гоняет YOLO, не дожидаясь друг друга. `navigator` — уже существующий
    `CoastalSnakeNavigator`, `model` — уже существующая YOLO-модель (`engine.py`) — ни то, ни другое
    не переписывается.

    Очередь — ОДНА папка `pending/` на всё приложение (решение владельца 2026-09-21): кадры всех
    запусков и скрины, которые пользователь кладёт руками, лежат вместе и разбираются по времени
    добавления. Нейросеть (consumer) одна и не зависит от змейки; змейка (producer) сама встаёт на
    паузу, когда очередь дошла до `pause_threshold`, и продолжает при спаде до 10% ИЛИ через `pause_seconds`
    (игра без движения 4+ минут уходит в режим рекламы).

    `capture_fn` — источник кадров (в проде — `mss.grab` + перевод в BGR, инжектируется параметром,
    чтобы этот класс не был завязан на конкретное железо и был тестируем без экрана)."""

    JOIN_TIMEOUT = 3.0  # то же число, что уже принято в проекте для сопоставимого цикла (PacmanEngine)
    NATURAL_CYCLE_WINDOW = 20  # замеров в медиане естественного цикла

    def __init__(self, navigator, capture_fn, model, conf: float, sessions_root: str,
                 move_wait: float = 0.5, on_found_callback=None, speed_factor: float = 1.0,
                 pause_threshold: int = SCOUT_QUEUE_PAUSE_THRESHOLD,
                 pause_seconds: float = SCOUT_PAUSE_MINUTES * 60,
                 ttl_sec: float = QUEUE_TTL_SEC):
        self.navigator = navigator
        self.capture_fn = capture_fn
        self.model = model
        self.conf = conf
        self.sessions_root = sessions_root
        self.move_wait = move_wait
        # Скорость змейки как множитель от минимального цикла ЭТОГО ПК (решение владельца
        # 2026-09-21): 1.0 — без паузы, 4.0 — цикл в четыре раза длиннее минимального.
        self.speed_factor = speed_factor
        self.pause_threshold = pause_threshold
        self.pause_seconds = pause_seconds
        self._pause_until = 0.0
        self._run_ceiling = 0   # после запуска по таймеру: до какого размера очереди змейка идёт без паузы
        self.ttl_sec = ttl_sec
        self._cycle_samples = []
        self.on_found_callback = on_found_callback

        self.pending_dir = os.path.join(sessions_root, "pending")
        self.found_dir = os.path.join(sessions_root, "found")
        os.makedirs(self.pending_dir, exist_ok=True)
        os.makedirs(self.found_dir, exist_ok=True)

        self.is_running = False
        self.paused_by_queue = False
        self.producer_error = None      # текст ошибки, если поток змейки умер; None — всё в порядке
        self.sid = None
        self._producer_thread = None
        self._consumer_thread = None
        self._consumer_stop_event = None
        self._nn_user_stopped = False
        self._frame_counter = 0

    @property
    def natural_cycle(self) -> float:
        """Естественный цикл змейки на этом ПК, с: медиана последних замеров «захват + шаг + запись
        кадра» без паузы. 0.0 — ещё не измерен."""
        samples = self._cycle_samples
        if not samples:
            return 0.0
        ordered = sorted(samples)
        return ordered[len(ordered) // 2]

    def _speed_pause(self) -> float:
        return self.move_wait + max(0.0, self.speed_factor - 1.0) * self.natural_cycle

    def queue_size(self) -> int:
        """Число кадров в единой очереди (включая скрины, положенные вручную) — источник прогресс-бара."""
        return count_queue(self.pending_dir)

    # ── змейка (producer) ────────────────────────────────────────────────────────────────────────
    def start(self) -> None:
        """Запускает змейку. C-04: повторный start() без stop() — RuntimeError. Очередь не сбрасывается;
        нейросеть поднимается вместе со змейкой, если её не остановили кнопкой."""
        if self.is_running:
            raise RuntimeError("ExchangeScoutEngine уже запущен — сначала stop()")

        cleanup_expired(self.sessions_root, self.ttl_sec)
        self.sid = generate_session_id()
        self._frame_counter = 0
        self._cycle_samples = []
        self.paused_by_queue = False
        self.producer_error = None
        self.is_running = True

        self._producer_thread = threading.Thread(target=self._producer_loop, daemon=True)
        self._producer_thread.start()
        if not self._nn_user_stopped and not self.consumer_alive:
            self._spawn_consumer()

    def stop(self) -> None:
        """C-05: bounded join ТОЛЬКО на producer-треде (только он двигает джойстик/мышь). Consumer НЕ
        останавливается — он дообрабатывает очередь и сам завершается, когда она опустеет (инвариант
        конвейера — ESC/Стоп не отменяют уже захваченные кадры)."""
        self.is_running = False
        if self._producer_thread is not None:
            self._producer_thread.join(timeout=self.JOIN_TIMEOUT)

    @property
    def resume_threshold(self) -> int:
        """Порог раннего продолжения: 10% текущего лимита (300 -> 30, 600 -> 60, 999 -> 99)."""
        return self.pause_threshold // 10

    def _wait_for_queue_room(self) -> None:
        """Автопауза. Очередь дошла до лимита — змейка стоит (состояние навигатора сохраняется, цикл
        нырок→сдвиг→возврат→сдвиг не рвётся) и продолжает по ЛЮБОМУ из двух условий, что наступит раньше:
        очередь спала до 10% лимита ИЛИ прошло `pause_seconds` (игра без движения 4+ минут уходит в режим
        рекламы). После запуска по таймеру змейка работает, а не делает один шаг: снова пауза, только когда
        очередь вырастет до лимита (если она и так полна — ещё на 10% лимита)."""
        size = self.queue_size()
        if size < self.pause_threshold:
            self._run_ceiling = 0
            return
        if self._run_ceiling and size < self._run_ceiling:
            return                                   # идёт «окно движения» после запуска по таймеру
        self.paused_by_queue = True
        self._pause_until = time.monotonic() + self.pause_seconds
        drained = False
        while self.is_running and time.monotonic() < self._pause_until:
            if self.queue_size() <= self.resume_threshold:
                drained = True
                break
            time.sleep(0.2)
        self.paused_by_queue = False
        self._pause_until = 0.0
        if self.is_running and not drained:
            self._run_ceiling = self.queue_size() + max(1, self.pause_threshold // 10)
        else:
            self._run_ceiling = 0

    def pause_remaining(self) -> float:
        """Сколько секунд осталось до конца паузы (0.0 — змейка не на паузе)."""
        if not self.paused_by_queue:
            return 0.0
        return max(0.0, self._pause_until - time.monotonic())

    def _producer_loop(self) -> None:
        try:
            while self.is_running:
                self._wait_for_queue_room()
                if not self.is_running:
                    break
                t0 = time.monotonic()
                frame = self.capture_fn()
                from navigator import is_water_center_screen
                is_water = is_water_center_screen(frame)
                self._frame_counter += 1
                producer_step(self.navigator, frame, is_water, self.pending_dir, self._frame_counter,
                              name_prefix=f"{self.sid}_")
                self._cycle_samples.append(time.monotonic() - t0)
                del self._cycle_samples[:-self.NATURAL_CYCLE_WINDOW]
                time.sleep(self._speed_pause())
        except Exception as e:
            # Раньше исключение молча убивало поток, а GUI продолжал показывать «работает».
            import traceback
            traceback.print_exc()
            self.producer_error = f"{type(e).__name__}: {e}"
            self.is_running = False
        finally:
            self.paused_by_queue = False

    # ── нейросеть (consumer) ─────────────────────────────────────────────────────────────────────
    def _spawn_consumer(self) -> None:
        stop_event = threading.Event()
        self._consumer_stop_event = stop_event
        self._consumer_thread = threading.Thread(target=self._consumer_loop, args=(stop_event,),
                                                 daemon=True)
        self._consumer_thread.start()

    @property
    def consumer_alive(self) -> bool:
        """Нейросеть работает (с точки зрения пользователя): поток жив и её не остановили кнопкой."""
        return (self._consumer_thread is not None and self._consumer_thread.is_alive()
                and not (self._consumer_stop_event is not None and self._consumer_stop_event.is_set()))

    def stop_consumer(self) -> None:
        """Кнопка «остановить нейросеть» (решение владельца 2026-09-18): consumer заканчивает кадр, с
        которым работает, и останавливается; кадры остаются в очереди, змейка продолжает работать;
        запуск змейки нейросеть сам не поднимает, пока её не запустят кнопкой."""
        self._nn_user_stopped = True
        if self._consumer_stop_event is not None:
            self._consumer_stop_event.set()

    def start_consumer(self) -> None:
        """Кнопка «запустить нейросеть»: работает и без змейки (разбор скринов, положенных вручную).
        Обработав очередь до конца (и если змейка стоит), сама останавливается."""
        self._nn_user_stopped = False
        if self.consumer_alive:
            return
        old = self._consumer_thread
        if old is not None and old.is_alive():
            old.join(timeout=self.JOIN_TIMEOUT)   # предыдущий доделывает кадр после stop_consumer()
        cleanup_expired(self.sessions_root, self.ttl_sec)
        self._spawn_consumer()

    def _producing(self) -> bool:
        return self._producer_thread is not None and self._producer_thread.is_alive()

    def _consumer_loop(self, stop_event) -> None:
        while not stop_event.is_set():
            # Порядок важен: сначала «змейка ещё пишет?», потом листинг. Если змейка уже мертва, листинг
            # окончательный; если наоборот — кадр, дописанный после stop(), остался бы в очереди.
            producing = self._producing()
            queue = list_queue(self.pending_dir)
            if not queue:
                if not producing:
                    break
                time.sleep(0.05)
                continue
            src = queue[0]
            try:
                expired = time.time() - frame_added_time(src) > self.ttl_sec
            except OSError:
                continue
            if expired:      # устаревший кадр в нейросеть не идёт, просто удаляется
                try:
                    os.remove(src)
                except OSError:
                    pass
                continue
            was_found = consumer_step(self.model, self.conf, src, self.found_dir)
            if was_found and self.on_found_callback:
                found_path = os.path.join(self.found_dir, os.path.basename(src))
                frame = cv2.imread(found_path)
                if frame is not None:
                    # Исключение в обработчике (OCR, списание, сеть) не должно молча убивать нейросеть —
                    # результат или ошибка каждого кадра пишутся в журнал.
                    try:
                        result = self.on_found_callback(frame, found_path)
                        entry = dict(result) if isinstance(result, dict) else {}
                    except Exception as e:
                        entry = {"error": f"{type(e).__name__}: {e}"}
                    append_result_journal(self.sessions_root,
                                          {"file": os.path.basename(src), **entry})


def make_found_handler(crop_box, kingdom: int, hunt_type: str, hwid: str,
                        spend_fn=None, roy_client=None, screen_size=None, on_sound=None, on_result=None,
                        on_debug_frame=None, on_debug_result=None, on_debug_crop=None, publish_fn=None):
    """Единственная точка, где Этап 3 подключается к Этапам 1+2 — собирает `on_found_callback`
    для `ExchangeScoutEngine`. По умолчанию использует уже существующие, реальные `auth.spend_credit`
    и `roy.roy_client.RoyClient` (не новые) — `spend_fn`/`roy_client` можно переопределить только
    для тестов.

    Порядок на находке: звуковой сигнал (сразу, сбой звука цепочку не ломает) -> область координат
    пересчитывается под размер кадра -> OCR -> списание -> публикация -> `on_result(kingdom, result)`
    (GUI: карточка «последняя биржа», защита РОЙ от собственного звука). `on_debug_frame(frame)` —
    кадр находки уходит в debug-Telegram сразу, параллельно с обработкой; `on_debug_result(file, result)` —
    результат отдельным сообщением. Оба необязательны, их сбои цепочку не ломают."""
    if spend_fn is None:
        from auth import spend_credit
        spend_fn = spend_credit
    if roy_client is None:
        from roy.roy_client import RoyClient
        roy_client = RoyClient(hwid)
    if screen_size is None:
        import pyautogui
        screen_size = tuple(pyautogui.size())

    def _on_found(frame, found_path):
        if on_sound is not None:
            try:
                on_sound()
            except Exception:
                pass
        if on_debug_frame is not None:
            try:
                on_debug_frame(frame)
            except Exception:
                pass
        crop = scale_crop_box(crop_box, screen_size, frame.shape)
        publish = True if publish_fn is None else bool(publish_fn())
        result = process_found_frame(frame, crop, kingdom, hunt_type, spend_fn, roy_client, publish=publish)
        if on_debug_crop is not None:
            try:
                on_debug_crop(panel_crop_image(frame, crop))
            except Exception:
                pass
        if on_debug_result is not None:
            try:
                on_debug_result(os.path.basename(found_path), result)
            except Exception:
                pass
        if on_result is not None:
            try:
                on_result(result.get("kingdom") or kingdom, result)
            except Exception:
                pass
        return result

    return _on_found
