"""
exchange_scout.py — Биржа 2.0 (Exchange Scout).

Три этапа (решение владельца 2026-09-21, сессия #147):
  1. ЗМЕЙКА    — навигация по карте + полные screenshots → pending/<sid>/*.jpg
  2. YOLO      — фоновый consumer: pending → YOLO → found (только кадры с биржей)
  3. КООРДИНАТЫ — found → ROI #13 (exchange_coord_roi) → OCR → X/Y → spend_credit → RoyClient

Этот файл реализуется поэтапно, TDD. Текущее состояние — Этап 1: структура сессии (уникальный sid,
подпапки) и атомарная запись кадра (cv2.imencode → .tmp → os.replace) — внутренний механизм надёжности
Этапа 1, чтобы Этап 2 никогда не читал недописанный JPEG.
"""
import os
import re

import cv2

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


def create_session_dirs(sessions_root: str) -> str:
    """Резервирует уникальный sid и создаёт pending/<sid>/, found/<sid>/, errors/<sid>/ под указанным
    корнем. Не трогает существующее содержимое pending/ (никакого rmtree/очистки чужих сессий).
    Уникальность sid гарантируется retry на FileExistsError — не только случайностью суффикса."""
    pending_root = os.path.join(sessions_root, "pending")
    while True:
        sid = generate_session_id()
        try:
            os.makedirs(os.path.join(pending_root, sid), exist_ok=False)
            break
        except FileExistsError:
            continue

    os.makedirs(os.path.join(sessions_root, "found", sid), exist_ok=True)
    os.makedirs(os.path.join(sessions_root, "errors", sid), exist_ok=True)
    return sid


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


def producer_step(navigator, frame, is_water: bool, pending_dir: str, frame_id: int) -> None:
    """Одна итерация Этапа 1 (ЗМЕЙКА). Тот же паттерн, что уже работает в 1.0 (`PacmanEngine._run`,
    navigator.py:1006-1040), БЕЗ YOLO — producer только двигается и сохраняет полный кадр, нейросеть
    (Этап 2) читает эти кадры отдельно, фоново, с диска. `navigator` — уже существующий
    `CoastalSnakeNavigator`, не переписывается: вызывается его собственный `step(is_water=, frame=)`.

    Сбой сохранения кадра (диск и т. п.) не останавливает навигацию — движение и запись независимы,
    как и в 1.0 (там сбой записи отдельного кадра тоже не останавливает бота)."""
    navigator.step(is_water=is_water, frame=frame)
    frame_path = os.path.join(pending_dir, f"{frame_id:06d}.jpg")
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


def process_found_frame(frame, crop_box, kingdom: int, hunt_type: str, spend_fn, roy_client) -> dict:
    """Этап 3 — склейка: OCR → существующий механизм списания → существующий RoyClient. Ни списание,
    ни публикация не переизобретаются — `spend_fn`/`roy_client` инжектируются вызывающим кодом (сейчас
    это `auth.spend_credit` и `roy.roy_client.RoyClient`, уже реализованы и работают в 1.0/проде).

    Порядок по контракту Части A/A-М: списание происходит ВСЕГДА (цена не зависит от результата OCR,
    C-17 монетизации), публикация — только если списание подтверждено успешным И координаты прочитаны
    (P-01, спека №1)."""
    coords = read_exchange_coords(frame, crop_box)
    coords_ok = coords is not None
    x, y = coords if coords_ok else (None, None)

    spend_result = spend_fn(hunt_type)
    charged = bool(spend_result and spend_result.get("success"))

    published = False
    if charged and coords_ok:
        published = bool(roy_client.report_scout_find(kingdom=kingdom, x=x, y=y))

    return {"coords_ok": coords_ok, "x": x, "y": y, "charged": charged, "published": published}
