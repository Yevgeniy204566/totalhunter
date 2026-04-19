"""
debug_vision.py — Показывает что бот "видит" в реальном времени.
Увеличенная миникарта + маски суши/воды + frontier.
Запустить отдельно: python debug_vision.py
"""
import cv2
import numpy as np
import pyautogui
from navigator import (
    get_land_water_masks, SCAN_AREA, MINIMAP_ZOOM,
    LAND_HSV, WATER_HSV, FRONTIER_DILATION,
)

CENTER_X = 90
CENTER_Y = 925
EATING_RADIUS = 12
MEMORY_CANVAS_SIZE = 1200
SCROLL_FACTOR = 0.84


def main():
    memory = np.zeros((MEMORY_CANVAS_SIZE, MEMORY_CANVAS_SIZE), np.uint8)
    mc = MEMORY_CANVAS_SIZE // 2
    offset = SCAN_AREA // 2

    print("Debug vision started. Press Q to quit.")
    print(f"Watching minimap at ({CENTER_X}, {CENTER_Y}), SCAN_AREA={SCAN_AREA}")

    while True:
        # Grab minimap
        shot = pyautogui.screenshot(
            region=(CENTER_X - offset, CENTER_Y - offset, SCAN_AREA, SCAN_AREA))
        minimap = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

        # Get masks (on zoomed image)
        land_z, water_z = get_land_water_masks(minimap)

        # Resize back for display side-by-side
        z = MINIMAP_ZOOM
        land_sm  = cv2.resize(land_z,  (SCAN_AREA, SCAN_AREA), interpolation=cv2.INTER_NEAREST)
        water_sm = cv2.resize(water_z, (SCAN_AREA, SCAN_AREA), interpolation=cv2.INTER_NEAREST)

        # Build frontier visualization
        mem_local = memory[mc - offset:mc + offset, mc - offset:mc + offset]
        void = cv2.bitwise_or(water_sm, mem_local)
        food = cv2.bitwise_and(land_sm, cv2.bitwise_not(void))
        dil_k    = np.ones((FRONTIER_DILATION * 2 + 1, FRONTIER_DILATION * 2 + 1), np.uint8)
        frontier = cv2.bitwise_and(food, cv2.dilate(void, dil_k))

        # Colour overlay on zoomed minimap
        display = cv2.resize(minimap, (SCAN_AREA * z, SCAN_AREA * z),
                             interpolation=cv2.INTER_LINEAR)

        # Water = blue overlay
        w_mask = cv2.resize(water_sm, (SCAN_AREA * z, SCAN_AREA * z),
                            interpolation=cv2.INTER_NEAREST)
        display[w_mask > 0] = (180, 60, 20)  # blue

        # Land = green overlay
        l_mask = cv2.resize(land_sm, (SCAN_AREA * z, SCAN_AREA * z),
                            interpolation=cv2.INTER_NEAREST)
        display[l_mask > 0] = (30, 140, 50)  # green

        # Frontier = yellow overlay
        f_mask = cv2.resize(frontier, (SCAN_AREA * z, SCAN_AREA * z),
                            interpolation=cv2.INTER_NEAREST)
        display[f_mask > 0] = (0, 220, 220)  # yellow

        # Visited = white dots
        v_mask = cv2.resize(mem_local, (SCAN_AREA * z, SCAN_AREA * z),
                            interpolation=cv2.INTER_NEAREST)
        display[v_mask > 0] = (200, 200, 200)  # light grey

        # Centre dot
        cx, cy = SCAN_AREA * z // 2, SCAN_AREA * z // 2
        cv2.circle(display, (cx, cy), 4, (0, 0, 255), -1)

        # Stats text
        land_pct  = int(land_sm.mean() / 255 * 100)
        water_pct = int(water_sm.mean() / 255 * 100)
        front_pct = int(frontier.mean() / 255 * 100)
        cv2.putText(display, f"Land:{land_pct}%  Water:{water_pct}%  Frontier:{front_pct}%",
                    (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show original next to overlay
        orig_z = cv2.resize(minimap, (SCAN_AREA * z, SCAN_AREA * z),
                            interpolation=cv2.INTER_LINEAR)
        combined = np.hstack([orig_z, display])
        cv2.imshow("Bot Vision  [original | overlay: green=land  blue=water  yellow=frontier]",
                   combined)

        key = cv2.waitKey(200) & 0xFF
        if key == ord('q') or key == 27:
            break

    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
