"""
simulate_small_screen.py — посмотреть глазами, как бот выглядит на маленьком мониторе.

Запускает НАСТОЯЩЕЕ окно бота так, будто монитор — WIDTHxHEIGHT с масштабом Windows SCALE:
окно встаёт у правого края воображаемого экрана (левый верхний угол вашего монитора),
а сам воображаемый экран обведён красной рамкой, его панель задач — полосой снизу.

    python simulate_small_screen.py              → 1366×768, 125%
    python simulate_small_screen.py 1280 720 1.5
"""
import os
import sys

TASKBAR_PX = 40


def main_():
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 1366
    h = int(sys.argv[2]) if len(sys.argv) > 2 else 768
    s = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, root_dir)
    os.chdir(root_dir)

    import customtkinter as ctk
    import tkinter as tk
    import main

    ctk.set_widget_scaling(s)
    ctk.set_window_scaling(s)
    work_area = (0, 0, w, h - TASKBAR_PX)
    main.get_work_area = lambda: work_area

    app = main.TotalHunterApp()
    app.title(f"{app.title()}  [ИМИТАЦИЯ {w}x{h} @ {int(s * 100)}%]")

    # Рамка воображаемого экрана + его «панель задач» — окна-подложки, прозрачные для кликов
    # не нужны: они ниже окна бота и просто показывают границы.
    def _bar(x, y, bw, bh, color):
        t = tk.Toplevel(app)
        t.overrideredirect(True)
        t.geometry(f"{bw}x{bh}+{x}+{y}")
        t.configure(bg=color)
        t.attributes("-topmost", False)
        return t

    _bar(0, h - TASKBAR_PX, w, TASKBAR_PX, "#303a55")   # панель задач
    _bar(0, h - 1, w, 3, "#ff3030")                     # низ экрана
    _bar(w, 0, 3, h, "#ff3030")                         # правый край экрана
    app.lift()
    app.mainloop()


if __name__ == "__main__":
    main_()
