"""
Оверлей координат мыши — показывает X,Y поверх всех окон.
Запустить: python mouse_overlay.py
Закрыть: нажать ESC или закрыть окно.
"""
import tkinter as tk
import pyautogui
import threading


def run_overlay():
    root = tk.Tk()
    root.overrideredirect(True)       # без рамки
    root.attributes('-topmost', True)  # поверх всего
    root.attributes('-alpha', 0.85)   # полупрозрачность
    root.configure(bg='black')

    label = tk.Label(
        root,
        text='X: 0   Y: 0',
        font=('Courier', 18, 'bold'),
        fg='#00FF00',
        bg='black',
        padx=10, pady=5,
    )
    label.pack()

    # Позиция окна — правый верхний угол
    root.geometry('+1600+10')

    def update():
        x, y = pyautogui.position()
        label.config(text=f'X: {x:<5}  Y: {y:<5}')
        root.after(50, update)

    def on_key(event):
        if event.keysym == 'Escape':
            root.destroy()

    root.bind('<Escape>', on_key)
    update()
    root.mainloop()


if __name__ == '__main__':
    print("Оверлей запущен. Координаты мыши отображаются в правом верхнем углу.")
    print("Нажми ESC чтобы закрыть.")
    run_overlay()
