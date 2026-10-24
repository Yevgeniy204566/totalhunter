"""
Две полосы во вкладке «Сундуки» (владелец 2026-10-24): «Очередь сундуков» — кропы, ждущие OCR,
шкала QUEUE_LIMIT (2000); «Батч сундуков» — распознанные неотправленные + очередь, шкала
BATCH_LIMIT (5000). Раньше очередь мерилась лимитом батча — это разные пределы.
"""
from unittest.mock import MagicMock, patch

import main as _main_module
from main import LANGS


def _app():
    app = _main_module.TotalHunterApp.__new__(_main_module.TotalHunterApp)
    app.chest_queue_bar = MagicMock()
    app.chest_queue_count_lb = MagicMock()
    app.chest_batch_bar = MagicMock()
    app.chest_batch_count_lb = MagicMock()
    return app


def test_queue_bar_uses_queue_limit_not_batch_limit():
    app = _app()
    with patch("chest_reader.count_pending", return_value=500), \
         patch("chest_reader.count_batch", return_value=500):
        app._refresh_chest_queue()

    app.chest_queue_bar.set.assert_called_with(0.25)                       # 500 / 2000
    assert app.chest_queue_count_lb.configure.call_args.kwargs["text"] == "500 / 2000"


def test_batch_bar_uses_batch_limit_and_counts_recognized_plus_queue():
    app = _app()
    with patch("chest_reader.count_pending", return_value=500), \
         patch("chest_reader.count_batch", return_value=1250):
        app._refresh_chest_queue()

    app.chest_batch_bar.set.assert_called_with(0.25)                       # 1250 / 5000
    assert app.chest_batch_count_lb.configure.call_args.kwargs["text"] == "1250 / 5000"


def test_bars_do_not_overflow_past_full():
    app = _app()
    with patch("chest_reader.count_pending", return_value=2500), \
         patch("chest_reader.count_batch", return_value=6000):
        app._refresh_chest_queue()

    app.chest_queue_bar.set.assert_called_with(1.0)
    app.chest_batch_bar.set.assert_called_with(1.0)


def test_every_language_has_both_bar_titles():
    for code in LANGS:
        assert LANGS[code].get("chest_queue_title"), code
        assert LANGS[code].get("chest_batch_title"), code


def test_titles_no_longer_say_ocr_queue():
    assert LANGS["RU"]["chest_queue_title"] == "Очередь сундуков"
    assert LANGS["RU"]["chest_batch_title"] == "Батч сундуков"
    assert LANGS["EN"]["chest_queue_title"] == "Chest queue"
    assert LANGS["EN"]["chest_batch_title"] == "Chest batch"
