"""
calibration_ui.py — Sequential 2-point calibration with live magnifier.

Each point gets a live-updating zoom canvas (refreshes every 150 ms).
No upfront screenshot — grabs screen continuously so the game is always visible.

Usage:
    from calibration_ui import run_calibration
    point_a, point_b = run_calibration()
    # Returns (None, None) if user cancels
"""
import tkinter as tk

try:
    import mss as _mss
    from PIL import Image, ImageTk, ImageDraw
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from coord_manager import REF_A, REF_B

ZOOM_FACTOR  = 6          # 600%
CANVAS_W     = 420
CANVAS_H     = 320
REGION_W     = CANVAS_W // ZOOM_FACTOR   # 70 px of screen captured
REGION_H     = CANVAS_H // ZOOM_FACTOR   # 53 px of screen captured
REFRESH_MS   = 150        # live refresh interval


def _grab_region_live(cx: int, cy: int) -> "Image.Image":
    """Capture REGION_W×REGION_H pixels around (cx, cy) and zoom ZOOM_FACTOR×."""
    x1 = max(0, cx - REGION_W // 2)
    y1 = max(0, cy - REGION_H // 2)
    with _mss.mss() as sct:
        monitor = {"left": x1, "top": y1, "width": REGION_W, "height": REGION_H}
        shot = sct.grab(monitor)
    # shot.rgb gives raw RGB bytes directly — no numpy channel issues
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    img = img.resize((CANVAS_W, CANVAS_H), Image.NEAREST)
    # Draw red crosshair at center
    draw = ImageDraw.Draw(img)
    draw.line([(CANVAS_W // 2, 0), (CANVAS_W // 2, CANVAS_H)], fill="red", width=1)
    draw.line([(0, CANVAS_H // 2), (CANVAS_W, CANVAS_H // 2)], fill="red", width=1)
    return img


def _show_red_dot(root: tk.Tk, x: int, y: int) -> tk.Toplevel:
    """16×16 red crosshair Toplevel at screen position (x, y)."""
    dot = tk.Toplevel(root)
    dot.overrideredirect(True)
    dot.attributes("-topmost", True)
    dot.geometry(f"16x16+{x - 8}+{y - 8}")
    c = tk.Canvas(dot, width=16, height=16, bg="red", highlightthickness=0)
    c.pack()
    c.create_line(0, 8, 16, 8, fill="white", width=1)
    c.create_line(8, 0, 8, 16, fill="white", width=1)
    return dot


def _calibrate_one_point(
    root: tk.Tk,
    start_pos: tuple[int, int],
    label_text: str,
) -> "tuple[int, int] | None":
    """
    Live-zoom magnifier for one anchor point.
    Blocks until «Зафиксировать» or cancel.
    Returns (x, y) or None if cancelled.
    """
    result    = [None]
    cancelled = [False]
    cur_x     = tk.IntVar(master=root, value=start_pos[0])
    cur_y     = tk.IntVar(master=root, value=start_pos[1])
    red_dot   = [None]
    zoom_ref  = [None]    # keep PhotoImage alive (prevent GC)
    running   = [True]    # controls the refresh loop

    win = tk.Toplevel(root)
    win.title(f"Калибровка — {label_text}")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    tk.Label(win, text=label_text, font=("Arial", 12, "bold")).pack(pady=(10, 2))
    tk.Label(
        win,
        text="Кликните в лупе чтобы сместить точку.\nОтредактируйте X/Y вручную если нужно.",
        font=("Arial", 9), fg="gray",
    ).pack(pady=(0, 4))

    canvas = tk.Canvas(win, width=CANVAS_W, height=CANVAS_H,
                       cursor="crosshair", bg="black")
    canvas.pack(padx=10)

    # ── Live refresh loop ────────────────────────────────────────────────
    def _refresh():
        if not running[0]:
            return
        x, y = cur_x.get(), cur_y.get()
        canvas.delete("all")
        try:
            img   = _grab_region_live(x, y)
            photo = ImageTk.PhotoImage(img)
            zoom_ref[0] = photo
            canvas.create_image(0, 0, anchor="nw", image=photo)
        except Exception as e:
            canvas.create_text(CANVAS_W // 2, CANVAS_H // 2,
                               text=f"Ошибка захвата:\n{e}",
                               fill="red", font=("Arial", 10), justify="center")
        # Overlay current coordinates for visibility
        canvas.create_text(4, 4, anchor="nw",
                           text=f"X={x}  Y={y}",
                           fill="yellow", font=("Arial", 9, "bold"))
        # Move red dot on real screen
        _update_dot()
        win.after(REFRESH_MS, _refresh)

    def _update_dot():
        if red_dot[0]:
            try:
                red_dot[0].destroy()
            except tk.TclError:
                pass
        red_dot[0] = _show_red_dot(root, cur_x.get(), cur_y.get())

    def on_canvas_click(event):
        dx = (event.x - CANVAS_W // 2) / ZOOM_FACTOR
        dy = (event.y - CANVAS_H // 2) / ZOOM_FACTOR
        cur_x.set(int(cur_x.get() + dx))
        cur_y.set(int(cur_y.get() + dy))
        _update_dot()

    canvas.bind("<Button-1>", on_canvas_click)

    # ── X / Y spinboxes ──────────────────────────────────────────────────
    coord_frame = tk.Frame(win)
    coord_frame.pack(pady=8)

    def _on_spinbox_change(*_):
        _update_dot()

    tk.Label(coord_frame, text="X:", font=("Arial", 11)).grid(row=0, column=0, padx=4)
    sx = tk.Spinbox(coord_frame, from_=0, to=3840, textvariable=cur_x, width=6,
                    font=("Arial", 11), command=_on_spinbox_change)
    sx.grid(row=0, column=1, padx=4)
    sx.bind("<Return>",   _on_spinbox_change)
    sx.bind("<FocusOut>", _on_spinbox_change)

    tk.Label(coord_frame, text="Y:", font=("Arial", 11)).grid(row=0, column=2, padx=4)
    sy = tk.Spinbox(coord_frame, from_=0, to=2160, textvariable=cur_y, width=6,
                    font=("Arial", 11), command=_on_spinbox_change)
    sy.grid(row=0, column=3, padx=4)
    sy.bind("<Return>",   _on_spinbox_change)
    sy.bind("<FocusOut>", _on_spinbox_change)

    # ── Buttons ──────────────────────────────────────────────────────────
    def _cleanup():
        running[0] = False
        if red_dot[0]:
            try:
                red_dot[0].destroy()
            except tk.TclError:
                pass

    def on_fix():
        result[0] = (cur_x.get(), cur_y.get())
        _cleanup()
        win.destroy()

    def on_cancel():
        cancelled[0] = True
        _cleanup()
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=10)
    tk.Button(
        btn_frame, text="Зафиксировать",
        bg="#2d7a2d", fg="white", font=("Arial", 11, "bold"), width=16,
        command=on_fix,
    ).pack(side="left", padx=8)
    tk.Button(btn_frame, text="Отмена", font=("Arial", 11),
              command=on_cancel).pack(side="left", padx=8)

    # Start live refresh
    win.after(50, _refresh)
    win.wait_window()
    return result[0]


def run_calibration(
    parent: "tk.Misc | None" = None,
    start_a: "tuple[int,int] | None" = None,
    start_b: "tuple[int,int] | None" = None,
) -> "tuple[tuple[int,int]|None, tuple[int,int]|None]":
    """
    Sequential 2-point calibration with live magnifier.
    Shows Point A (minimap) first, then Point B (silver crosshair).

    parent: existing Tk/CTk root. Pass the main app window to avoid
            creating a second Tk instance (which breaks IntVar bindings).

    Returns (point_a, point_b). Either is None if user cancelled.
    """
    if not _DEPS_OK:
        raise ImportError("mss and Pillow are required for calibration UI")

    # Reuse existing root — never create a second tk.Tk() alongside CTkApp
    root = parent if parent is not None else tk.Tk()
    created_own_root = (parent is None)
    if created_own_root:
        root.withdraw()

    point_a = _calibrate_one_point(
        root, start_a if start_a is not None else REF_A,
        "Точка А — центр мини-карты (лево-низ)",
    )
    if point_a is None:
        if created_own_root:
            root.destroy()
        return None, None

    point_b = _calibrate_one_point(
        root, start_b if start_b is not None else REF_B,
        "Точка Б — крестик серебра (право-верх)",
    )
    if created_own_root:
        root.destroy()
    return point_a, point_b
