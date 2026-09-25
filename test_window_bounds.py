"""
test_window_bounds.py — Ограничение размера окна бота (входящие, п.A; владелец 2026-09-25).

Жалоба: у части пользователей окно бота разворачивается на весь экран — перекрывает игру,
бот перестаёт видеть её элементы. Проверяем чистую формулу ширины (compute_window_width) и
guard от maximize (enforce_no_maximize) без запуска полного GUI (main.py безопасно
импортируется — TotalHunterApp создаётся только под `if __name__ == "__main__"`).
"""
import customtkinter as ctk
import main


def test_normal_and_large_screens_keep_current_460px():
    """Владелец 2026-09-25: 'меня очень устраивает мой вариант как сейчас у меня на 2К' —
    460px НИКОГДА не должно вырасти на нормальных/больших экранах, 30% — потолок сверху,
    не цель, к которой нужно стремиться."""
    for width in (1920, 2560, 3840, 7680):  # FHD, 2K (владелец), 4K, 8K
        assert main.compute_window_width(width) == 460


def test_small_screens_shrink_to_stay_within_30_percent():
    # 1366×768 ноутбук — из оригинального ТЗ владельца как обязательный сценарий проверки
    assert main.compute_window_width(1366) == 409  # int(1366*0.30), меньше 460
    assert main.compute_window_width(1280) == 384


def test_never_exceeds_30_percent_once_screen_is_wide_enough_for_the_floor():
    """≤30% — только пока экран достаточно широкий, чтобы 30% не упирались в пол 360px
    (то есть ширина >= 1200px, где 30% == 360). Ниже этого — пол намеренно побеждает
    30% (см. test_ancient_tv_resolutions_respect_absolute_floor), это не нарушение."""
    for width in (1280, 1366, 1920, 2560, 3840, 7680):
        win_w = main.compute_window_width(width)
        assert win_w <= width * main.WINDOW_MAX_WIDTH_FRACTION + 1  # +1 — округление int()


def test_ancient_tv_resolutions_respect_absolute_floor():
    """Владелец 2026-09-25: ноутбук на телевизор, старые/слабые разрешения — чистые 30%
    дают 240-307px, интерфейс (свёрстан под 460px) там налезал бы друг на друга. Пол
    360px — подтверждено владельцем явно, приоритетнее чистых 30% на экзотике."""
    assert main.compute_window_width(800) == 360
    assert main.compute_window_width(1024) == 360


def test_zero_or_negative_work_area_falls_back_to_preferred_width():
    """Защита от сбоя SystemParametersInfoW (RECT нулевой/некорректный) — не должно
    привести к нулевой/отрицательной ширине окна."""
    assert main.compute_window_width(0) == 460
    assert main.compute_window_width(-100) == 460


def test_enforce_no_maximize_resets_zoomed_window():
    root = ctk.CTk()
    try:
        root.geometry("460x800+100+50")
        root.update_idletasks()
        root.state("zoomed")
        root.update_idletasks()
        assert root.state() == "zoomed"

        reverted = main.enforce_no_maximize(root, "460x800+100+50")

        root.update_idletasks()
        assert reverted is True
        assert root.state() == "normal"
        assert root.winfo_width() == 460
    finally:
        root.destroy()


def test_enforce_no_maximize_is_noop_when_already_normal():
    root = ctk.CTk()
    try:
        root.geometry("460x800+100+50")
        root.update_idletasks()
        assert main.enforce_no_maximize(root, "460x800+100+50") is False
    finally:
        root.destroy()
