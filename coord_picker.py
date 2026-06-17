"""
coord_picker.py — служебная утилита (НЕ часть бота).
Окно поверх всех — живая лупа вокруг курсора + точные экранные X,Y.
Наведи курсор на нужный пиксель в игре и читай координаты в заголовке окна.

Запуск: python coord_picker.py
Выход: Esc или закрыть окно.
"""
import tkinter as tk

import mss
import pyautogui
from PIL import Image, ImageTk

ZOOM_FACTOR = 8
CANVAS_W = 480
CANVAS_H = 360
REGION_W = CANVAS_W // ZOOM_FACTOR
REGION_H = CANVAS_H // ZOOM_FACTOR
REFRESH_MS = 80


def main():
    root = tk.Tk()
    root.title("coord_picker")
    root.attributes("-topmost", True)
    root.geometry(f"{CANVAS_W}x{CANVAS_H + 40}+40+40")
    root.resizable(False, False)

    label = tk.Label(root, text="X: ---  Y: ---", font=("Consolas", 14, "bold"))
    label.pack(pady=4)

    canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg="black")
    canvas.pack()
    img_ref = {"tk_img": None}

    root.bind("<Escape>", lambda e: root.destroy())

    def tick():
        cx, cy = pyautogui.position()
        label.configure(text=f"X: {cx}  Y: {cy}")

        x1 = max(0, cx - REGION_W // 2)
        y1 = max(0, cy - REGION_H // 2)
        with mss.mss() as sct:
            monitor = {"left": x1, "top": y1, "width": REGION_W, "height": REGION_H}
            shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img = img.resize((CANVAS_W, CANVAS_H), Image.NEAREST)

        tk_img = ImageTk.PhotoImage(img)
        img_ref["tk_img"] = tk_img  # keep a reference, tkinter needs it alive
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=tk_img)
        # Crosshair at center (= cursor position)
        canvas.create_line(CANVAS_W // 2, 0, CANVAS_W // 2, CANVAS_H, fill="#00FF00")
        canvas.create_line(0, CANVAS_H // 2, CANVAS_W, CANVAS_H // 2, fill="#00FF00")

        root.after(REFRESH_MS, tick)

    root.after(REFRESH_MS, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
