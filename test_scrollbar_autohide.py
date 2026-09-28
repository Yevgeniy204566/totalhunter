"""
Полосы прокрутки окна скрыты, пока игрок не меняет размер окна (владелец 27.09/28.09).
Полосы остаются в раскладке и работают (колесо, перетаскивание) — только рисуются цветом
фона, чтобы содержимое не прыгало на ширину полосы. Появляются при изменении размера окна,
гаснут через 2 с после последнего изменения. Перемещение окна их не показывает.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from main import AutoHideScrollbars, SCROLLBAR_HIDE_DELAY_MS

SHOWN = {"button_color": "#AAA", "button_hover_color": "#BBB"}
BG = "#000"


class FakeWin:
    def __init__(self):
        self.jobs, self.cancelled, self._n = {}, [], 0

    def after(self, ms, fn):
        self._n += 1
        self.jobs[self._n] = (ms, fn)
        return self._n

    def after_cancel(self, job):
        self.cancelled.append(job)
        self.jobs.pop(job, None)

    def run_pending(self):
        for job in list(self.jobs):
            _, fn = self.jobs.pop(job)
            fn()


def _setup():
    win = FakeWin()
    bars = [MagicMock(), MagicMock()]
    hider = AutoHideScrollbars(win, bars, SHOWN, BG)
    return win, bars, hider


def _event(win, w, h):
    return SimpleNamespace(widget=win, width=w, height=h)


def _last_colors(bar):
    return bar.configure.call_args.kwargs


def test_delay_is_two_seconds():
    assert SCROLLBAR_HIDE_DELAY_MS == 2000


def test_hidden_from_start():
    _, bars, _ = _setup()
    for bar in bars:
        assert _last_colors(bar) == {"button_color": BG, "button_hover_color": BG}


def test_first_configure_only_records_size():
    win, bars, hider = _setup()
    hider.on_configure(_event(win, 400, 900))
    assert _last_colors(bars[0])["button_color"] == BG


def test_resize_shows_then_hides_after_delay():
    win, bars, hider = _setup()
    hider.on_configure(_event(win, 400, 900))
    hider.on_configure(_event(win, 420, 900))
    for bar in bars:
        assert _last_colors(bar) == SHOWN
    assert [ms for ms, _ in win.jobs.values()] == [2000]
    win.run_pending()
    for bar in bars:
        assert _last_colors(bar)["button_color"] == BG


def test_continuous_resize_restarts_timer():
    win, _, hider = _setup()
    hider.on_configure(_event(win, 400, 900))
    hider.on_configure(_event(win, 410, 900))
    hider.on_configure(_event(win, 420, 910))
    assert len(win.jobs) == 1 and len(win.cancelled) == 1


def test_move_without_resize_and_child_widgets_do_not_show():
    win, bars, hider = _setup()
    hider.on_configure(_event(win, 400, 900))
    hider.on_configure(_event(win, 400, 900))               # перемещение окна
    hider.on_configure(SimpleNamespace(widget=object(), width=10, height=10))  # дочерний виджет
    assert _last_colors(bars[0])["button_color"] == BG
    assert win.jobs == {}
