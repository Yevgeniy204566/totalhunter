"""
test_gui_small_screens.py — окно бота на ЛЮБОМ мониторе (владелец 2026-09-27, жалоба на v2.1.0).

Требование владельца: на любых разрешениях кнопка Старт/Стоп всегда доступна и прокрутка
доходит до самого низа бота; проверка — автоматически при каждом выпуске
(build_release.py запускает этот файл и прерывает сборку при провале).

Матрица: от нетбука/ТВ 1024×600 до 4K, масштаб Windows 100-200%. Каждый случай —
настоящее окно TotalHunterApp в отдельном процессе (gui_layout_check.py).
"""
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import pytest

import main

ROOT = os.path.dirname(os.path.abspath(__file__))
SCREENS = [(1024, 600), (1280, 720), (1366, 768), (1600, 900), (1920, 1080),
           (2560, 1440), (3840, 2160)]
SCALES = [1.0, 1.25, 1.5, 1.75, 2.0]
# Масштаб, при котором логическая высота экрана < ~400 (1024×600 на 200%) Windows
# сам не предлагает — такие сочетания не проверяем, окно там физически не помещается.
MIN_LOGICAL_HEIGHT = 380
CASES = [(w, h, s) for (w, h) in SCREENS for s in SCALES if (h - 40) / s >= MIN_LOGICAL_HEIGHT]
CASE_TIMEOUT_S = 180


def _run_case(case):
    w, h, s = case
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        subprocess.run([sys.executable, os.path.join(ROOT, "gui_layout_check.py"),
                        str(w), str(h), str(s), out],
                       cwd=ROOT, timeout=CASE_TIMEOUT_S,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(out, encoding="utf-8") as f:
            text = f.read()
        if not text:
            return {"screen": f"{w}x{h}", "scale": s, "ok": False,
                    "errors": ["проверка не записала результат (процесс упал)"]}
        return json.loads(text)
    except subprocess.TimeoutExpired:
        return {"screen": f"{w}x{h}", "scale": s, "ok": False,
                "errors": [f"таймаут {CASE_TIMEOUT_S}с"]}
    finally:
        try:
            os.remove(out)
        except OSError:
            pass


@pytest.fixture(scope="module")
def results():
    # Параллельно — каждый процесс поднимает полное окно бота (~10с)
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(_run_case, CASES))


def test_every_screen_and_scale_keeps_start_stop_reachable(results):
    failed = [r for r in results if not r["ok"]]
    report = "\n".join(f"{r['screen']} @ {int(r['scale'] * 100)}%:\n  " + "\n  ".join(r["errors"][:10])
                       for r in failed)
    assert not failed, f"{len(failed)}/{len(results)} экранов с проблемами:\n{report}"


# ── Чистые формулы (без GUI) ──────────────────────────────────────────────────

def test_window_geometry_is_logical_so_ctk_scaling_does_not_push_it_off_screen():
    """1920×1080 на 150%: CTk умножит 460×(1040/1.5-35) на 1.5 — должно поместиться."""
    w, h, geo = main.compute_window_geometry((0, 0, 1920, 1040), 1.5)
    assert round(h * 1.5) <= 1040 - 35
    x = int(geo.split("+")[1])
    assert x + round(w * 1.5) <= 1920


def test_window_geometry_at_100_percent_unchanged_on_owner_2k():
    """2K на 100% (у владельца) — ширина как и раньше 460, у правого края с отступом 10."""
    w, h, geo = main.compute_window_geometry((0, 0, 2560, 1400), 1.0)
    assert w == 460
    assert geo == f"460x{1400 - 35}+{2560 - 460 - 10}+0"


def test_content_height_grows_to_fit_tab_but_never_below_base():
    assert main.compute_content_height(740, 500, 1.0) == 740
    assert main.compute_content_height(740, 934, 1.0) == 934
    assert main.compute_content_height(740, 1401, 1.5) == 934
