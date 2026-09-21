"""
TDD: Биржа 2.0 — три этапа (решение владельца 2026-09-21, сессия #147):
  Этап 1 (ЗМЕЙКА) — навигация + полные screenshots → pending/<sid>/*.jpg
  Этап 2 (ФОНОВЫЙ YOLO) — pending → YOLO → found (только кадры с биржей)
  Этап 3 (КООРДИНАТЫ) — found → ROI #13 → OCR → X/Y → spend_credit → RoyClient

Этот файл начинается с Этапа 1: структура сессии (C-01) и безопасная атомарная запись кадра
(cv2.imencode → .tmp → os.replace — внутренний механизм надёжности Этапа 1, не отдельный продуктовый
слой: без него consumer на Этапе 2 может прочитать недописанный JPEG).
"""
import os
import re

from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from exchange_scout import (
    generate_session_id,
    create_session_dirs,
    save_frame_atomic,
    producer_step,
    SESSION_ID_RE,
)


class TestGenerateSessionId:
    """C-01: sid = YYYY-MM-DD_HH-MM-SS + 4 hex-символа."""

    def test_format_matches_contract(self):
        sid = generate_session_id()
        assert SESSION_ID_RE.match(sid), f"{sid!r} не соответствует формату C-01"

    def test_hex_suffix_is_4_chars(self):
        sid = generate_session_id()
        suffix = sid.rsplit("_", 1)[-1]
        assert len(suffix) == 4
        int(suffix, 16)  # не бросает — валидный hex

    def test_successive_calls_produce_different_suffixes_with_high_probability(self):
        """Не гарантия уникальности (это даёт create_session_dirs с retry) — просто здравая
        проверка, что суффикс не захардкожен/константа."""
        sids = {generate_session_id() for _ in range(20)}
        assert len(sids) > 1


class TestCreateSessionDirs:
    """C-01/C-04 шаг 2: pending/<sid>/, found/<sid>/, errors/<sid>/ — уникальность гарантируется
    retry на FileExistsError, не только случайностью суффикса."""

    def test_creates_all_three_branches(self, tmp_path):
        sid = create_session_dirs(str(tmp_path))
        assert os.path.isdir(os.path.join(tmp_path, "pending", sid))
        assert os.path.isdir(os.path.join(tmp_path, "found", sid))
        assert os.path.isdir(os.path.join(tmp_path, "errors", sid))

    def test_does_not_touch_existing_pending_content(self, tmp_path):
        """C-02: pending/ не очищается — существующие файлы других сессий не трогаются."""
        old_sid_dir = tmp_path / "pending" / "2020-01-01_00-00-00_dead"
        old_sid_dir.mkdir(parents=True)
        marker = old_sid_dir / "000001.jpg"
        marker.write_bytes(b"old frame")

        create_session_dirs(str(tmp_path))

        assert marker.exists()
        assert marker.read_bytes() == b"old frame"

    def test_retries_on_sid_collision(self, tmp_path, monkeypatch):
        """C-01: 'уникален контрактно, не только вероятностно' — os.makedirs(exist_ok=False) +
        retry на FileExistsError, не просто полагается на случайный суффикс."""
        calls = {"n": 0}
        fixed_sid = "2026-01-01_00-00-00_aaaa"
        second_sid = "2026-01-01_00-00-00_bbbb"

        def fake_generate():
            calls["n"] += 1
            return fixed_sid if calls["n"] == 1 else second_sid

        monkeypatch.setattr("exchange_scout.generate_session_id", fake_generate)

        # Первый вызов сам "занимает" fixed_sid извне — эмулирует коллизию.
        os.makedirs(os.path.join(tmp_path, "pending", fixed_sid))

        sid = create_session_dirs(str(tmp_path))

        assert sid == second_sid, "должен был повторить попытку с новым sid после коллизии"
        assert os.path.isdir(os.path.join(tmp_path, "found", second_sid))

    def test_two_calls_never_collide_in_practice(self, tmp_path):
        """Не строгое доказательство (то даёт retry-тест выше), но живая проверка на реальном
        os.urandom — 50 последовательных сессий не должны столкнуться."""
        sids = {create_session_dirs(str(tmp_path)) for _ in range(50)}
        assert len(sids) == 50


class TestSaveFrameAtomic:
    """Этап 1 — безопасная запись кадра: encode в память → запись в .tmp → os.replace в .jpg.
    Гонка, которую это закрывает: если бы producer писал сразу в `NNNNNN.jpg`, Этап 2 (YOLO consumer,
    сканирует ту же папку) мог бы прочитать недописанный файл (найдено ревью владельца в этой же сессии,
    Design 44 §4.1.2 — тот же механизм, просто без Части B вокруг него)."""

    def _frame(self):
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def test_writes_readable_jpg_at_final_path(self, tmp_path):
        final_path = tmp_path / "000001.jpg"
        save_frame_atomic(self._frame(), str(final_path))

        assert final_path.exists()
        img = cv2.imread(str(final_path))
        assert img is not None
        assert img.shape == (10, 10, 3)

    def test_no_tmp_file_left_after_success(self, tmp_path):
        final_path = tmp_path / "000001.jpg"
        save_frame_atomic(self._frame(), str(final_path))

        leftovers = [p for p in os.listdir(tmp_path) if p != "000001.jpg"]
        assert leftovers == []

    def test_tmp_file_never_has_jpg_in_name(self, tmp_path, monkeypatch):
        """Consumer (Этап 2) сканирует `*.jpg` — временное имя обязано не попадать в этот скан ни на
        каком шаге, не полагаясь на скорость записи."""
        final_path = tmp_path / "000001.jpg"
        seen_names = []

        real_replace = os.replace

        def spy_replace(src, dst):
            seen_names.append(os.path.basename(src))
            return real_replace(src, dst)

        monkeypatch.setattr("exchange_scout.os.replace", spy_replace)
        save_frame_atomic(self._frame(), str(final_path))

        assert len(seen_names) == 1
        assert ".jpg" not in seen_names[0]

    def test_returns_false_and_writes_nothing_on_encode_failure(self, tmp_path, monkeypatch):
        """Если imencode не смог закодировать — final .jpg не появляется вообще, .tmp тоже не
        создаётся (контракт из Design 44 §4.1.2 — не оставлять полу-кадр)."""
        final_path = tmp_path / "000001.jpg"
        monkeypatch.setattr("exchange_scout.cv2.imencode", lambda ext, frame: (False, None))

        ok = save_frame_atomic(self._frame(), str(final_path))

        assert ok is False
        assert not final_path.exists()
        assert os.listdir(tmp_path) == []

    def test_returns_false_on_encode_exception(self, tmp_path, monkeypatch):
        final_path = tmp_path / "000001.jpg"

        def boom(ext, frame):
            raise cv2.error("boom")

        monkeypatch.setattr("exchange_scout.cv2.imencode", boom)

        ok = save_frame_atomic(self._frame(), str(final_path))

        assert ok is False
        assert not final_path.exists()


class TestProducerStep:
    """Этап 1 — одна итерация producer'а: тот же паттерн, что уже работает в 1.0
    (`PacmanEngine._run`, navigator.py:1006-1040), БЕЗ YOLO (это отдельный Этап 2 — producer не должен
    вызывать нейросеть вообще, только двигаться и сохранять кадр). Навигатор и определение воды
    инжектируются — единственный переиспользуемый компонент, `CoastalSnakeNavigator`, не переписывается
    (`step(is_water=..., frame=...)`, уже существующая сигнатура, navigator.py:808)."""

    def _frame(self):
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def test_calls_navigator_step_with_frame_and_water_flag(self, tmp_path):
        navigator = MagicMock()
        frame = self._frame()

        producer_step(navigator, frame, is_water=True, pending_dir=str(tmp_path), frame_id=1)

        navigator.step.assert_called_once_with(is_water=True, frame=frame)

    def test_saves_frame_to_pending_dir_with_six_digit_name(self, tmp_path):
        navigator = MagicMock()
        producer_step(navigator, self._frame(), is_water=False, pending_dir=str(tmp_path), frame_id=7)

        saved = tmp_path / "000007.jpg"
        assert saved.exists()
        assert cv2.imread(str(saved)) is not None

    def test_does_not_call_yolo_or_anything_else_on_navigator(self, tmp_path):
        """Producer вызывает ровно один метод навигатора — step(). Ничего похожего на YOLO/predict
        не должно вызываться отсюда — это Этап 2, отдельный фоновый consumer."""
        navigator = MagicMock()
        producer_step(navigator, self._frame(), is_water=True, pending_dir=str(tmp_path), frame_id=1)

        assert len(navigator.method_calls) == 1
        assert navigator.method_calls[0][0] == "step"

    def test_frame_save_failure_does_not_crash_step(self, tmp_path, monkeypatch):
        """Если запись кадра не удалась (диск и т.п.) — producer_step не должен падать; навигация
        (движение) не зависит от того, удалось ли сохранить именно этот кадр."""
        navigator = MagicMock()
        monkeypatch.setattr("exchange_scout.save_frame_atomic", lambda frame, path: False)

        # Не должно бросить исключение.
        producer_step(navigator, self._frame(), is_water=True, pending_dir=str(tmp_path), frame_id=1)
        navigator.step.assert_called_once()
