"""
gui_layout_check.py — проверка окна бота на маленьких мониторах и масштабе Windows.

Владелец 2026-09-27 (жалоба на v2.1.0): на маленьких мониторах окно обрезано, Старт/Стоп
не виден, докрутить нельзя. Требование: на ЛЮБОМ разрешении Старт/Стоп доступен и
прокрутка доходит до самого низа — и это проверяется автоматически в каждой сборке
(build_release.py → test_gui_small_screens.py → этот скрипт).

Один запуск = один экран. Реальное окно TotalHunterApp создаётся невидимым (alpha=0),
рабочая область подменяется (main.get_work_area), масштаб Windows — через CTk scaling.
Отдельный процесс на случай: масштаб CTk глобален, а TotalHunterApp держит потоки/хуки.

    python gui_layout_check.py 1366 768 1.25     → JSON {"ok": bool, "errors": [...]}
"""
import ctypes
import ctypes.wintypes
import json
import os
import sys
import tkinter as tk

TASKBAR_PX = 40
# GetWindowRect включает невидимую рамку ресайза Windows 10/11 (~7px при 100%)
FRAME_TOLERANCE_PX = 8
# Кнопки, ради которых всё это: должны быть достижимы на любом экране
KEY_BUTTONS = {
    "tab_crypt": "crypt_start_btn",
    "tab_hunt": None,  # 1.0 — start_button, 2.0 — _scout_button, выбирается по режиму
    "tab_chest": "chest_start_btn",
    "tab_ancient": "ancient_start_btn",
    "tab_roy": "_roy_hunt_btn",
}


def _outer_rect(win):
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(int(win.wm_frame(), 16), ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def _visible_descendants(widget):
    """Потомки, видимые в раскладке вкладки. Внутрь tk.Canvas не заходим: содержимое
    CTkScrollableFrame живёт в canvas-окне и обрезается штатно — у него свой скроллбар."""
    for child in widget.winfo_children():
        if not child.winfo_ismapped():
            continue
        yield child
        if not isinstance(child, tk.Canvas):
            yield from _visible_descendants(child)


def _check_view(app, name, tab, key_button, errors):
    app.update()
    app._fit_content_height()
    app.update()

    # 1. Внутри вкладки ничего не обрезано (карточка pack_propagate(False))
    tab_top, tab_h, tab_w = tab.winfo_rooty(), tab.winfo_height(), tab.winfo_width()
    tab_left = tab.winfo_rootx()
    widgets = list(_visible_descendants(tab))
    for w in widgets:
        bottom = w.winfo_rooty() + w.winfo_height()
        right = w.winfo_rootx() + w.winfo_width()
        if bottom - tab_top > tab_h + 1:
            errors.append(f"{name}: {w.winfo_class()} {w} обрезан снизу "
                          f"({bottom - tab_top} > {tab_h})")
        if right - tab_left > tab_w + 1:
            errors.append(f"{name}: {w.winfo_class()} {w} обрезан справа "
                          f"({right - tab_left} > {tab_w})")

    # 2. Внешняя прокрутка докручивает до самого низа вкладки (координаты — ПОСЛЕ прокрутки)
    canvas = app._outer._parent_canvas
    canvas.yview_moveto(1.0)
    app.update()
    view_top = canvas.winfo_rooty()
    view_bottom = view_top + canvas.winfo_height()
    card = app._content_frame
    card_bottom = card.winfo_rooty() + card.winfo_height()
    if card_bottom > view_bottom + 1:
        errors.append(f"{name}: низ карточки ({card_bottom}) ниже видимой области "
                      f"({view_bottom}) после прокрутки до конца")
    for w in widgets:
        if w.winfo_rooty() + w.winfo_height() > view_bottom + 1:
            errors.append(f"{name}: {w} не виден даже после прокрутки до конца")
            break

    # 3. Кнопку Старт/Стоп можно прокруткой увидеть ЦЕЛИКОМ (на длинных вкладках она
    #    не обязана быть у самого низа — важно, что до неё можно докрутить)
    if key_button is not None:
        btn = getattr(app, key_button)
        if not btn.winfo_ismapped():
            errors.append(f"{name}: {key_button} не показан")
        else:
            total = float(canvas.bbox("all")[3]) or 1.0
            y_in_canvas = btn.winfo_rooty() - view_top + canvas.canvasy(0)
            canvas.yview_moveto(max(0.0, (y_in_canvas - 10) / total))
            app.update()
            b_top = btn.winfo_rooty()
            b_bottom = b_top + btn.winfo_height()
            if b_top < view_top - 1 or b_bottom > view_bottom + 1:
                errors.append(f"{name}: {key_button} нельзя увидеть целиком "
                              f"[{b_top}..{b_bottom}] vs [{view_top}..{view_bottom}]")
    canvas.yview_moveto(0.0)


def run(screen_w: int, screen_h: int, scale: float) -> dict:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, root_dir)
    os.chdir(root_dir)
    import customtkinter as ctk
    import main

    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)
    work_area = (0, 0, screen_w, screen_h - TASKBAR_PX)
    main.get_work_area = lambda: work_area

    errors = []
    app = main.TotalHunterApp()
    try:
        app.attributes("-alpha", 0.0)
        app.update()
        app._on_always_on_top()  # тот же пересчёт геометрии, что бот делает через 200мс
        app.update()

        # 0. Окно целиком на экране (не за правым/нижним краем)
        eff = app._get_window_scaling()
        left, top, right, bottom = _outer_rect(app)
        tol = round(FRAME_TOLERANCE_PX * eff)
        if right > work_area[2] + tol:
            errors.append(f"окно вылезает за правый край: {right} > {work_area[2]}")
        if bottom > work_area[3] + tol:
            errors.append(f"окно вылезает за нижний край: {bottom} > {work_area[3]}")
        if left < work_area[0] - tol:
            errors.append(f"окно вылезает за левый край: {left} < {work_area[0]}")

        for key in ("tab_crypt", "tab_roy", "tab_chest", "tab_ancient", "tab_ref"):
            app._show_tab(key)
            _check_view(app, key, getattr(app, key), KEY_BUTTONS.get(key), errors)

        app._show_tab("tab_hunt")
        for mode, btn in ((main.MODE_V1, "start_button"), (main.MODE_V2, "_scout_button")):
            app._set_exchange_mode(mode)
            for adv in (False, True):
                if app._adv_open != adv:
                    app._toggle_advanced()
                _check_view(app, f"tab_hunt[{mode},adv={adv}]", app.tab_hunt, btn, errors)
        app._set_exchange_mode(main.MODE_V1)

        app._show_calibration_tab()
        # _cal_frame — CTkScrollableFrame: сам объект — прокручиваемое содержимое внутри
        # canvas, раскладку вкладки занимает его внешний контейнер _parent_frame
        _check_view(app, "calibration", app._cal_frame._parent_frame, None, errors)
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return {"screen": f"{screen_w}x{screen_h}", "scale": scale,
            "effective_scale": eff, "ok": not errors, "errors": errors}


if __name__ == "__main__":
    w, h, s = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    out = sys.argv[4] if len(sys.argv) > 4 else None
    try:
        result = run(w, h, s)
    except Exception as exc:  # падение сборки окна — тоже провал проверки
        import traceback
        result = {"screen": f"{w}x{h}", "scale": s, "ok": False,
                  "errors": [f"исключение: {exc!r}", traceback.format_exc()]}
    data = json.dumps(result, ensure_ascii=False)
    # stdout бота перехвачен его логированием — результат пишем в файл, если он задан
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        print(data)
    os._exit(0)  # фоновые потоки бота (баланс, heartbeat) не должны держать процесс
