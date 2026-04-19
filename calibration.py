"""
calibration.py — автокалибровка джойстика навигации
Определяет SCREEN_W и SCREEN_H (сколько игровых единиц = 1 экран)
"""
import json
import time
import numpy as np
import pyautogui
from mss import mss as _mss

from PIL import Image
from navigator import PositionReader, CompassNavigator

CONFIG_PATH = 'C:/BattleBot/nav_config.json'


def grab_screen() -> np.ndarray:
    """Захват текущего экрана."""
    with _mss() as sct:
        monitor = sct.monitors[1]
        return np.array(sct.grab(monitor))


class Calibrator:
    def __init__(self, center_x: int = 90, center_y: int = 925, step: int = 17):
        self.center_x = center_x
        self.center_y = center_y
        self.step = step
        self.reader = PositionReader(crop_box=(0, 990, 300, 1080))
        self.joystick = CompassNavigator(center_x=center_x, center_y=center_y, step=step)

    # ── основные методы ────────────────────────

    def read_position(self, screenshot: np.ndarray) -> tuple[int, int]:
        """Читает X/Y с экрана. Бросает RuntimeError если не удалось."""
        pos = self.reader.read(screenshot)
        if pos is None:
            raise RuntimeError(
                "Не удалось прочитать координаты с экрана. "
                "Убедитесь что игра открыта и координаты видны в левом нижнем углу."
            )
        return pos

    def calc_screen_size(
        self,
        before: tuple[int, int],
        after: tuple[int, int],
        direction: str
    ) -> int:
        """
        Вычисляет размер 1 экрана в игровых единицах.
        direction='RIGHT'/'LEFT' → по оси X
        direction='DOWN'/'UP'   → по оси Y
        """
        if direction in ('RIGHT', 'LEFT'):
            delta = abs(after[0] - before[0])
        else:
            delta = abs(after[1] - before[1])

        if delta == 0:
            raise RuntimeError(
                f"Позиция не изменилась после хода {direction}. "
                "Проверьте координаты центра джойстика и шаг."
            )
        return delta

    def save(
        self,
        screen_w: int, screen_h: int,
        center_x: int, center_y: int, step: int,
        path: str = CONFIG_PATH
    ):
        """Сохраняет параметры калибровки в JSON."""
        config = {
            'screen_w': screen_w,
            'screen_h': screen_h,
            'center_x': center_x,
            'center_y': center_y,
            'step': step,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def load(self, path: str = CONFIG_PATH) -> dict:
        """Загружает параметры калибровки из JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def run(self, save_path: str = CONFIG_PATH) -> dict:
        """
        Полный цикл автокалибровки:
        1. Читаем стартовую позицию
        2. Клик ВПРАВО → читаем новую X → SCREEN_W
        3. Клик ВНИЗ   → читаем новую Y → SCREEN_H
        4. Сохраняем конфиг
        """
        print("=== Автокалибровка джойстика ===")
        print("Убедитесь, что игра открыта и карта видна.\n")

        # Шаг 1 — стартовая позиция (до 10 попыток)
        x0, y0 = None, None
        for attempt in range(10):
            screen0 = grab_screen()
            try:
                x0, y0 = self.read_position(screen0)
                break
            except RuntimeError:
                print(f"  Попытка {attempt+1}/10: координаты не видны, жду...")
                time.sleep(1)
        if x0 is None:
            raise RuntimeError("Не удалось прочитать координаты. Убедитесь что карта открыта.")
        print(f"Стартовая позиция: X={x0}, Y={y0}")

        # Шаг 2 — ход ВПРАВО
        print("Ход ВПРАВО...")
        # Сохраняем скрин ДО хода
        Image.fromarray(screen0).save('cal_before_right.png')
        self.joystick.move('RIGHT')
        time.sleep(2.0)
        screen1 = grab_screen()
        Image.fromarray(screen1).save('cal_after_right.png')
        x1, y1 = self.read_position(screen1)
        print(f"После хода вправо: X={x1}, Y={y1}")
        screen_w = self.calc_screen_size((x0, y0), (x1, y1), 'RIGHT')
        print(f"SCREEN_W = {screen_w} единиц")

        # Шаг 3 — ход ВНИЗ
        print("Ход ВНИЗ...")
        self.joystick.move('DOWN')
        time.sleep(2.0)
        screen2 = grab_screen()
        Image.fromarray(screen2).save('cal_after_down.png')
        x2, y2 = self.read_position(screen2)
        print(f"После хода вниз: X={x2}, Y={y2}")
        screen_h = self.calc_screen_size((x1, y1), (x2, y2), 'DOWN')
        print(f"SCREEN_H = {screen_h} единиц")

        result = {
            'screen_w': screen_w,
            'screen_h': screen_h,
            'center_x': self.center_x,
            'center_y': self.center_y,
            'step': self.step,
        }

        self.save(**result, path=save_path)
        print(f"\nКалибровка завершена! Сохранено в {save_path}")
        print(f"  screen_w = {screen_w}")
        print(f"  screen_h = {screen_h}")
        return result


# ── запуск напрямую ────────────────────────────
if __name__ == '__main__':
    import sys

    center_x = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    center_y = int(sys.argv[2]) if len(sys.argv) > 2 else 925
    step     = int(sys.argv[3]) if len(sys.argv) > 3 else 13

    print(f"Параметры: center=({center_x},{center_y}), step={step}")
    print("\nПереключись на игру прямо сейчас! Начало через:")
    for i in range(10, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)
    print("Старт!\n")

    cal = Calibrator(center_x, center_y, step)
    cal.run()
