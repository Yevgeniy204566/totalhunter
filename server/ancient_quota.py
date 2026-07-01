"""
ancient_quota.py — pure reference tables and split math for the "Древний" calculator.

No DB, no FastAPI — kept dependency-free so the weight math is trivially testable in
isolation. See docs/superpowers/specs/2026-06-23-ancient-quota-calculator-design.md.
"""
import re

# Уровень Древнего (81-250) → суммарный требуемый урон (HP) в миллионах. Источник —
# Google Sheet 1CvfVs4cWUr4EXs7e8uKi2wbT-sQ_gYSIWDw3oJ0Xo64, вкладка «Древний» (полная
# ресинхронизация 2026-06-23 — владелец исправил исходник в таблице, прежний артефакт
# на уровнях 163+/235-250 в источнике устранён, больше не домножаем вручную).
ANCIENT_LEVEL_HP: dict[int, float] = {
    81: 45.1, 82: 47.3, 83: 49.7, 84: 52.2, 85: 54.8, 86: 57.5, 87: 60.4, 88: 63.4,
    89: 66.6, 90: 69.9, 91: 73.4, 92: 77.1, 93: 80.9, 94: 85.0, 95: 89.2, 96: 93.7,
    97: 98.4, 98: 103.0, 99: 108.0, 100: 114.0, 101: 118.0, 102: 123.0, 103: 128.0,
    104: 133.0, 105: 139.0, 106: 144.0, 107: 150.0, 108: 156.0, 109: 162.0, 110: 169.0,
    111: 175.0, 112: 182.0, 113: 190.0, 114: 197.0, 115: 205.0, 116: 213.0, 117: 222.0,
    118: 231.0, 119: 240.0, 120: 250.0, 121: 259.0, 122: 270.0, 123: 281.0, 124: 292.0,
    125: 304.0, 126: 316.0, 127: 328.0, 128: 341.0, 129: 355.0, 130: 369.0, 131: 384.0,
    132: 399.0, 133: 415.0, 134: 432.0, 135: 449.0, 136: 467.0, 137: 486.0, 138: 505.0,
    139: 526.0, 140: 547.0, 141: 569.0, 142: 591.0, 143: 615.0, 144: 640.0, 145: 665.0,
    146: 692.0, 147: 719.0, 148: 748.0, 149: 778.0, 150: 809.0, 151: 842.0, 152: 867.0,
    153: 893.0, 154: 920.0, 155: 947.0, 156: 976.0, 157: 1000.0, 158: 1004.0,
    159: 1007.0, 160: 1100.0, 161: 1130.0, 162: 1170.0, 163: 1260.0, 164: 1300.0,
    165: 1340.0, 166: 1390.0, 167: 1440.0, 168: 1480.0, 169: 1530.0, 170: 1590.0,
    171: 1640.0, 172: 1700.0, 173: 1750.0, 174: 1810.0, 175: 1870.0, 176: 1940.0,
    177: 2000.0, 178: 2070.0, 179: 2140.0, 180: 2210.0, 181: 2280.0, 182: 2360.0,
    183: 2440.0, 184: 2540.0, 185: 2640.0, 186: 2720.0, 187: 2810.0, 188: 2890.0,
    189: 2980.0, 190: 3070.0, 191: 3160.0, 192: 3250.0, 193: 3350.0, 194: 3450.0,
    195: 3550.0, 196: 3660.0, 197: 3770.0, 198: 3880.0, 199: 4000.0, 200: 4120.0,
    201: 4240.0, 202: 4370.0, 203: 4500.0, 204: 4640.0, 205: 4780.0, 206: 4920.0,
    207: 5070.0, 208: 5220.0, 209: 5380.0, 210: 5540.0, 211: 5700.0, 212: 5870.0,
    213: 6050.0, 214: 6230.0, 215: 6420.0, 216: 6610.0, 217: 6810.0, 218: 7010.0,
    219: 7220.0, 220: 7440.0, 221: 7660.0, 222: 7890.0, 223: 8130.0, 224: 8370.0,
    225: 8630.0, 226: 8880.0, 227: 9150.0, 228: 9430.0, 229: 9710.0, 230: 10000.0,
    231: 10300.0, 232: 10600.0, 233: 10900.0, 234: 11200.0,
    235: 11600.0, 236: 11900.0, 237: 12300.0, 238: 12700.0, 239: 13000.0,
    240: 13400.0, 241: 13800.0, 242: 14300.0, 243: 14700.0, 244: 15100.0,
    245: 15600.0, 246: 16000.0, 247: 16500.0, 248: 17000.0, 249: 17500.0,
    250: 18100.0,
}

# Множитель силы одного тира войск относительно тира 5 (база = 1.0). Подтверждено
# владельцем — каждый следующий тир (5→9) в 1.8 раза сильнее предыдущего. Формула
# проверена на всех точках прежней вручную настроенной 13-шаговой диагональной таблицы
# (docs/superpowers/specs/2026-07-01-ancient-troop-weight-geometric-formula-design.md) —
# совпадает с допуском ±0.05, и, в отличие от диагонали, определена для ЛЮБОЙ независимой
# комбинации тиров G/S/M (5-9 каждый), а не только для 13 фиксированных строк.
TROOP_TIER_GROWTH = 1.8

VALID_PRESETS: set[str] = {"T5", "T6", "T7", "T8", "T9"}


def _tier_factor(tier: int) -> float:
    return TROOP_TIER_GROWTH ** (tier - 5)


def troop_weight(preset: str, g: int, s: int, m: int) -> float:
    preset_tier = int(preset[1:])
    player_power = _tier_factor(g) + _tier_factor(s) + _tier_factor(m)
    preset_power = 3 * _tier_factor(preset_tier)
    return min(1.0, player_power / preset_power)


def parse_troop_level(troop_level: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"G([5-9]) S([5-9]) M([5-9])", troop_level)
    if not match:
        raise ValueError(f"Malformed troop_level: {troop_level!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def total_quota_millions(levels: list[int], amplification: float) -> float:
    return sum(ANCIENT_LEVEL_HP[level] for level in levels) * amplification


def split_strategy_a(total: float, officer_count: int, veteran_count: int) -> dict:
    denom = officer_count * 1.0 + veteran_count * 0.5
    if denom <= 0:
        raise ValueError("officer_count and veteran_count cannot both be zero")
    officer_quota = (total / denom) * 1.0 if officer_count > 0 else 0.0
    veteran_quota = (total / denom) * 0.5 if veteran_count > 0 else 0.0
    return {
        "officer_quota": officer_quota,
        "veteran_quota": veteran_quota,
    }


def split_strategy_b(total: float, preset: str,
                      players: list[tuple[str, str | None]]) -> dict:
    included = [
        (name, level, troop_weight(preset, *parse_troop_level(level)))
        for name, level in players if level is not None
    ]
    excluded = [name for name, level in players if level is None]
    denom = sum(w for _, _, w in included)
    if denom <= 0:
        raise ValueError("no players with a troop_level set")
    return {
        "players": [
            {"name": name, "troop_level": level, "quota": total * w / denom}
            for name, level, w in included
        ],
        "excluded": excluded,
    }
