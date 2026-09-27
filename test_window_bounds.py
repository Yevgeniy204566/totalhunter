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


# ── automation_conflict (входящие, п.G) ─────────────────────────────────────────

def test_automation_conflict_nothing_running():
    assert main.automation_conflict(None, False, False, False, exclude="chest") is False


def test_automation_conflict_exchange_active_mode_blocks_others():
    assert main.automation_conflict("v1", False, False, False, exclude="chest") is True
    assert main.automation_conflict("v2", False, False, False, exclude="crypt") is True


def test_automation_conflict_scout_consumer_still_draining_blocks_others():
    """Живая жалоба владельца 2026-09-25: 'в фоне чекаются скрины Биржи, а мы запустили
    другую работу' — фоновый YOLO consumer Биржи 2.0 продолжает работать и ПОСЛЕ явной
    остановки змейки (active_mode уже None), должен блокировать старт другой автоматизации."""
    assert main.automation_conflict(None, True, False, False, exclude="chest") is True
    assert main.automation_conflict(None, True, False, False, exclude="crypt") is True


def test_automation_conflict_crypt_and_chest_block_each_other():
    assert main.automation_conflict(None, False, True, False, exclude="chest") is True
    assert main.automation_conflict(None, False, False, True, exclude="crypt") is True


def test_automation_conflict_excluded_automation_never_blocks_itself():
    """exclude — сама стартующая автоматизация не должна блокировать саму себя (иначе
    повторный старт/останов был бы невозможен)."""
    assert main.automation_conflict("v2", True, False, False, exclude="exchange") is False
    assert main.automation_conflict(None, False, True, False, exclude="crypt") is False
    assert main.automation_conflict(None, False, False, True, exclude="chest") is False


# ── Владелец 2026-09-27: при старте окно НЕ перекрывает панель задач Windows и НЕ
#    залезает в игру больше чем на 30% ширины — на любом экране и масштабе Windows.
#    Остальное (что не влезло) игрок доматывает двумя scrollbar / растягивает окно сам.
SCREENS = [(1024, 600), (1280, 720), (1366, 768), (1600, 900), (1920, 1080),
           (2560, 1440), (3840, 2160)]
SCALES = [1.0, 1.25, 1.5, 1.75, 2.0]
TASKBAR = 40
TITLE_BAR_LOGICAL = 31  # заголовок окна Windows при 100%, растёт вместе с масштабом


def test_start_window_never_covers_windows_taskbar():
    for sw, sh in SCREENS:
        for s in SCALES:
            area = (0, 0, sw, sh - TASKBAR)
            _, h, geo = main.compute_window_geometry(area, s)
            y = int(geo.split("+")[2])
            bottom = y + round((h + TITLE_BAR_LOGICAL) * s)
            assert bottom <= area[3], f"{sw}x{sh}@{s}: низ окна {bottom} > панель задач {area[3]}"


def test_start_window_takes_at_most_30_percent_of_screen_width():
    """≤30% — пока 30% не упираются в пол 360 (решение владельца 25.09 для экранов
    уже 1200 логических px, см. test_ancient_tv_resolutions_respect_absolute_floor)."""
    for sw, sh in SCREENS:
        for s in SCALES:
            area = (0, 0, sw, sh - TASKBAR)
            w, _, geo = main.compute_window_geometry(area, s)
            x = int(geo.split("+")[1])
            phys_w = round(w * s)
            assert x + phys_w <= sw, f"{sw}x{sh}@{s}: окно за правым краем"
            if sw / s >= main.WINDOW_MIN_WIDTH_FLOOR / main.WINDOW_MAX_WIDTH_FRACTION:
                assert phys_w <= sw * main.WINDOW_MAX_WIDTH_FRACTION + s, \
                    f"{sw}x{sh}@{s}: окно {phys_w}px > 30% экрана"
