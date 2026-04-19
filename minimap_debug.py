"""
minimap_debug.py — Live minimap diagnostic tool.

Run this INSIDE the game to see what the bot "reads" from the minimap
every second: coast angle, inland vector, ocean/river detection.

Usage:
    python minimap_debug.py
    python minimap_debug.py --cx 90 --cy 925   (custom joystick centre)
    python minimap_debug.py --interval 0.5      (faster refresh)

Press Ctrl+C to stop.
"""
import argparse
import time
import sys
import numpy as np

from minimap_reader import detect_coast_angle, analyze_forward_zone, get_minimap_snapshot


def perpendicular(angle: float) -> float:
    """Return angle + 90° (perpendicular direction)."""
    return angle + np.pi / 2


def vec(angle: float) -> tuple[float, float]:
    """Unit vector from angle in radians."""
    return float(np.cos(angle)), float(np.sin(angle))


def deg(angle: float) -> float:
    """Angle in degrees, normalised to [0, 360)."""
    return float(np.degrees(angle) % 360)


def direction_label(dx: float, dy: float) -> str:
    """Human-readable compass label for a vector."""
    angle = np.degrees(np.arctan2(dy, dx)) % 360
    sectors = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']
    idx = int((angle + 22.5) / 45) % 8
    return sectors[idx]


def bar(ratio: float, width: int = 20) -> str:
    """ASCII progress bar for land_ratio."""
    filled = int(ratio * width)
    return '[' + '#' * filled + '.' * (width - filled) + ']'


def main():
    parser = argparse.ArgumentParser(description='Minimap diagnostic')
    parser.add_argument('--cx',       type=int,   default=90,   help='Joystick centre X')
    parser.add_argument('--cy',       type=int,   default=925,  help='Joystick centre Y')
    parser.add_argument('--size',     type=int,   default=180,  help='Minimap capture size')
    parser.add_argument('--interval', type=float, default=1.0,  help='Refresh interval (s)')
    args = parser.parse_args()

    print(f"\n  Minimap Diagnostic  (Ctrl+C to stop)")
    print(f"  Joystick centre: ({args.cx}, {args.cy})  |  "
          f"Capture size: {args.size}px  |  Refresh: {args.interval}s\n")
    print(f"  {'COAST':>6}  {'INLAND':>6}  │  "
          f"{'FWD water':>9}  {'FWD land':>8}  {'ratio':>6}  "
          f"land%          STATUS")
    print("  " + "─" * 80)

    try:
        while True:
            minimap = get_minimap_snapshot(args.cx, args.cy, args.size)

            coast_angle  = detect_coast_angle(minimap)
            inland_angle = perpendicular(coast_angle)
            inland_vec   = vec(inland_angle)
            coast_vec    = vec(coast_angle)

            # Analyse in the inland direction (where bot dives)
            fwd = analyze_forward_zone(minimap, inland_vec)

            # Analyse in the coast direction (where bot shifts)
            side = analyze_forward_zone(minimap, coast_vec)

            # Status
            if fwd['is_ocean']:
                status = "OCEAN — turn back"
            elif fwd['land_px'] == 0 and fwd['water_px'] == 0:
                status = "no data in cone"
            elif fwd['land_ratio'] < 0.03:
                status = "open water ahead (ocean?)"
            elif fwd['land_ratio'] > 0.7:
                status = "mostly land ahead"
            else:
                status = f"river/internal water  (land {fwd['land_ratio']:.0%})"

            coast_label  = direction_label(*coast_vec)
            inland_label = direction_label(*inland_vec)

            print(
                f"  {deg(coast_angle):>5.1f}° "
                f"({coast_label:>2})  "
                f"{deg(inland_angle):>5.1f}° "
                f"({inland_label:>2})  │  "
                f"{fwd['water_px']:>9}  "
                f"{fwd['land_px']:>8}  "
                f"{fwd['land_ratio']:>6.1%}  "
                f"{bar(min(fwd['land_ratio'], 1.0))}  "
                f"{status}"
            )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n  Stopped.")
        sys.exit(0)


if __name__ == '__main__':
    main()
