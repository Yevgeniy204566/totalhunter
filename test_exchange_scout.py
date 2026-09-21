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
import time
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from exchange_scout import (
    generate_session_id,
    save_frame_atomic,
    producer_step,
    frame_has_exchange,
    consumer_step,
    read_exchange_coords,
    process_found_frame,
    ExchangeScoutEngine,
    make_found_handler,
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


def _boxes(n):
    """Фейковый результат YOLO .predict() — только то, что читает frame_has_exchange
    (len(r.boxes) > 0), точная форма как в navigator.py:1028-1032."""
    result = MagicMock()
    result.boxes = [MagicMock() for _ in range(n)]
    return [result]


class TestFrameHasExchange:
    """Этап 2 — фильтр YOLO. Тот же вызов, что уже работает в 1.0 (navigator.py:1025-1032):
    `model.predict(frame, conf=conf, imgsz=1280, verbose=False)`, наличие — `len(r.boxes) > 0`.
    Модель не переписывается и не заменяется — только вызывается тем же способом."""

    def _frame(self):
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def test_true_when_boxes_found(self):
        model = MagicMock()
        model.predict.return_value = _boxes(1)

        assert frame_has_exchange(model, self._frame(), conf=0.8) is True

    def test_false_when_no_boxes(self):
        model = MagicMock()
        model.predict.return_value = _boxes(0)

        assert frame_has_exchange(model, self._frame(), conf=0.8) is False

    def test_calls_predict_with_same_parameters_as_1_0(self):
        """imgsz=1280 — золотое правило YOLO FULLSCREEN (CLAUDE.md), verbose=False как в 1.0."""
        model = MagicMock()
        model.predict.return_value = _boxes(0)
        frame = self._frame()

        frame_has_exchange(model, frame, conf=0.77)

        model.predict.assert_called_once_with(frame, conf=0.77, imgsz=1280, verbose=False)


class TestConsumerStep:
    """Этап 2 — одна итерация фонового consumer'а: читает кадр из pending, гоняет YOLO, либо удаляет
    (нет биржи), либо переносит в found (есть биржа). Работает независимо от Этапа 1 (змейка не ждёт
    результат) — это и есть «разнести змейку от нейросети», ничего сверх этого сейчас не нужно."""

    def _write_frame(self, path):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", frame)
        assert ok
        with open(path, "wb") as f:
            f.write(encoded.tobytes())
        return frame

    def test_removes_frame_when_no_exchange(self, tmp_path):
        pending_dir = tmp_path / "pending"
        found_dir = tmp_path / "found"
        pending_dir.mkdir()
        found_dir.mkdir()
        src = pending_dir / "000001.jpg"
        self._write_frame(src)

        model = MagicMock()
        model.predict.return_value = _boxes(0)

        result = consumer_step(model, conf=0.8, src_path=str(src), found_dir=str(found_dir))

        assert result is False
        assert not src.exists()
        assert list(found_dir.iterdir()) == []

    def test_moves_frame_to_found_when_exchange_present(self, tmp_path):
        pending_dir = tmp_path / "pending"
        found_dir = tmp_path / "found"
        pending_dir.mkdir()
        found_dir.mkdir()
        src = pending_dir / "000002.jpg"
        self._write_frame(src)

        model = MagicMock()
        model.predict.return_value = _boxes(1)

        result = consumer_step(model, conf=0.8, src_path=str(src), found_dir=str(found_dir))

        assert result is True
        assert not src.exists()
        moved = found_dir / "000002.jpg"
        assert moved.exists()

    def test_missing_source_file_is_not_an_error(self, tmp_path):
        """Гонка с другим consumer'ом/TTL (Часть B) — файл мог уже исчезнуть до чтения. Это легитимный
        случай, не крах: consumer просто пропускает кандидата."""
        pending_dir = tmp_path / "pending"
        found_dir = tmp_path / "found"
        pending_dir.mkdir()
        found_dir.mkdir()
        src = pending_dir / "000003.jpg"  # никогда не создавался

        model = MagicMock()

        result = consumer_step(model, conf=0.8, src_path=str(src), found_dir=str(found_dir))

        assert result is False
        model.predict.assert_not_called()


class TestReadExchangeCoords:
    """Этап 3 — координаты. Тонкая обёртка над уже существующим `PositionReader` (navigator.py:30,
    не переписывается) — единственное, что меняется относительно старого использования: `crop_box`
    приходит СНАРУЖИ (параметр), а не хардкодится литералом внутри. Источник значения — калибровка #13
    `exchange_coord_roi` (main.py), резолвится вызывающим кодом (GUI), не этим модулем — избегает
    циклического импорта exchange_scout↔main и совпадает с уже принятым контрактом Части A
    (`position_crop_box` — параметр конструктора движка, файл 14 §4.4)."""

    def test_delegates_to_position_reader_with_given_crop_box(self, monkeypatch):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        crop_box = (10, 20, 310, 110)
        captured = {}

        class FakePositionReader:
            def __init__(self, crop_box):
                captured["crop_box"] = crop_box

            def read(self, screenshot_np):
                captured["frame"] = screenshot_np
                return (512, 318)

        monkeypatch.setattr("navigator.PositionReader", FakePositionReader)

        result = read_exchange_coords(frame, crop_box)

        assert result == (512, 318)
        assert captured["crop_box"] == crop_box
        assert captured["frame"] is frame

    def test_returns_none_when_ocr_fails(self, monkeypatch):
        """C-12 (Часть A): провал OCR не должен бросать исключение — вызывающий код (журнал) сам
        решает, что делать с `coords_ok=False`."""
        class FakePositionReader:
            def __init__(self, crop_box):
                pass

            def read(self, screenshot_np):
                return None

        monkeypatch.setattr("navigator.PositionReader", FakePositionReader)

        result = read_exchange_coords(np.zeros((5, 5, 3), dtype=np.uint8), (0, 0, 5, 5))

        assert result is None


class TestProcessFoundFrame:
    """Этап 3 — склейка: OCR → существующий spend_credit (уже реализован, auth.py:106, только
    вызывается) → существующий RoyClient.report_scout_find (уже реализован и живёт в проде,
    roy/roy_client.py). Обе внешние функции инжектируются параметрами — эта функция не решает,
    какой hunt_type использовать (ждёт решения владельца), только описывает порядок вызовов.

    Порядок по контракту Части A/A-М (C-03, C-12, P-01): OCR → списание (всегда, независимо от
    OCR) → публикация (только если списание успешно И OCR успешен)."""

    def _frame(self):
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def test_publishes_when_charged_and_coords_ok(self, monkeypatch):
        monkeypatch.setattr(
            "exchange_scout.read_exchange_position", lambda frame, crop_box: (7, 512, 318)
        )
        spend_fn = MagicMock(return_value={"success": True, "credits": 90})
        roy_client = MagicMock()
        roy_client.report_scout_find.return_value = True

        result = process_found_frame(
            self._frame(), crop_box=(0, 0, 5, 5), kingdom=7,
            hunt_type="exchange", spend_fn=spend_fn, roy_client=roy_client,
        )

        spend_fn.assert_called_once_with("exchange")
        roy_client.report_scout_find.assert_called_once_with(kingdom=7, x=512, y=318)
        assert result == {"coords_ok": True, "kingdom": 7, "x": 512, "y": 318, "charged": True,
                          "published": True}

    def test_does_not_publish_when_ocr_fails(self, monkeypatch):
        """C-12: провал OCR не теряет находку (списание всё равно происходит — цена не зависит от
        coords_ok, монетизация спека С-17), но публикации быть не должно (P-01)."""
        monkeypatch.setattr("exchange_scout.read_exchange_position", lambda frame, crop_box: None)
        spend_fn = MagicMock(return_value={"success": True, "credits": 90})
        roy_client = MagicMock()

        result = process_found_frame(
            self._frame(), crop_box=(0, 0, 5, 5), kingdom=7,
            hunt_type="exchange", spend_fn=spend_fn, roy_client=roy_client,
        )

        spend_fn.assert_called_once_with("exchange")
        roy_client.report_scout_find.assert_not_called()
        assert result == {"coords_ok": False, "kingdom": None, "x": None, "y": None, "charged": True,
                          "published": False}

    def test_does_not_publish_when_payment_fails(self, monkeypatch):
        """P-01: даже с успешным OCR публикации не будет, если списание не подтверждено (402/403/
        сетевой сбой и т. п. — spend_fn вернул success!=True)."""
        monkeypatch.setattr(
            "exchange_scout.read_exchange_position", lambda frame, crop_box: (7, 512, 318)
        )
        spend_fn = MagicMock(return_value={"success": False, "low_credits": True})
        roy_client = MagicMock()

        result = process_found_frame(
            self._frame(), crop_box=(0, 0, 5, 5), kingdom=7,
            hunt_type="exchange", spend_fn=spend_fn, roy_client=roy_client,
        )

        roy_client.report_scout_find.assert_not_called()
        assert result == {"coords_ok": True, "kingdom": 7, "x": 512, "y": 318, "charged": False,
                          "published": False}

    def test_kingdom_comes_from_the_screen_when_it_was_read(self, monkeypatch):
        """На панели три числа K/X/Y: публикуется королевство с экрана, а не из настроек РОЙ."""
        monkeypatch.setattr("exchange_scout.read_exchange_position",
                            lambda frame, crop_box: (233, 898, 548))
        spend_fn = MagicMock(return_value={"success": True})
        roy_client = MagicMock()
        roy_client.report_scout_find.return_value = True
        process_found_frame(self._frame(), crop_box=(0, 0, 5, 5), kingdom=7, hunt_type="exchange",
                            spend_fn=spend_fn, roy_client=roy_client)
        roy_client.report_scout_find.assert_called_once_with(kingdom=233, x=898, y=548)

    def test_only_x_y_without_kingdom_is_not_a_reading(self):
        """Нужны все три числа: строка без K не разбирается (иначе королевство пришлось бы гадать)."""
        from exchange_scout import _KXY_PATTERN
        assert _KXY_PATTERN.search("X: 898 Y: 548") is None

    def test_result_is_json_serializable_for_the_journal(self, monkeypatch):
        import json
        monkeypatch.setattr("exchange_scout.read_exchange_position", lambda frame, crop_box: (7, 512, 318))
        result = process_found_frame(self._frame(), crop_box=(0, 0, 5, 5), kingdom=7, hunt_type="exchange",
                                     spend_fn=MagicMock(return_value={"success": True}),
                                     roy_client=MagicMock(**{"report_scout_find.return_value": True}))
        json.dumps(result)


class TestExchangeScoutEngine:
    """Собирает Этапы 1+2 в реальные потоки (тот же паттерн, что уже работает в 1.0 —
    `PacmanEngine`, navigator.py:988-1000): producer двигается и пишет кадры, consumer фоново читает
    их и гоняет YOLO — независимо, без ожидания друг друга. `stop()` — bounded join ТОЛЬКО на
    producer'е (3.0 сек, то же число, что уже принято в проекте для сопоставимого цикла); consumer
    доигрывает то, что уже лежит в pending, и останавливается сам."""

    def _fake_navigator(self):
        return MagicMock()

    def _fake_capture(self, n_frames=5):
        frames = [np.zeros((10, 10, 3), dtype=np.uint8) for _ in range(n_frames)]
        state = {"i": 0}

        def _capture():
            frame = frames[state["i"] % len(frames)]
            state["i"] += 1
            return frame

        return _capture

    def _fake_model_always_finds(self):
        model = MagicMock()
        result = MagicMock()
        result.boxes = [MagicMock()]
        model.predict.return_value = [result]
        return model

    def _fake_model_never_finds(self):
        model = MagicMock()
        result = MagicMock()
        result.boxes = []
        model.predict.return_value = [result]
        return model

    def test_start_creates_session_dirs_and_sets_is_running(self, tmp_path):
        engine = ExchangeScoutEngine(
            navigator=self._fake_navigator(), capture_fn=self._fake_capture(),
            model=self._fake_model_never_finds(), conf=0.8,
            sessions_root=str(tmp_path), move_wait=0.01,
        )
        engine.start()
        try:
            assert engine.is_running is True
            assert os.path.isdir(engine.pending_dir)
            assert os.path.isdir(engine.found_dir)
        finally:
            engine.stop()

    def test_repeated_start_without_stop_raises(self, tmp_path):
        """C-04.7 (Часть A): повторный start() без stop() на том же экземпляре — RuntimeError."""
        engine = ExchangeScoutEngine(
            navigator=self._fake_navigator(), capture_fn=self._fake_capture(),
            model=self._fake_model_never_finds(), conf=0.8,
            sessions_root=str(tmp_path), move_wait=0.01,
        )
        engine.start()
        try:
            with pytest.raises(RuntimeError):
                engine.start()
        finally:
            engine.stop()

    def test_stop_returns_promptly_bounded_by_join_timeout(self, tmp_path):
        engine = ExchangeScoutEngine(
            navigator=self._fake_navigator(), capture_fn=self._fake_capture(),
            model=self._fake_model_never_finds(), conf=0.8,
            sessions_root=str(tmp_path), move_wait=0.01,
        )
        engine.start()
        time.sleep(0.05)
        t0 = time.time()
        engine.stop()
        elapsed = time.time() - t0
        assert elapsed < 3.5, "stop() обязан вернуться в пределах bounded join (3.0 сек) + запас"

    def test_end_to_end_frame_with_exchange_ends_up_in_found(self, tmp_path):
        """Полный проход Этапов 1+2: змейка пишет кадры, YOLO (всегда находит биржу в этом тесте)
        переносит их в found. Координаты/РОЙ (Этап 3) здесь не участвуют — отдельная, уже
        протестированная функция (process_found_frame)."""
        engine = ExchangeScoutEngine(
            navigator=self._fake_navigator(), capture_fn=self._fake_capture(n_frames=3),
            model=self._fake_model_always_finds(), conf=0.8,
            sessions_root=str(tmp_path), move_wait=0.01,
        )
        engine.start()
        deadline = time.time() + 2.0
        found_dir = engine.found_dir
        while time.time() < deadline and len(os.listdir(found_dir)) == 0:
            time.sleep(0.05)
        engine.stop()

        assert len(os.listdir(found_dir)) > 0, "хотя бы один кадр должен был дойти до found"

    def test_no_exchange_frames_are_discarded_not_left_in_pending(self, tmp_path):
        """Этап 2: если биржи нет ни на одном кадре — pending пустеет (кадры удаляются), found
        остаётся пустым."""
        engine = ExchangeScoutEngine(
            navigator=self._fake_navigator(), capture_fn=self._fake_capture(n_frames=3),
            model=self._fake_model_never_finds(), conf=0.8,
            sessions_root=str(tmp_path), move_wait=0.01,
        )
        engine.start()
        time.sleep(0.3)
        engine.stop()
        # Дать consumer'у время доиграть то, что producer успел написать до stop().
        deadline = time.time() + 2.0
        pending_dir = engine.pending_dir
        while time.time() < deadline and len(os.listdir(pending_dir)) > 0:
            time.sleep(0.05)

        assert os.listdir(pending_dir) == []
        assert os.listdir(engine.found_dir) == []


class TestEndToEndPipeline:
    """Полный проход, как просил владелец: змейка → pending → фоновый YOLO → found → calibration
    #13-style crop_box → OCR X/Y → spend_credit("exchange") → RoyClient.report_scout_find(). Внешние
    сети/платежи подменены fake-объектами (та же дисциплина, что и в TestProcessFoundFrame) — сама
    склейка и порядок вызовов — реальные, не мокнутые."""

    def test_full_pipeline_charges_and_publishes_on_successful_find(self, tmp_path, monkeypatch):
        navigator = MagicMock()
        frames = [np.zeros((10, 10, 3), dtype=np.uint8) for _ in range(3)]
        state = {"i": 0}

        def capture_fn():
            f = frames[state["i"] % len(frames)]
            state["i"] += 1
            return f

        model = MagicMock()
        result = MagicMock()
        result.boxes = [MagicMock()]
        model.predict.return_value = [result]

        # OCR подменена на уровне exchange_scout (уже отдельно протестирована в TestReadExchangeCoords)
        # - здесь проверяется склейка, не точность распознавания текста на пустом кадре.
        monkeypatch.setattr("exchange_scout.read_exchange_position", lambda frame, crop_box: (7, 512, 318))

        spend_fn = MagicMock(return_value={"success": True, "credits": 90})
        roy_client = MagicMock()
        roy_client.report_scout_find.return_value = True

        on_found = make_found_handler(
            crop_box=(0, 990, 300, 1080), kingdom=7, hunt_type="exchange", hwid="test-hwid",
            spend_fn=spend_fn, roy_client=roy_client,
        )

        engine = ExchangeScoutEngine(
            navigator=navigator, capture_fn=capture_fn, model=model, conf=0.8,
            sessions_root=str(tmp_path), move_wait=0.01, on_found_callback=on_found,
        )
        engine.start()
        deadline = time.time() + 2.0
        while time.time() < deadline and spend_fn.call_count == 0:
            time.sleep(0.05)
        engine.stop()

        spend_fn.assert_called_with("exchange")
        roy_client.report_scout_find.assert_called_with(kingdom=7, x=512, y=318)
        assert len(os.listdir(engine.found_dir)) > 0


class TestResolveExchangeCropBox:
    """GUI-wiring (сессия #147, пункт 4): main.resolve_exchange_crop_box() — реальный
    crop_box из калибровочной цели #13 (exchange_coord_roi), тем же способом что
    _show_chest_rect_overlay считает свой оверлей-прямоугольник."""

    def _reset_coord_manager(self):
        from coord_manager import coord_manager, REF_A, REF_B
        coord_manager.calibrate(REF_A, REF_B)  # scale=1.0, anchor=REF_A — детерминированная база
        coord_manager.dialog_offset_x = 0
        coord_manager.dialog_offset_y = 0
        coord_manager.ui_offsets["exchange_coord_roi"] = [0, 0]
        return coord_manager

    def test_matches_ref_rect_when_no_offsets_calibrated(self):
        import main as _main_module
        coord_manager = self._reset_coord_manager()
        try:
            x1, y1, x2, y2 = _main_module.resolve_exchange_crop_box()
            ref_x, ref_y, ref_w, ref_h = _main_module.cal_target_by_id("exchange_coord_roi")["ref_rect"]
            assert (x1, y1) == coord_manager.to_screen(ref_x, ref_y)
            assert (x2 - x1, y2 - y1) == (ref_w, ref_h)
        finally:
            self._reset_coord_manager()

    def test_applies_position_and_size_offsets(self):
        import main as _main_module
        coord_manager = self._reset_coord_manager()
        try:
            coord_manager.set_ui_offset("exchange_coord_roi", 5, -3)
            coord_manager.set_roi_size_delta("exchange_coord_roi", 20, 10)
            x1, y1, x2, y2 = _main_module.resolve_exchange_crop_box()
            ref_x, ref_y, ref_w, ref_h = _main_module.cal_target_by_id("exchange_coord_roi")["ref_rect"]
            base_x, base_y = coord_manager.to_screen(ref_x, ref_y)
            assert (x1, y1) == (base_x + 5, base_y - 3)
            assert (x2 - x1, y2 - y1) == (ref_w + 20, ref_h + 10)
        finally:
            self._reset_coord_manager()

    def test_returned_box_is_directly_usable_by_position_reader(self):
        """Контракт из комментария main.py:180-199: (x1,y1,x2,y2) применяется НАПРЯМУЮ
        к исходному full-screenshot кадру, без доп. scaling — здесь просто проверяем,
        что PositionReader принимает выход resolve_exchange_crop_box() без ошибок."""
        import main as _main_module
        self._reset_coord_manager()
        try:
            crop_box = _main_module.resolve_exchange_crop_box()
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            coords = read_exchange_coords(frame, crop_box)
            assert coords is None  # пустой чёрный кадр — OCR не находит X/Y, но и не падает
        finally:
            self._reset_coord_manager()


class TestBuildScoutNavigator:
    """Живой баг (сессия #147): _toggle_scout передавал max_inland_steps из
    nav_inland_slider (потолок 10, Биржа 1.0), хотя владелец явно решил — до 50 шагов
    вглубь для Биржи 2.0 (feedback_no_drama_on_bounded_number_changes). 38/38 тестов
    были зелёными, потому что ни один тест не вызывал реальную функцию сборки
    navigator'а из production-пути (main._toggle_scout) — тесты проверяли только
    exchange_scout.py напрямую с фейковым navigator. Эти тесты закрывают именно
    этот разрыв test-wiring/production-wiring: вызывают ТУ ЖЕ функцию, что и GUI."""

    _GUI_CONFIG = {
        'ocean_land_ratio': 0.03,
        'min_water_px': 500,
        'diagonal_blind_coeff': 0.5,
        'footprint_ttl': 120.0,
        'return_delta_px': 0,
        'smooth_alpha': 0.5,
        'pixels_per_step': 20,
    }

    def test_default_depth_is_13_and_ceiling_is_50_not_the_bot1_slider_ceiling(self):
        import main as _main_module
        navigator = _main_module.build_scout_navigator(
            center_x=90, center_y=925, step=13, gui_config=self._GUI_CONFIG,
        )
        assert navigator.max_inland_steps == 13     # по умолчанию 13 (владелец 2026-09-21)
        assert _main_module.SCOUT_MAX_INLAND_STEPS == 50    # потолок 2.0

    def test_passes_through_remaining_gui_config_values(self):
        import main as _main_module
        navigator = _main_module.build_scout_navigator(
            center_x=90, center_y=925, step=13, gui_config=self._GUI_CONFIG,
        )
        assert navigator.center_x == 90
        assert navigator.center_y == 925
        assert navigator.ocean_land_ratio == 0.03
        assert navigator.min_water_px == 500
        assert navigator.diagonal_blind_coeff == 0.5
        assert navigator.return_delta_px == 0
        assert navigator.smooth_alpha == 0.5


class TestBuildScoutCaptureFn:
    """GUI-wiring (сессия #147, пункт 3): main.build_scout_capture_fn() — реальный
    mss.grab + BGRA->BGR, тем же паттерном что _run() в navigator.py (PacmanEngine)."""

    def test_returns_bgr_frame_from_mocked_mss(self, monkeypatch):
        import main as _main_module

        fake_shot = np.zeros((100, 200, 4), dtype=np.uint8)
        fake_shot[:, :, 0] = 10  # B
        fake_shot[:, :, 1] = 20  # G
        fake_shot[:, :, 2] = 30  # R

        class FakeSct:
            monitors = [None, {"left": 0, "top": 0, "width": 200, "height": 100}]

            def grab(self, monitor):
                return fake_shot

        monkeypatch.setattr("mss.mss", lambda: FakeSct())

        capture_fn = _main_module.build_scout_capture_fn()
        frame = capture_fn()

        assert frame.shape == (100, 200, 3)
        assert tuple(frame[0, 0]) == (10, 20, 30)  # BGRA->BGR: alpha dropped, order preserved

    def test_reuses_same_mss_instance_across_calls(self, monkeypatch):
        import main as _main_module

        fake_shot = np.zeros((10, 10, 4), dtype=np.uint8)
        created = []

        class FakeSct:
            monitors = [None, {"left": 0, "top": 0, "width": 10, "height": 10}]

            def grab(self, monitor):
                return fake_shot

        def _factory():
            created.append(1)
            return FakeSct()

        monkeypatch.setattr("mss.mss", _factory)

        capture_fn = _main_module.build_scout_capture_fn()
        capture_fn()
        capture_fn()

        assert len(created) == 1  # mss() создаётся один раз на весь producer-тред, не на кадр


class TestQueueAndNeuralControl:
    """Сессия #148 (пункт 3): счётчик очереди для прогресс-бара и отдельная кнопка «остановить/
    запустить нейросеть» (решение владельца 2026-09-18: ESC/Стоп останавливают змейку, но не consumer;
    для остановки нейросети — отдельная кнопка, кадры при этом остаются в очереди)."""

    def _engine(self, tmp_path, model=None, move_wait=0.01):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[:, :] = (30, 60, 90)
        navigator = MagicMock()
        if model is None:
            model = MagicMock()
            model.predict.return_value = [MagicMock(boxes=[])]   # биржи нет
        return ExchangeScoutEngine(
            navigator=navigator, capture_fn=lambda: frame, model=model, conf=0.8,
            sessions_root=str(tmp_path), move_wait=move_wait,
        )

    def _wait(self, cond, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline and not cond():
            time.sleep(0.02)
        return cond()

    def _put_frames(self, engine, n):
        for i in range(n):
            save_frame_atomic(np.zeros((40, 40, 3), dtype=np.uint8),
                              os.path.join(engine.pending_dir, f"{9000 + i:06d}.jpg"))

    def test_queue_size_zero_before_start(self, tmp_path):
        assert self._engine(tmp_path).queue_size() == 0

    def test_queue_size_counts_pending_jpgs(self, tmp_path):
        engine = self._engine(tmp_path)
        engine.start()
        engine.stop_consumer()
        assert self._wait(lambda: not engine.consumer_alive)
        engine.stop()
        before = engine.queue_size()          # змейка успела записать сколько-то кадров сама
        self._put_frames(engine, 5)
        assert engine.queue_size() == before + 5

    def test_stop_consumer_leaves_frames_in_queue_and_snake_keeps_producing(self, tmp_path):
        engine = self._engine(tmp_path)
        engine.start()
        engine.stop_consumer()
        assert self._wait(lambda: not engine.consumer_alive)
        before = engine.queue_size()
        assert self._wait(lambda: engine.queue_size() >= before + 3)   # змейка пишет, никто не читает
        assert engine.is_running is True
        engine.stop()

    def test_start_consumer_drains_queue_after_stop(self, tmp_path):
        engine = self._engine(tmp_path)
        engine.start()
        engine.stop_consumer()
        assert self._wait(lambda: not engine.consumer_alive)
        engine.stop()
        self._put_frames(engine, 4)
        assert engine.queue_size() >= 4
        engine.start_consumer()
        assert self._wait(lambda: engine.queue_size() == 0)
        assert self._wait(lambda: not engine.consumer_alive)   # очередь пуста, змейка стоит — сам завершился

    def test_start_consumer_is_noop_when_already_alive(self, tmp_path):
        engine = self._engine(tmp_path)
        engine.start()
        first = engine._consumer_thread
        engine.start_consumer()
        assert engine._consumer_thread is first
        engine.stop()

    def test_snake_stop_does_not_stop_consumer_while_queue_not_empty(self, tmp_path):
        """Инвариант конвейера (C-05) не сломан: ESC/Стоп змейки не трогают consumer."""
        engine = self._engine(tmp_path)
        engine.start()
        engine.stop_consumer()
        assert self._wait(lambda: not engine.consumer_alive)
        engine.stop()
        self._put_frames(engine, 3)
        engine.start_consumer()
        assert self._wait(lambda: engine.queue_size() == 0)


class TestSnakeSpeedFactor:
    """Владелец 2026-09-21: скорость змейки в 2.0 — не секунды, а множитель от МИНИМАЛЬНОГО цикла
    именно этого ПК (1× = быстрее всего, максимум = 4× от минимума). Пауза после шага =
    (множитель − 1) × измеренный естественный цикл (захват + шаг + запись кадра)."""

    def _engine(self, tmp_path, step_sec, factor, move_wait=0.0):
        frame = np.zeros((40, 40, 3), dtype=np.uint8)
        navigator = MagicMock()
        navigator.step.side_effect = lambda *a, **k: time.sleep(step_sec)
        model = MagicMock()
        model.predict.return_value = [MagicMock(boxes=[])]
        return ExchangeScoutEngine(
            navigator=navigator, capture_fn=lambda: frame, model=model, conf=0.8,
            sessions_root=str(tmp_path), move_wait=move_wait, speed_factor=factor,
        )

    def _cycles(self, engine, seconds):
        engine.start()
        time.sleep(seconds)
        engine.stop()
        return engine._frame_counter

    def test_factor_1_adds_no_pause(self, tmp_path):
        engine = self._engine(tmp_path, step_sec=0.05, factor=1.0)
        n = self._cycles(engine, 1.0)
        assert n >= 10                      # ~ 1.0 / (0.05 + накладные) — без паузы

    def test_factor_4_is_about_four_times_slower(self, tmp_path):
        fast = self._engine(tmp_path / "a", step_sec=0.05, factor=1.0)
        slow = self._engine(tmp_path / "b", step_sec=0.05, factor=4.0)
        n_fast = self._cycles(fast, 1.5)
        n_slow = self._cycles(slow, 1.5)
        assert n_fast / n_slow > 2.5        # ≈4×, запас на дрожание таймеров

    def test_natural_cycle_is_measured_from_real_work(self, tmp_path):
        engine = self._engine(tmp_path, step_sec=0.06, factor=1.0)
        self._cycles(engine, 0.8)
        assert 0.05 <= engine.natural_cycle <= 0.2

    def test_natural_cycle_zero_before_any_step(self, tmp_path):
        assert self._engine(tmp_path, 0.01, 1.0).natural_cycle == 0.0

    def test_default_factor_is_1(self, tmp_path):
        frame = np.zeros((40, 40, 3), dtype=np.uint8)
        engine = ExchangeScoutEngine(navigator=MagicMock(), capture_fn=lambda: frame, model=MagicMock(),
                                     conf=0.8, sessions_root=str(tmp_path))
        assert engine.speed_factor == 1.0
