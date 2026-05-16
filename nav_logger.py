"""
nav_logger.py — Бортовой самописец CoastalSnakeNavigator.

Записывает ВСЁ: каждый клик с реальными координатами экрана,
каждый переход состояний, каждое действие змейки.

Использование: вызвать install() ДО engine.start().
Подключён автоматически в engine.py.

Лог: C:\\BattleBot\\nav_debug.log
"""

import os
import datetime
import numpy as np
import navigator as _nav_mod

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nav_debug.log")

_installed = False

# ──────────────────────────────────────────────────────────────────
# Форматирование
# ──────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

def _vec(v) -> str:
    return f"({v[0]:+.2f},{v[1]:+.2f})"

def _screen(nav, dx: float, dy: float) -> str:
    """Реальные координаты клика на экране."""
    norm = np.hypot(dx, dy)
    if norm == 0:
        return "(none)"
    ndx, ndy = dx / norm, dy / norm
    sx = int(nav.center_x + ndx * nav.p_range_x)
    sy = int(nav.center_y + ndy * nav.p_range_y)
    return f"screen({sx},{sy})"

def _write(line: str):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ──────────────────────────────────────────────────────────────────
# Установка патчей
# ──────────────────────────────────────────────────────────────────

def install():
    global _installed
    if _installed:
        return

    # Заголовок сессии
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*100}\n")
        f.write(f"SESSION  {datetime.datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"{'='*100}\n")

    cls = _nav_mod.CoastalSnakeNavigator

    _patch_step(cls)
    _patch_move_perpendicular(cls)
    _patch_shift_click(cls)
    _patch_is_at_coast_now(cls)

    _installed = True
    print(f"[nav_logger] Samopisets aktiven -> {LOG_PATH}")


def _patch_step(cls):
    orig = cls.step

    def _step(self, is_water: bool = False, frame=None):
        state_before = self._state
        result = orig(self, is_water=is_water, frame=frame)
        state_after  = self._state

        if state_before != state_after:
            # Переход состояния
            extras = ""
            if state_after == "DIVING":
                extras = f"  inland_steps=0  blind={self._return_blind_steps}"
            elif state_after == "RETURNING":
                extras = (f"  return_steps={self._return_steps}"
                          f"  blind={self._return_blind_steps}")
            elif state_after == "HOMING":
                extras = ""

            _write(
                f"{_ts()}  "
                f"[TRANSITION]  {state_before:9} → {state_after:9}"
                f"  inland_vec={_vec(self._inland_vec)}"
                f"  shift_vec={_vec(self._shift_vec)}"
                f"  sv_locked={'YES' if self._shift_vec_set else 'NO'}"
                f"{extras}"
            )

        return result

    cls.step = _step


def _screen_with_delta(nav, dx: float, dy: float, delta_px: int) -> str:
    """Реальные координаты клика с учётом delta-смещения."""
    norm = np.hypot(dx, dy)
    if norm == 0:
        return "(none)"
    ndx, ndy = dx / norm, dy / norm
    cx = int(nav.center_x + ndx * nav.p_range_x)
    cy = int(nav.center_y + ndy * nav.p_range_y)
    if delta_px > 0 and nav._shift_vec_set:
        sv = nav._shift_vec
        sv_n = float(np.hypot(sv[0], sv[1]))
        if sv_n > 0:
            cx += int(sv[0] / sv_n * delta_px)
            cy += int(sv[1] / sv_n * delta_px)
    return f"screen({cx},{cy})"


def _patch_move_perpendicular(cls):
    orig = cls._move_perpendicular

    def _move_perp(self, toward_water: bool, return_delta_px: int = 0):
        iv = self._inland_vec
        if toward_water:
            action = "RETURN"
            dx, dy = -iv[0], -iv[1]
        else:
            action = "DIVE  "
            dx, dy = iv[0], iv[1]

        # Показываем РЕАЛЬНЫЙ клик (с дельтой для RETURN)
        sc = _screen_with_delta(self, dx, dy, return_delta_px)
        norm = np.hypot(dx, dy)
        if norm > 0:
            dx_n, dy_n = dx / norm, dy / norm
        else:
            dx_n, dy_n = 0.0, 0.0

        delta_info = f"  delta={return_delta_px}px" if return_delta_px else ""
        _write(
            f"{_ts()}  "
            f"[{action}]   {self._state:9}"
            f"  click=({dx_n:+.2f},{dy_n:+.2f})  {sc}"
            f"  inland_vec={_vec(iv)}"
            f"  inland_step={self._inland_steps}"
            f"  return_step={self._return_steps}"
            f"  blind={self._return_blind_steps}"
            f"{delta_info}"
        )
        return orig(self, toward_water, return_delta_px=return_delta_px)

    cls._move_perpendicular = _move_perp


def _patch_is_at_coast_now(cls):
    orig = cls._is_at_coast_now

    def _coast_now(self, frame=None):
        result = orig(self, frame=frame)
        # We need z values — re-run the check for logging only (cheap, same minimap)
        try:
            from minimap_reader import analyze_forward_zone
            mm = self._grab_minimap(frame=frame)
            seaward = (-self._inland_vec[0], -self._inland_vec[1])
            z = analyze_forward_zone(mm, seaward, radius=self.coast_detect_radius)
            _write(
                f"{_ts()}  "
                f"[LANTERN]  {self._state:9}"
                f"  water_px={z['water_px']:4d}  land_ratio={z['land_ratio']:.2f}"
                f"  result={'STOP' if result else 'go  '}"
                f"  return_step={self._return_steps}"
            )
        except Exception:
            pass
        return result

    cls._is_at_coast_now = _coast_now


def _patch_shift_click(cls):
    orig = cls._shift_click

    def _shift(self):
        sv_locked = self._shift_vec_set
        iv = self._inland_vec
        orig(self)
        sv_after = self._shift_vec
        sc = _screen(self, sv_after[0], sv_after[1])

        _write(
            f"{_ts()}  "
            f"[SHIFT ]   {self._state:9}"
            f"  sv={_vec(sv_after)}  {sc}"
            f"  iv_x={iv[0]:+.2f}"
            f"  sv_locked={'YES' if sv_locked else 'NO'}"
        )

    cls._shift_click = _shift
