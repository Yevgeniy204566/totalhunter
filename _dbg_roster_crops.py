"""
Сохраняет панель, сетку и кропы карточек для визуальной проверки.
Запускать с открытой вкладкой «Старший» — там гарантированно 3+ карточки.
"""
import time
import cv2
import numpy as np
from clan_roster_reader import (
    grab_panel, get_card_crops,
    HEADER_HEIGHT_PX, OWN_Y0, PANEL_HEIGHT, PANEL_WIDTH,
    PITCH, NUM_VISIBLE_ROWS,
    NAME_X1, NAME_X2, NAME_Y1, NAME_Y2,
    MIGHT_X1, MIGHT_X2,
    MIGHT_Y1_C0, MIGHT_Y2_C0, MIGHT_Y1_C1, MIGHT_Y2_C1,
)

print("Жду 3 сек — переключись на вкладку Старший...")
for i in (3, 2, 1):
    print(i); time.sleep(1)

panel = grab_panel()
cv2.imwrite("_dbg_roster_panel.png", panel)
print(f"Панель: {panel.shape}  (ожидается {PANEL_HEIGHT}×{PANEL_WIDTH})")

# Контентная зона
content = panel[HEADER_HEIGHT_PX:OWN_Y0, :]
cv2.imwrite("_dbg_roster_content.png", content)

# Визуализация сетки
vis = panel.copy()
# Синяя: граница шапки
cv2.line(vis, (0, HEADER_HEIGHT_PX), (PANEL_WIDTH, HEADER_HEIGHT_PX), (255, 0, 0), 2)
# Красная: граница своей строки
cv2.line(vis, (0, OWN_Y0), (PANEL_WIDTH, OWN_Y0), (0, 0, 255), 2)
# Зелёные: границы карточек
for i in range(NUM_VISIBLE_ROWS + 1):
    y = HEADER_HEIGHT_PX + i * PITCH
    if y > OWN_Y0:
        break
    cv2.line(vis, (0, y), (PANEL_WIDTH, y), (0, 255, 0), 1)
# X-границы имени (жёлтые)
cv2.line(vis, (NAME_X1, HEADER_HEIGHT_PX), (NAME_X1, OWN_Y0), (0, 255, 255), 1)
cv2.line(vis, (NAME_X2, HEADER_HEIGHT_PX), (NAME_X2, OWN_Y0), (0, 255, 255), 1)
# X-границы могущества (магента)
cv2.line(vis, (MIGHT_X1, HEADER_HEIGHT_PX), (MIGHT_X1, OWN_Y0), (255, 0, 255), 1)
cv2.line(vis, (MIGHT_X2, HEADER_HEIGHT_PX), (MIGHT_X2, OWN_Y0), (255, 0, 255), 1)

# Y-границы имени: ЕДИНЫЙ диапазон для всех карточек (голубые)
for i in range(NUM_VISIBLE_ROWS):
    base = HEADER_HEIGHT_PX + i * PITCH
    if base + NAME_Y2 > OWN_Y0:
        break
    cv2.line(vis, (NAME_X1, base + NAME_Y1), (NAME_X2, base + NAME_Y1), (255, 255, 0), 1)
    cv2.line(vis, (NAME_X1, base + NAME_Y2), (NAME_X2, base + NAME_Y2), (255, 255, 0), 1)

# Y-границы могущества: C0 (фиолетовые) для card_0, C1 (оранжевые) для card_1+
base0 = HEADER_HEIGHT_PX
cv2.line(vis, (MIGHT_X1, base0 + MIGHT_Y1_C0), (MIGHT_X2, base0 + MIGHT_Y1_C0), (128, 0, 255), 1)
cv2.line(vis, (MIGHT_X1, base0 + MIGHT_Y2_C0), (MIGHT_X2, base0 + MIGHT_Y2_C0), (128, 0, 255), 1)
for i in range(1, NUM_VISIBLE_ROWS):
    b = HEADER_HEIGHT_PX + i * PITCH
    if b + MIGHT_Y2_C1 > OWN_Y0:
        break
    cv2.line(vis, (MIGHT_X1, b + MIGHT_Y1_C1), (MIGHT_X2, b + MIGHT_Y1_C1), (0, 100, 200), 1)
    cv2.line(vis, (MIGHT_X1, b + MIGHT_Y2_C1), (MIGHT_X2, b + MIGHT_Y2_C1), (0, 100, 200), 1)

cv2.imwrite("_dbg_roster_grid.png", vis)
print("Grid: синяя=header, зелёные=карточки, жёлтые_X=имя, магента_X=might")
print(f"      голубые_Y=имя Y={NAME_Y1}..{NAME_Y2} (все карточки)")
print(f"      фиолетовые_Y=might C0 Y={MIGHT_Y1_C0}..{MIGHT_Y2_C0}  оранжевые_Y=might C1 Y={MIGHT_Y1_C1}..{MIGHT_Y2_C1}")

# Кропы
cards = get_card_crops(panel, first_frame=True)
print(f"\nКарточек: {len(cards)}")
for i, (name_roi, might_roi) in enumerate(cards):
    cv2.imwrite(f"_dbg_roster_name_{i}.png", name_roi)
    cv2.imwrite(f"_dbg_roster_might_{i}.png", might_roi)
    tag = "C0" if i == 0 else "C1"
    print(f"  [{i}] might={tag}  name={name_roi.shape}  might_roi={might_roi.shape}")

# Полные слайсы карточек — для диагностики точных Y-позиций
for i in range(NUM_VISIBLE_ROWS):
    y0 = HEADER_HEIGHT_PX + i * PITCH
    y1 = min(y0 + PITCH, OWN_Y0)
    card_full = panel[y0:y1, :]
    cv2.imwrite(f"_dbg_card_full_{i}.png", card_full)
    print(f"  [card_{i}] y={y0}..{y1}  shape={card_full.shape}")

print("\nГотово. Проверь _dbg_roster_grid.png и _dbg_roster_name_*.png / _dbg_roster_might_*.png")
