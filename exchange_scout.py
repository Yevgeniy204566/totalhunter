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
