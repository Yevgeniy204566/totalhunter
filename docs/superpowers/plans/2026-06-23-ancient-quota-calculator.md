# Древний (Ancient Quota Calculator) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Древний" tab to the leader dashboard that computes a clan-wide Ancient
damage quota from chosen Ancient levels + a clan amplification coefficient, and splits
that quota among clan members either by rank (Officer/Veteran) or by troop level
(13-step matrix), using a roster sourced from a rewritten `tournament_reader.py`.

**Architecture:** Reuses the existing `ChestCollector` tenant (kingdom+clan+user_id,
same as Chests). One new table `ancient_roster` (per-player place/points/troop_level,
fully refreshed by tournament import except `troop_level`, which survives reimport for
players still present and is dropped when a player leaves). One new table
`ancient_calculations` (capped at 5 rows per collector) stores calculator history. Two
new FastAPI routers (`tournaments.py` for the bot-side import, `ancients_dashboard.py`
for the web dashboard) plus a pure-function module (`ancient_quota.py`) holding the
reference tables and the weight-split math, kept dependency-free so it's trivially
unit-testable. `tournament_reader.py` is rewritten from its current
`alliance_tag`/`api_token` contract to the `hwid`/`kingdom`/`clan` contract already used
by `chest_reader.py`.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend), React + react-router
(frontend), pytest (tests), `auth.get_hwid()` (bot client).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-23-ancient-quota-calculator-design.md` — follow
  it exactly; this plan implements Part A only (calculator). Public PIN self-report and
  audit/rollback are explicitly out of scope.
- Free feature: the tournament import endpoint and the calculator do **not** charge
  credits (unlike `/api/v1/chests/import`).
- `ancient_roster` import is a full replace per collector: players missing from the new
  import are deleted (no "dead souls"), `troop_level` for players still present is
  preserved across reimports.
- Clan preset dropdown must offer **T5, T6, T7, T8, T9** (all five).
- Strategy A has exactly two buckets: **Officer** (weight 1.0) and **Veteran** (weight
  0.5) — no third "regular" bucket.
- History capped at 5 rows per collector (oldest dropped on the 6th insert).
- Follow existing code patterns: tenant resolution via `_get_or_create_collector`-style
  helpers (see `server/chests.py`), dashboard auth via `get_web_user` + ownership check
  (see `server/chest_dashboard.py::_get_own_collector`), frontend i18n via
  `dashboard_content.js`/`dashboard_content.en.js` + `useLang()`.

---

## File Structure

| File | Responsibility |
|---|---|
| `server/ancient_quota.py` | **Create.** Pure constants (`ANCIENT_LEVEL_HP`, `TROOP_QUOTA_PRESETS`) + pure functions (`total_quota`, `split_strategy_a`, `split_strategy_b`). No DB, no FastAPI — fully unit-testable in isolation. |
| `server/tests/test_ancient_quota.py` | **Create.** Unit tests for the pure module. |
| `server/models.py` | **Modify.** Add `AncientRoster`, `AncientCalculation` models. |
| `server/alembic/versions/a1n2c3i4e5n6_add_ancient_tables.py` | **Create.** Migration for the two new tables. |
| `server/tournaments.py` | **Create.** `POST /api/v1/tournaments/import` — hwid auth, tenant resolution, roster upsert/delete. |
| `server/tests/test_tournaments.py` | **Create.** Endpoint tests for upsert/delete semantics. |
| `server/ancients_dashboard.py` | **Create.** `/web/dashboard/ancients` — GET roster+history, PATCH troop_level, POST calculate. |
| `server/tests/test_ancients_dashboard.py` | **Create.** Endpoint tests for calculate + history cap. |
| `server/main.py` | **Modify.** Register the two new routers. |
| `tournament_reader.py` | **Modify.** Replace `alliance_tag`/`api_token` contract with `hwid`/`kingdom`/`clan`, drop `tournament_config.json` dependency. |
| `web/src/api.js` | **Modify.** Add `dashboardAncients*` request helpers. |
| `web/src/pages/AncientsPage.jsx` | **Create.** Dashboard tab UI. |
| `web/src/App.jsx` | **Modify.** Register `/dashboard/ancients` route. |
| `web/src/components/Layout.jsx` | **Modify.** Add nav entry. |
| `web/src/dashboard_content.js` / `.en.js` | **Modify.** Add `ancients` i18n strings + `nav.ancients`. |

---

## Task 1: Pure calculation module

**Files:**
- Create: `server/ancient_quota.py`
- Test: `server/tests/test_ancient_quota.py`

**Interfaces:**
- Consumes: nothing (pure module).
- Produces:
  - `ANCIENT_LEVEL_HP: dict[int, float]` — level (81-250) → HP in millions.
  - `TROOP_QUOTA_PRESETS: dict[str, dict[str, float]]` — preset ('T5'..'T9') → troop_step → weight.
  - `TROOP_STEPS: list[str]` — the 13 step labels, in upgrade order, for UI dropdowns.
  - `total_quota_millions(levels: list[int], amplification: float) -> float`
  - `split_strategy_a(total: float, officer_count: int, veteran_count: int) -> dict` → `{"officer_quota": float, "veteran_quota": float}`
  - `split_strategy_b(total: float, preset: str, players: list[tuple[str, str | None]]) -> dict` → `{"players": [{"name": str, "troop_level": str, "quota": float}], "excluded": [str]}` — `players` is `[(name, troop_level_or_None), ...]`.

- [ ] **Step 1: Write the failing tests**

```python
# server/tests/test_ancient_quota.py
import pytest

from ancient_quota import (
    ANCIENT_LEVEL_HP, TROOP_QUOTA_PRESETS, TROOP_STEPS,
    total_quota_millions, split_strategy_a, split_strategy_b,
)


def test_ancient_level_hp_covers_full_range():
    assert set(ANCIENT_LEVEL_HP.keys()) == set(range(81, 251))
    assert ANCIENT_LEVEL_HP[81] == 45.1
    assert ANCIENT_LEVEL_HP[250] == 15700.0


def test_ancient_level_hp_monotonically_increasing():
    levels = sorted(ANCIENT_LEVEL_HP)
    for a, b in zip(levels, levels[1:]):
        assert ANCIENT_LEVEL_HP[b] > ANCIENT_LEVEL_HP[a]


def test_troop_steps_has_13_entries():
    assert len(TROOP_STEPS) == 13
    assert TROOP_STEPS[0] == "База 5"
    assert TROOP_STEPS[-1] == "База 9"


def test_troop_quota_presets_shape():
    assert set(TROOP_QUOTA_PRESETS.keys()) == {"T5", "T6", "T7", "T8", "T9"}
    for preset, weights in TROOP_QUOTA_PRESETS.items():
        assert set(weights.keys()) == set(TROOP_STEPS)


def test_troop_quota_presets_cap_at_own_tier():
    # База 9 is always 1.0 regardless of preset (player's tier >= every preset).
    for preset in TROOP_QUOTA_PRESETS:
        assert TROOP_QUOTA_PRESETS[preset]["База 9"] == 1.0
    # А player matching the clan's own preset tier is always 1.0.
    assert TROOP_QUOTA_PRESETS["T8"]["База 8"] == 1.0
    assert TROOP_QUOTA_PRESETS["T7"]["База 7"] == 1.0


def test_total_quota_millions_sums_and_amplifies():
    total = total_quota_millions([81, 100], 2.0)
    assert total == pytest.approx((45.1 + 114) * 2.0)


def test_total_quota_millions_single_level_no_amplification():
    assert total_quota_millions([81], 1.0) == pytest.approx(45.1)


def test_split_strategy_a_basic():
    result = split_strategy_a(total=150.0, officer_count=2, veteran_count=2)
    # denom = 2*1.0 + 2*0.5 = 3.0
    assert result["officer_quota"] == pytest.approx(150.0 * 1.0 / 3.0)
    assert result["veteran_quota"] == pytest.approx(150.0 * 0.5 / 3.0)


def test_split_strategy_a_zero_veterans():
    result = split_strategy_a(total=100.0, officer_count=4, veteran_count=0)
    assert result["officer_quota"] == pytest.approx(25.0)
    assert result["veteran_quota"] == pytest.approx(0.0)


def test_split_strategy_a_zero_total_members_raises():
    with pytest.raises(ValueError):
        split_strategy_a(total=100.0, officer_count=0, veteran_count=0)


def test_split_strategy_b_basic():
    players = [("Иванов", "База 8"), ("Петров", "Шаг 7.1")]
    result = split_strategy_b(total=100.0, preset="T8", players=players)
    w_ivanov = TROOP_QUOTA_PRESETS["T8"]["База 8"]
    w_petrov = TROOP_QUOTA_PRESETS["T8"]["Шаг 7.1"]
    denom = w_ivanov + w_petrov
    by_name = {p["name"]: p["quota"] for p in result["players"]}
    assert by_name["Иванов"] == pytest.approx(100.0 * w_ivanov / denom)
    assert by_name["Петров"] == pytest.approx(100.0 * w_petrov / denom)
    assert result["excluded"] == []


def test_split_strategy_b_excludes_missing_troop_level():
    players = [("Иванов", "База 8"), ("Безуровневый", None)]
    result = split_strategy_b(total=100.0, preset="T8", players=players)
    names_in_result = {p["name"] for p in result["players"]}
    assert "Безуровневый" not in names_in_result
    assert result["excluded"] == ["Безуровневый"]


def test_split_strategy_b_all_excluded_raises():
    with pytest.raises(ValueError):
        split_strategy_b(total=100.0, preset="T8", players=[("Никто", None)])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_ancient_quota.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ancient_quota'`

- [ ] **Step 3: Write the implementation**

```python
# server/ancient_quota.py
"""
ancient_quota.py — pure reference tables and split math for the "Древний" calculator.

No DB, no FastAPI — kept dependency-free so the weight math is trivially testable in
isolation. See docs/superpowers/specs/2026-06-23-ancient-quota-calculator-design.md.
"""

# Уровень Древнего (81-250) → суммарный требуемый урон (HP) в миллионах. Источник —
# Google Sheet 1CvfVs4cWUr4EXs7e8uKi2wbT-sQ_gYSIWDw3oJ0Xo64, вкладка «Древний». Уровни
# 235-250 в исходнике потеряли множитель ×10 при копировании (подтверждено владельцем
# 2026-06-23 — рост ~3% на уровень сохраняется только если домножить).
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
    159: 1007.0, 160: 1100.0, 161: 1130.0, 162: 1170.0, 163: 1200.0, 164: 1240.0,
    165: 1270.0, 166: 1310.0, 167: 1350.0, 168: 1390.0, 169: 1430.0, 170: 1480.0,
    171: 1520.0, 172: 1570.0, 173: 1610.0, 174: 1660.0, 175: 1710.0, 176: 1760.0,
    177: 1820.0, 178: 1870.0, 179: 1930.0, 180: 1980.0, 181: 2040.0, 182: 2100.0,
    183: 2170.0, 184: 2230.0, 185: 2300.0, 186: 2370.0, 187: 2440.0, 188: 2510.0,
    189: 2590.0, 190: 2670.0, 191: 2750.0, 192: 2830.0, 193: 2910.0, 194: 3000.0,
    195: 3090.0, 196: 3180.0, 197: 3280.0, 198: 3380.0, 199: 3480.0, 200: 3580.0,
    201: 3690.0, 202: 3800.0, 203: 3910.0, 204: 4030.0, 205: 4150.0, 206: 4280.0,
    207: 4410.0, 208: 4540.0, 209: 4670.0, 210: 4810.0, 211: 4960.0, 212: 5110.0,
    213: 5260.0, 214: 5420.0, 215: 5580.0, 216: 5750.0, 217: 5920.0, 218: 6100.0,
    219: 6280.0, 220: 6470.0, 221: 6660.0, 222: 6860.0, 223: 7070.0, 224: 7280.0,
    225: 7500.0, 226: 7730.0, 227: 7960.0, 228: 8200.0, 229: 8440.0, 230: 8700.0,
    231: 8960.0, 232: 9220.0, 233: 9500.0, 234: 9790.0,
    # 235-250: исходные значения ×10 (см. комментарий выше).
    235: 10100.0, 236: 10400.0, 237: 10700.0, 238: 11000.0, 239: 11300.0,
    240: 11700.0, 241: 12000.0, 242: 12400.0, 243: 12800.0, 244: 13200.0,
    245: 13500.0, 246: 14000.0, 247: 14400.0, 248: 14800.0, 249: 15200.0,
    250: 15700.0,
}

# 13-ступенчатая матрица переходных войск (М→С→Г), финальная версия из переписки с
# Gemini (docs/Входящие_Gemini.md, секция «Мастер-таблица для Клода (с переходными
# войсками)»). Cap-правило (тир игрока выше прессета → 1.0) уже встроено в значения.
TROOP_STEPS: list[str] = [
    "База 5", "Шаг 5.1", "Шаг 5.2",
    "База 6", "Шаг 6.1", "Шаг 6.2",
    "База 7", "Шаг 7.1", "Шаг 7.2",
    "База 8", "Шаг 8.1", "Шаг 8.2",
    "База 9",
]

TROOP_QUOTA_PRESETS: dict[str, dict[str, float]] = {
    "T5": {
        "База 5": 1.0, "Шаг 5.1": 1.0, "Шаг 5.2": 1.0,
        "База 6": 1.0, "Шаг 6.1": 1.0, "Шаг 6.2": 1.0,
        "База 7": 1.0, "Шаг 7.1": 1.0, "Шаг 7.2": 1.0,
        "База 8": 1.0, "Шаг 8.1": 1.0, "Шаг 8.2": 1.0,
        "База 9": 1.0,
    },
    "T6": {
        "База 5": 0.55, "Шаг 5.1": 0.65, "Шаг 5.2": 0.80,
        "База 6": 1.0, "Шаг 6.1": 1.0, "Шаг 6.2": 1.0,
        "База 7": 1.0, "Шаг 7.1": 1.0, "Шаг 7.2": 1.0,
        "База 8": 1.0, "Шаг 8.1": 1.0, "Шаг 8.2": 1.0,
        "База 9": 1.0,
    },
    "T7": {
        "База 5": 0.30, "Шаг 5.1": 0.35, "Шаг 5.2": 0.45,
        "База 6": 0.55, "Шаг 6.1": 0.65, "Шаг 6.2": 0.80,
        "База 7": 1.0, "Шаг 7.1": 1.0, "Шаг 7.2": 1.0,
        "База 8": 1.0, "Шаг 8.1": 1.0, "Шаг 8.2": 1.0,
        "База 9": 1.0,
    },
    "T8": {
        "База 5": 0.15, "Шаг 5.1": 0.20, "Шаг 5.2": 0.25,
        "База 6": 0.30, "Шаг 6.1": 0.35, "Шаг 6.2": 0.45,
        "База 7": 0.55, "Шаг 7.1": 0.65, "Шаг 7.2": 0.80,
        "База 8": 1.0, "Шаг 8.1": 1.0, "Шаг 8.2": 1.0,
        "База 9": 1.0,
    },
    "T9": {
        "База 5": 0.05, "Шаг 5.1": 0.05, "Шаг 5.2": 0.10,
        "База 6": 0.15, "Шаг 6.1": 0.20, "Шаг 6.2": 0.25,
        "База 7": 0.30, "Шаг 7.1": 0.35, "Шаг 7.2": 0.45,
        "База 8": 0.55, "Шаг 8.1": 0.65, "Шаг 8.2": 0.80,
        "База 9": 1.0,
    },
}


def total_quota_millions(levels: list[int], amplification: float) -> float:
    return sum(ANCIENT_LEVEL_HP[level] for level in levels) * amplification


def split_strategy_a(total: float, officer_count: int, veteran_count: int) -> dict:
    denom = officer_count * 1.0 + veteran_count * 0.5
    if denom <= 0:
        raise ValueError("officer_count and veteran_count cannot both be zero")
    return {
        "officer_quota": total * 1.0 / denom,
        "veteran_quota": total * 0.5 / denom,
    }


def split_strategy_b(total: float, preset: str,
                      players: list[tuple[str, str | None]]) -> dict:
    weights = TROOP_QUOTA_PRESETS[preset]
    included = [(name, weights[level]) for name, level in players if level is not None]
    excluded = [name for name, level in players if level is None]
    denom = sum(w for _, w in included)
    if denom <= 0:
        raise ValueError("no players with a troop_level set")
    return {
        "players": [
            {"name": name, "troop_level": level, "quota": total * weights[level] / denom}
            for name, level in players if level is not None
        ],
        "excluded": excluded,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_ancient_quota.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add server/ancient_quota.py server/tests/test_ancient_quota.py
git commit -m "feat(ancients): add ANCIENT_LEVEL_HP/TROOP_QUOTA_PRESETS reference tables and split math"
```

---

## Task 2: Database models + migration

**Files:**
- Modify: `server/models.py`
- Create: `server/alembic/versions/a1n2c3i4e5n6_add_ancient_tables.py`

**Interfaces:**
- Consumes: `ChestCollector` (existing, `server/models.py:379`).
- Produces: `AncientRoster`, `AncientCalculation` ORM classes for Tasks 3 and 4.

- [ ] **Step 1: Add the models**

Append to `server/models.py` (after `ChestLocalization`, end of file):

```python
class AncientRoster(Base):
    """Один игрок клана в текущем ростере «Древнего» — полностью перезаписывается
    каждым импортом турнира, кроме troop_level (ручной ввод лидера, переживает
    реимпорт для оставшихся игроков, удаляется вместе со строкой для выпавших)."""
    __tablename__ = "ancient_roster"
    __table_args__ = (
        UniqueConstraint("collector_id", "player_name", name="uq_ancient_roster_player"),
    )

    id            = Column(Integer, primary_key=True)
    collector_id  = Column(Integer, ForeignKey("chest_collectors.id"),
                           nullable=False, index=True)
    player_name   = Column(String(100), nullable=False)
    place         = Column(Integer, nullable=True)
    points        = Column(BigInteger, nullable=True)
    troop_level   = Column(String(20), nullable=True)
    updated_at    = Column(TIMESTAMP(timezone=True), nullable=False,
                           server_default=func.now())


class AncientCalculation(Base):
    """История расчётов калькулятора «Древний» — максимум 5 на collector_id, старая
    запись удаляется при вставке 6-й. Пишется только по кнопке «Рассчитать»."""
    __tablename__ = "ancient_calculations"

    id                    = Column(Integer, primary_key=True)
    collector_id          = Column(Integer, ForeignKey("chest_collectors.id"),
                                   nullable=False, index=True)
    computed_at           = Column(TIMESTAMP(timezone=True), nullable=False,
                                   server_default=func.now())
    strategy              = Column(String(1), nullable=False)
    clan_preset           = Column(String(8), nullable=True)
    summon_levels         = Column(JSON, nullable=False)
    amplification_coef    = Column(Float, nullable=False)
    officer_count         = Column(Integer, nullable=True)
    veteran_count         = Column(Integer, nullable=True)
    total_quota_millions  = Column(Float, nullable=False)
    result_json           = Column(JSON, nullable=False)
```

Check `server/models.py` already imports `Float` and `BigInteger` — grep the top of the
file (`from sqlalchemy import ...`); if `Float` is missing from that import line, add it.

- [ ] **Step 2: Write the migration**

```python
# server/alembic/versions/a1n2c3i4e5n6_add_ancient_tables.py
"""add ancient_roster and ancient_calculations (Древний calculator, Part A)

Revision ID: a1n2c3i4e5n6
Revises: h1s2t3o4r5y6
Create Date: 2026-06-23

Per docs/superpowers/specs/2026-06-23-ancient-quota-calculator-design.md. Both tables
are scoped to the existing chest_collectors tenant (same collector_id as Chests).
"""
from alembic import op
import sqlalchemy as sa

revision      = 'a1n2c3i4e5n6'
down_revision = 'h1s2t3o4r5y6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'ancient_roster',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey('chest_collectors.id'),
                  nullable=False, index=True),
        sa.Column('player_name', sa.String(100), nullable=False),
        sa.Column('place', sa.Integer(), nullable=True),
        sa.Column('points', sa.BigInteger(), nullable=True),
        sa.Column('troop_level', sa.String(20), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('collector_id', 'player_name',
                            name='uq_ancient_roster_player'),
    )
    op.create_table(
        'ancient_calculations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey('chest_collectors.id'),
                  nullable=False, index=True),
        sa.Column('computed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('strategy', sa.String(1), nullable=False),
        sa.Column('clan_preset', sa.String(8), nullable=True),
        sa.Column('summon_levels', sa.JSON(), nullable=False),
        sa.Column('amplification_coef', sa.Float(), nullable=False),
        sa.Column('officer_count', sa.Integer(), nullable=True),
        sa.Column('veteran_count', sa.Integer(), nullable=True),
        sa.Column('total_quota_millions', sa.Float(), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('ancient_calculations')
    op.drop_table('ancient_roster')
```

- [ ] **Step 3: Verify the migration applies locally**

Run: `cd server && alembic upgrade head`
Expected: no errors, ends on revision `a1n2c3i4e5n6`. (Uses whatever `DATABASE_URL` is
configured in your local/dev environment — do **not** point this at the GCP production
database from a dev machine.)

- [ ] **Step 4: Commit**

```bash
git add server/models.py server/alembic/versions/a1n2c3i4e5n6_add_ancient_tables.py
git commit -m "feat(ancients): add ancient_roster and ancient_calculations tables"
```

---

## Task 3: Tournament import endpoint

**Files:**
- Create: `server/tournaments.py`
- Test: `server/tests/test_tournaments.py`
- Modify: `server/main.py`

**Interfaces:**
- Consumes: `ChestCollector`, `User`, `PlayerAlias` (`server/models.py`); the
  `_get_or_create_collector` pattern from `server/chests.py:52`.
- Produces: `router` (FastAPI `APIRouter`, prefix `/api/v1/tournaments`) registered in
  `main.py`.

- [ ] **Step 1: Write the failing tests**

Look at `server/tests/test_chests.py` first to copy its fixture setup (DB session,
test client, how a `User` + `hwid` is created) — match that pattern exactly so this
test file is consistent with the existing suite. Then write:

```python
# server/tests/test_tournaments.py
import pytest

from models import AncientRoster, ChestCollector, PlayerAlias

# NOTE for the implementer: import whatever async client / db-session fixtures
# server/tests/test_chests.py uses (e.g. `client`, `db_session`, a `make_user` helper)
# — do not invent a new fixture setup, mirror the existing one exactly.


@pytest.mark.asyncio
async def test_import_creates_roster(client, db_session, make_user):
    user = await make_user(hwid="HWID1")
    payload = {
        "hwid": "HWID1", "kingdom": "K229", "clan": "BERS",
        "timestamp": "2026-06-23T10:00:00",
        "items": [
            {"name": "Иванов", "place": 1, "points": 26000},
            {"name": "Петров", "place": 2, "points": 24000},
        ],
    }
    resp = await client.post("/api/v1/tournaments/import", json=payload)
    assert resp.status_code == 200
    assert resp.json()["count"] == 2

    collector = (await db_session.execute(
        __import__("sqlalchemy").select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS")
    )).scalar_one()
    rows = (await db_session.execute(
        __import__("sqlalchemy").select(AncientRoster).where(
            AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов", "Петров"}


@pytest.mark.asyncio
async def test_reimport_preserves_troop_level_for_existing_player(
        client, db_session, make_user):
    user = await make_user(hwid="HWID2")
    base_payload = {
        "hwid": "HWID2", "kingdom": "K229", "clan": "BERS2",
        "timestamp": "2026-06-23T10:00:00",
        "items": [{"name": "Иванов", "place": 1, "points": 100}],
    }
    await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        __import__("sqlalchemy").select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS2")
    )).scalar_one()
    row = (await db_session.execute(
        __import__("sqlalchemy").select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == "Иванов")
    )).scalar_one()
    row.troop_level = "База 8"
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Иванов", "place": 3, "points": 50}])
    await client.post("/api/v1/tournaments/import", json=reimport_payload)

    await db_session.refresh(row)
    assert row.place == 3
    assert row.points == 50
    assert row.troop_level == "База 8"


@pytest.mark.asyncio
async def test_reimport_drops_player_no_longer_present(client, db_session, make_user):
    user = await make_user(hwid="HWID3")
    base_payload = {
        "hwid": "HWID3", "kingdom": "K229", "clan": "BERS3",
        "timestamp": "2026-06-23T10:00:00",
        "items": [
            {"name": "Иванов", "place": 1, "points": 100},
            {"name": "Уходящий", "place": 2, "points": 50},
        ],
    }
    await client.post("/api/v1/tournaments/import", json=base_payload)

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Иванов", "place": 1, "points": 100}])
    await client.post("/api/v1/tournaments/import", json=reimport_payload)

    collector = (await db_session.execute(
        __import__("sqlalchemy").select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS3")
    )).scalar_one()
    rows = (await db_session.execute(
        __import__("sqlalchemy").select(AncientRoster).where(
            AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов"}


@pytest.mark.asyncio
async def test_import_does_not_charge_credits(client, db_session, make_user):
    user = await make_user(hwid="HWID4", credits=5)
    payload = {
        "hwid": "HWID4", "kingdom": "K229", "clan": "BERS4",
        "timestamp": "2026-06-23T10:00:00",
        "items": [{"name": "Иванов", "place": 1, "points": 100}],
    }
    resp = await client.post("/api/v1/tournaments/import", json=payload)
    assert resp.status_code == 200
    await db_session.refresh(user)
    assert user.credits == 5  # unchanged — free feature
```

(The `__import__("sqlalchemy").select` calls are deliberately verbose to avoid
guessing whether `test_chests.py` already has `select` imported at module scope —
replace with a plain `from sqlalchemy import select` import once you've checked.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_tournaments.py -v`
Expected: FAIL (404, route doesn't exist yet — `server/tournaments.py` not created)

- [ ] **Step 3: Write the implementation**

```python
# server/tournaments.py
"""
tournaments.py — Tournament roster import endpoint.

POST /api/v1/tournaments/import — принимает турнирный ростер от бота (tournament_reader.py),
изолирует по тенанту [kingdom, clan, user_id] (тот же ChestCollector, что у Сундуков),
полностью заменяет ancient_roster для этого collector_id: upsert по player_name (place/
points обновляются, troop_level не трогается), удаление строк для игроков, отсутствующих
в новом импорте.

Auth: hwid в payload → User (как /api/v1/chests/import). Бесплатно — не списывает кредиты,
весь функционал «Древний» бесплатен по требованию.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chests import _get_or_create_collector
from database import get_db
from models import AncientRoster, PlayerAlias, User

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])


class TournamentItemIn(BaseModel):
    name: str
    place: Optional[int] = None
    points: Optional[int] = None


class TournamentImportPayload(BaseModel):
    hwid: str
    kingdom: str
    clan: str
    timestamp: str
    items: List[TournamentItemIn]


@router.post("/import")
async def import_tournament(payload: TournamentImportPayload,
                            db: AsyncSession = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items is empty")

    user = (await db.execute(
        select(User).where(User.hwid == payload.hwid)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Banned")

    collector = await _get_or_create_collector(payload.kingdom, payload.clan, user.id, db)

    player_aliases = {
        row.raw_name: row.canonical_name
        for row in (await db.execute(
            select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
        )).scalars().all()
    }

    incoming_names = set()
    for item in payload.items:
        canonical_name = player_aliases.get(item.name, item.name)
        incoming_names.add(canonical_name)

        existing = (await db.execute(
            select(AncientRoster).where(
                AncientRoster.collector_id == collector.id,
                AncientRoster.player_name == canonical_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.place = item.place
            existing.points = item.points
        else:
            db.add(AncientRoster(
                collector_id=collector.id, player_name=canonical_name,
                place=item.place, points=item.points, troop_level=None,
            ))

    await db.flush()
    await db.execute(
        delete(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name.not_in(incoming_names),
        )
    )

    await db.commit()
    return {"ok": True, "count": len(payload.items), "collector_slug": collector.slug}
```

`_get_or_create_collector` is currently a private (`_`-prefixed) helper in
`server/chests.py:52`. Importing it across modules is fine in this codebase (Python
doesn't enforce privacy), but check `server/chests.py` for any other module already
importing it cross-file before adding this import, to confirm the pattern is
acceptable — if not, ask before proceeding rather than silently renaming it.

- [ ] **Step 4: Register the router**

In `server/main.py`, find the block of `app.include_router(...)` calls (around line
83-93) and the corresponding imports at the top of the file. Add:

```python
from tournaments import router as tournaments_router
```

next to the other router imports, and:

```python
app.include_router(tournaments_router)
```

next to `app.include_router(chests_router)`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_tournaments.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add server/tournaments.py server/tests/test_tournaments.py server/main.py
git commit -m "feat(ancients): add tournament roster import endpoint"
```

---

## Task 4: Dashboard endpoints (roster view, troop_level edit, calculate, history)

**Files:**
- Create: `server/ancients_dashboard.py`
- Test: `server/tests/test_ancients_dashboard.py`
- Modify: `server/main.py`

**Interfaces:**
- Consumes: `ancient_quota.total_quota_millions`, `split_strategy_a`,
  `split_strategy_b`, `TROOP_STEPS` (Task 1); `AncientRoster`, `AncientCalculation`
  (Task 2); `get_web_user`, `_get_own_collector`-style ownership check (pattern from
  `server/chest_dashboard.py:197`).
- Produces: `router` (prefix `/web/dashboard/ancients`) registered in `main.py`.

- [ ] **Step 1: Write the failing tests**

Mirror the fixture style of `server/tests/test_chest_dashboard.py` (web-session auth
via JWT, not hwid) — check that file first for how a logged-in `User` + Bearer token is
obtained in tests, and copy that pattern. Then:

```python
# server/tests/test_ancients_dashboard.py
import pytest

from models import AncientCalculation, AncientRoster, ChestCollector


@pytest.mark.asyncio
async def test_get_roster_returns_players(auth_client, db_session, web_user):
    collector = ChestCollector(kingdom="K1", clan="C1", user_id=web_user.id, slug="s1")
    db_session.add(collector)
    await db_session.flush()
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                  place=1, points=100, troop_level="База 8"))
    await db_session.commit()

    resp = await auth_client.get("/web/dashboard/ancients")
    assert resp.status_code == 200
    data = resp.json()
    assert data["collectors"][0]["roster"][0]["player_name"] == "Иванов"
    assert data["collectors"][0]["roster"][0]["troop_level"] == "База 8"


@pytest.mark.asyncio
async def test_patch_troop_level(auth_client, db_session, web_user):
    collector = ChestCollector(kingdom="K2", clan="C2", user_id=web_user.id, slug="s2")
    db_session.add(collector)
    await db_session.flush()
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                  place=1, points=100, troop_level=None))
    await db_session.commit()

    resp = await auth_client.patch(
        "/web/dashboard/ancients/s2/troop-level",
        json={"player_name": "Петров", "troop_level": "Шаг 7.1"},
    )
    assert resp.status_code == 200

    row = (await db_session.execute(
        __import__("sqlalchemy").select(AncientRoster).where(
            AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.troop_level == "Шаг 7.1"


@pytest.mark.asyncio
async def test_calculate_strategy_a_saves_history(auth_client, db_session, web_user):
    collector = ChestCollector(kingdom="K3", clan="C3", user_id=web_user.id, slug="s3")
    db_session.add(collector)
    await db_session.flush()
    await db_session.commit()

    resp = await auth_client.post(
        "/web/dashboard/ancients/s3/calculate",
        json={
            "strategy": "A", "summon_levels": [81, 100],
            "amplification_coef": 1.5, "officer_count": 2, "veteran_count": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_quota_millions"] == pytest.approx((45.1 + 114) * 1.5)
    assert "officer_quota" in body["result"]

    rows = (await db_session.execute(
        __import__("sqlalchemy").select(AncientCalculation).where(
            AncientCalculation.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_calculate_history_capped_at_5(auth_client, db_session, web_user):
    collector = ChestCollector(kingdom="K4", clan="C4", user_id=web_user.id, slug="s4")
    db_session.add(collector)
    await db_session.flush()
    await db_session.commit()

    for _ in range(6):
        resp = await auth_client.post(
            "/web/dashboard/ancients/s4/calculate",
            json={
                "strategy": "A", "summon_levels": [81],
                "amplification_coef": 1.0, "officer_count": 1, "veteran_count": 0,
            },
        )
        assert resp.status_code == 200

    rows = (await db_session.execute(
        __import__("sqlalchemy").select(AncientCalculation).where(
            AncientCalculation.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_ancients_dashboard.py -v`
Expected: FAIL (404, route doesn't exist)

- [ ] **Step 3: Write the implementation**

```python
# server/ancients_dashboard.py
"""
ancients_dashboard.py — Личный кабинет, вкладка «Древний».

Auth: site session (JWT Bearer via get_web_user), как chest_dashboard.py — лидер
управляет только своими ChestCollector. Бесплатно для всех пользователей.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ancient_quota import (
    TROOP_QUOTA_PRESETS, TROOP_STEPS,
    split_strategy_a, split_strategy_b, total_quota_millions,
)
from database import get_db
from models import AncientCalculation, AncientRoster, ChestCollector, User
from web_routes import get_web_user

router = APIRouter(prefix="/web/dashboard/ancients", tags=["ancients-dashboard"])

HISTORY_LIMIT = 5


async def _get_own_collector(db: AsyncSession, slug: str, user: User) -> ChestCollector:
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    if collector.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your collector")
    return collector


async def _roster_rows(db: AsyncSession, collector_id: int) -> list:
    rows = (await db.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector_id)
        .order_by(AncientRoster.place.asc().nullslast())
    )).scalars().all()
    return [
        {"player_name": r.player_name, "place": r.place, "points": r.points,
         "troop_level": r.troop_level}
        for r in rows
    ]


async def _history_rows(db: AsyncSession, collector_id: int) -> list:
    rows = (await db.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector_id)
        .order_by(AncientCalculation.computed_at.desc())
    )).scalars().all()
    return [
        {"id": r.id, "computed_at": r.computed_at.isoformat(), "strategy": r.strategy,
         "total_quota_millions": r.total_quota_millions, "result": r.result_json}
        for r in rows
    ]


@router.get("")
async def get_dashboard_ancients(user: User = Depends(get_web_user),
                                 db: AsyncSession = Depends(get_db)):
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.user_id == user.id)
    )).scalars().all()

    result = []
    for collector in collectors:
        result.append({
            "slug": collector.slug, "kingdom": collector.kingdom, "clan": collector.clan,
            "roster": await _roster_rows(db, collector.id),
            "history": await _history_rows(db, collector.id),
            "troop_steps": TROOP_STEPS,
            "presets": sorted(TROOP_QUOTA_PRESETS.keys()),
        })
    return {"collectors": result}


class TroopLevelPayload(BaseModel):
    player_name: str
    troop_level: Optional[str] = None


@router.patch("/{slug}/troop-level")
async def patch_troop_level(slug: str, payload: TroopLevelPayload,
                            user: User = Depends(get_web_user),
                            db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    if payload.troop_level is not None and payload.troop_level not in TROOP_STEPS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown troop_level: {payload.troop_level!r}")

    row = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == payload.player_name,
        )
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Player not in roster")

    row.troop_level = payload.troop_level
    await db.commit()
    return {"ok": True}


class CalculatePayload(BaseModel):
    strategy: str
    summon_levels: List[int]
    amplification_coef: float
    clan_preset: Optional[str] = None
    officer_count: Optional[int] = None
    veteran_count: Optional[int] = None


@router.post("/{slug}/calculate")
async def calculate(slug: str, payload: CalculatePayload,
                    user: User = Depends(get_web_user),
                    db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)

    if payload.strategy not in ("A", "B"):
        raise HTTPException(status_code=400, detail="strategy must be 'A' or 'B'")
    if not payload.summon_levels or len(payload.summon_levels) > 6:
        raise HTTPException(status_code=400, detail="summon_levels must have 1-6 entries")

    total = total_quota_millions(payload.summon_levels, payload.amplification_coef)

    if payload.strategy == "A":
        if payload.officer_count is None or payload.veteran_count is None:
            raise HTTPException(status_code=400,
                                detail="officer_count and veteran_count are required for strategy A")
        try:
            result = split_strategy_a(total, payload.officer_count, payload.veteran_count)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        if payload.clan_preset not in TROOP_QUOTA_PRESETS:
            raise HTTPException(status_code=400, detail="clan_preset must be one of T5-T9")
        roster = (await db.execute(
            select(AncientRoster).where(AncientRoster.collector_id == collector.id)
        )).scalars().all()
        players = [(r.player_name, r.troop_level) for r in roster]
        try:
            result = split_strategy_b(total, payload.clan_preset, players)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    db.add(AncientCalculation(
        collector_id=collector.id, strategy=payload.strategy,
        clan_preset=payload.clan_preset, summon_levels=payload.summon_levels,
        amplification_coef=payload.amplification_coef,
        officer_count=payload.officer_count, veteran_count=payload.veteran_count,
        total_quota_millions=total, result_json=result,
    ))
    await db.flush()

    history_ids = (await db.execute(
        select(AncientCalculation.id)
        .where(AncientCalculation.collector_id == collector.id)
        .order_by(AncientCalculation.computed_at.desc())
    )).scalars().all()
    if len(history_ids) > HISTORY_LIMIT:
        stale_ids = history_ids[HISTORY_LIMIT:]
        await db.execute(delete(AncientCalculation).where(
            AncientCalculation.id.in_(stale_ids)))

    await db.commit()
    return {"total_quota_millions": total, "result": result}
```

- [ ] **Step 4: Register the router**

In `server/main.py`, add `from ancients_dashboard import router as ancients_dashboard_router`
next to the other dashboard imports, and `app.include_router(ancients_dashboard_router)`
next to `app.include_router(chest_dashboard_router)`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_ancients_dashboard.py -v`
Expected: all PASS

- [ ] **Step 6: Run the full backend suite to check for regressions**

Run: `cd server && python -m pytest -v`
Expected: all PASS (no regressions in chests/dashboard/etc.)

- [ ] **Step 7: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py server/main.py
git commit -m "feat(ancients): add dashboard endpoints (roster, troop-level, calculate, history)"
```

---

## Task 5: Rewrite `tournament_reader.py` to the hwid/kingdom/clan contract

**Files:**
- Modify: `tournament_reader.py`

**Interfaces:**
- Consumes: `auth.get_hwid()`, `auth.SERVER_URL` (existing, used by `chest_reader.py:23`).
- Produces: POSTs to `/api/v1/tournaments/import` with
  `{hwid, kingdom, clan, timestamp, items: [{name, place, points}]}`.

This is a standalone CLI script with no existing automated tests (confirmed via
`project_tournament_reader_spec` memory: "Standalone CLI script ... NOT in bot GUI/build").
Manual verification only, per the steps below — do not invent a pytest suite for it
unless one already exists in the repo (check `server/tests/` and the repo root for
`test_tournament*.py` before assuming there's none).

- [ ] **Step 1: Read the current contract end-to-end**

Read `tournament_reader.py` lines 1-90 and 330-374 (config loading, `export_to_api`,
`main`) before editing — confirm `load_config`/`CONFIG_PATH`/`API_IMPORT_PATH` and the
`export_to_api`/`main` functions match what's quoted below; if the file has changed
since this plan was written, stop and re-read the live file instead of patching blind.

- [ ] **Step 2: Replace config loading with kingdom/clan/hwid**

Remove `load_config`, `CONFIG_PATH`, and the `tournament_config.json` requirement
entirely. Replace the `# --- Config / API ---` block (`tournament_reader.py:72-88`) with:

```python
# --- Config / API ---
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import SERVER_URL, get_hwid  # noqa: E402

API_IMPORT_PATH = '/api/v1/tournaments/import'
```

(`sys.path.insert` mirrors how this standalone script already finds its own directory
for `CONFIG_PATH` — `auth.py` lives at the repo root next to `tournament_reader.py`, so
no path manipulation should actually be necessary if the script is run from the repo
root; verify by running `python -c "from auth import get_hwid"` from the repo root
before adding the `sys.path` hack, and drop it if the plain import already works.)

- [ ] **Step 3: Replace `export_to_api` and `main`**

Replace `export_to_api` (`tournament_reader.py:333-354`) with:

```python
def export_to_api(kingdom, clan, data, event_timestamp):
    items = list(data["leaderboard"])
    if data.get("own_data"):
        own_name = data["own_data"].get("name")
        if own_name and not any(row.get("name") == own_name for row in items):
            items.append(data["own_data"])

    payload = {
        "hwid": get_hwid(),
        "kingdom": kingdom,
        "clan": clan,
        "timestamp": event_timestamp,
        "items": [
            {"name": row["name"], "place": row.get("rank"), "points": row.get("points")}
            for row in items if row.get("name")
        ],
    }
    url = SERVER_URL + API_IMPORT_PATH

    try:
        response = requests.post(url, json=payload, timeout=10)
        if 200 <= response.status_code < 300:
            return True
    except requests.RequestException:
        pass

    filename = f"tournament_export_{int(time.time())}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Не удалось отправить данные на сервер. Сохранено локально: {filename}")
    return False
```

Replace `main` (`tournament_reader.py:357-374`) — drop `config = load_config()` and the
`alliance_tag` reference, take `kingdom`/`clan` as CLI args instead:

```python
def main():
    if len(sys.argv) < 3:
        print("Использование: python tournament_reader.py <kingdom> <clan>")
        return
    kingdom, clan = sys.argv[1], sys.argv[2]

    print("Откройте диалог «Статистика» в игре. Сбор начнётся через 3 секунды...")
    for i in (3, 2, 1):
        print(i)
        time.sleep(1)

    data = collect_tournament_data()

    print(f"Собрано строк: {len(data['leaderboard'])}")
    print(f"Своё место: {data['own_data']}")

    event_timestamp = datetime.datetime.now().isoformat(timespec='seconds')
    success = export_to_api(kingdom, clan, data, event_timestamp)

    if success:
        print("Данные успешно отправлены на сервер.")
```

- [ ] **Step 4: Manual smoke test**

Run: `python tournament_reader.py K229 BERS` with the game's «Статистика» dialog open
(same manual procedure as the existing live tests referenced in
`project_tournament_reader_spec` memory — e.g. `_live_test_tournament.py`'s setup).
Expected: console prints collected rows, then either "Данные успешно отправлены на
сервер." or a local `tournament_export_*.json` fallback file if the dev server isn't
reachable. Confirm in the dashboard (`GET /web/dashboard/ancients` once Task 4 is live)
that the roster updated.

- [ ] **Step 5: Commit**

```bash
git add tournament_reader.py
git commit -m "feat(ancients): rewrite tournament_reader.py to hwid/kingdom/clan contract"
```

(If `tournament_config.json` / `tournament_config.example.json` exist in the repo root
and are now unused, remove them in this same commit — check with `git status` first.)

---

## Task 6: Frontend — Ancients dashboard tab

**Files:**
- Modify: `web/src/api.js`
- Create: `web/src/pages/AncientsPage.jsx`
- Modify: `web/src/App.jsx`
- Modify: `web/src/components/Layout.jsx`
- Modify: `web/src/dashboard_content.js`
- Modify: `web/src/dashboard_content.en.js`

**Interfaces:**
- Consumes: `/web/dashboard/ancients` (GET), `/web/dashboard/ancients/{slug}/troop-level`
  (PATCH), `/web/dashboard/ancients/{slug}/calculate` (POST) — all from Task 4.
- Produces: `/dashboard/ancients` route, reachable from the sidebar nav.

- [ ] **Step 1: Add API helpers**

In `web/src/api.js`, next to the existing `dashboardChests*` entries (around line
43-52), add:

```js
  dashboardAncients:      ()              => request('GET',   '/web/dashboard/ancients'),
  dashboardAncientsTroopLevel: (slug, playerName, troopLevel) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/troop-level`,
            { player_name: playerName, troop_level: troopLevel }),
  dashboardAncientsCalculate: (slug, payload) =>
    request('POST', `/web/dashboard/ancients/${slug}/calculate`, payload),
```

- [ ] **Step 2: Add i18n strings**

In `web/src/dashboard_content.js`, find the `nav` object (around line 22, next to
`chests: 'Сундуки'`) and add `ancients: 'Древний'`. Find the top-level object (sibling
of the `chests:` block around line 42) and add:

```js
  ancients: {
    title: 'Древний',
    rosterTitle: 'Ростер клана',
    player: 'Игрок', place: 'Место', points: 'Очки', troopLevel: 'Уровень войск',
    noTroopLevel: 'не указан',
    calcTitle: 'Калькулятор нормы',
    summonsLabel: 'Количество вызовов',
    levelLabel: level => `Уровень вызова ${level}`,
    presetLabel: 'Прессет клана',
    amplificationLabel: 'Коэффициент усиления',
    strategyLabel: 'Стратегия',
    strategyA: 'А — по рангу', strategyB: 'Б — по уровню войск',
    officerCount: 'Офицеры', veteranCount: 'Ветераны',
    calculateButton: 'Рассчитать',
    totalQuota: 'Общая норма (млн)',
    officerQuota: 'Норма на офицера', veteranQuota: 'Норма на ветерана',
    excludedNote: 'Без указанного уровня войск (не учтены)',
    historyTitle: 'История расчётов',
    noRoster: 'Ростер пуст — запустите tournament_reader.py на машине лидера.',
  },
```

Do the same in `web/src/dashboard_content.en.js` with English copy (mirror the RU keys
exactly — `nav.ancients = 'Ancient'`, and an `ancients` block with the same key names
translated).

- [ ] **Step 3: Write the page component**

```jsx
// web/src/pages/AncientsPage.jsx
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

export default function AncientsPage() {
  const [collectors, setCollectors] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [formByCollector, setFormByCollector] = useState({})
  const [resultByCollector, setResultByCollector] = useState({})
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.ancients
  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Древний' : 'Total Hunter — Ancient',
    description: lang === 'ru' ? 'Калькулятор нормы урона по Древним.' : 'Ancient damage quota calculator.',
  })

  async function refresh() {
    try {
      const data = await api.dashboardAncients()
      setCollectors(data.collectors)
      const nextForm = {}
      for (const c of data.collectors) {
        nextForm[c.slug] = {
          strategy: 'A', summonCount: 1, levels: [100],
          preset: 'T8', amplification: 1.0, officerCount: 0, veteranCount: 0,
        }
      }
      setFormByCollector(prev => ({ ...nextForm, ...prev }))
    } catch (e) {
      setLoadError(e.message || 'failed to load')
    }
  }
  useEffect(() => { refresh() }, [])

  function updateForm(slug, patch) {
    setFormByCollector(prev => ({ ...prev, [slug]: { ...prev[slug], ...patch } }))
  }

  function updateSummonCount(slug, count) {
    const form = formByCollector[slug]
    const levels = Array.from({ length: count }, (_, i) => form.levels[i] || 100)
    updateForm(slug, { summonCount: count, levels })
  }

  function updateLevel(slug, index, value) {
    const form = formByCollector[slug]
    const levels = [...form.levels]
    levels[index] = Number(value)
    updateForm(slug, { levels })
  }

  async function handleTroopLevelChange(slug, playerName, troopLevel) {
    await api.dashboardAncientsTroopLevel(slug, playerName, troopLevel || null)
    refresh()
  }

  async function handleCalculate(slug) {
    const form = formByCollector[slug]
    const payload = {
      strategy: form.strategy,
      summon_levels: form.levels,
      amplification_coef: Number(form.amplification),
      clan_preset: form.strategy === 'B' ? form.preset : null,
      officer_count: form.strategy === 'A' ? Number(form.officerCount) : null,
      veteran_count: form.strategy === 'A' ? Number(form.veteranCount) : null,
    }
    const result = await api.dashboardAncientsCalculate(slug, payload)
    setResultByCollector(prev => ({ ...prev, [slug]: result }))
    refresh()
  }

  if (loadError) return <div>{loadError}</div>
  if (!collectors) return <div>...</div>

  return (
    <div>
      <h1>{cx.title}</h1>
      {collectors.map(c => {
        const form = formByCollector[c.slug] || {
          strategy: 'A', summonCount: 1, levels: [100],
          preset: 'T8', amplification: 1.0, officerCount: 0, veteranCount: 0,
        }
        const result = resultByCollector[c.slug]
        return (
          <div key={c.slug}>
            <h2>{c.kingdom} / {c.clan}</h2>

            <h3>{cx.rosterTitle}</h3>
            {c.roster.length === 0 ? <p>{cx.noRoster}</p> : (
              <table>
                <thead>
                  <tr>
                    <th>{cx.player}</th><th>{cx.place}</th><th>{cx.points}</th><th>{cx.troopLevel}</th>
                  </tr>
                </thead>
                <tbody>
                  {c.roster.map(p => (
                    <tr key={p.player_name}>
                      <td>{p.player_name}</td>
                      <td>{p.place ?? '—'}</td>
                      <td>{p.points ?? '—'}</td>
                      <td>
                        <select value={p.troop_level || ''}
                                onChange={e => handleTroopLevelChange(c.slug, p.player_name, e.target.value)}>
                          <option value="">{cx.noTroopLevel}</option>
                          {c.troop_steps.map(step => <option key={step} value={step}>{step}</option>)}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <h3>{cx.calcTitle}</h3>
            <label>
              {cx.summonsLabel}
              <select value={form.summonCount}
                      onChange={e => updateSummonCount(c.slug, Number(e.target.value))}>
                {[1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            {form.levels.map((level, i) => (
              <label key={i}>
                {cx.levelLabel(i + 1)}
                <input type="number" min={81} max={250} value={level}
                       onChange={e => updateLevel(c.slug, i, e.target.value)} />
              </label>
            ))}
            <label>
              {cx.amplificationLabel}
              <input type="number" step="0.01" value={form.amplification}
                     onChange={e => updateForm(c.slug, { amplification: e.target.value })} />
            </label>
            <label>
              {cx.strategyLabel}
              <select value={form.strategy}
                      onChange={e => updateForm(c.slug, { strategy: e.target.value })}>
                <option value="A">{cx.strategyA}</option>
                <option value="B">{cx.strategyB}</option>
              </select>
            </label>
            {form.strategy === 'A' ? (
              <>
                <label>
                  {cx.officerCount}
                  <input type="number" min={0} value={form.officerCount}
                         onChange={e => updateForm(c.slug, { officerCount: e.target.value })} />
                </label>
                <label>
                  {cx.veteranCount}
                  <input type="number" min={0} value={form.veteranCount}
                         onChange={e => updateForm(c.slug, { veteranCount: e.target.value })} />
                </label>
              </>
            ) : (
              <label>
                {cx.presetLabel}
                <select value={form.preset}
                        onChange={e => updateForm(c.slug, { preset: e.target.value })}>
                  {c.presets.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </label>
            )}
            <button onClick={() => handleCalculate(c.slug)}>{cx.calculateButton}</button>

            {result && (
              <div>
                <p>{cx.totalQuota}: {result.total_quota_millions.toFixed(1)}</p>
                {result.result.officer_quota !== undefined ? (
                  <>
                    <p>{cx.officerQuota}: {result.result.officer_quota.toFixed(2)}</p>
                    <p>{cx.veteranQuota}: {result.result.veteran_quota.toFixed(2)}</p>
                  </>
                ) : (
                  <table>
                    <thead><tr><th>{cx.player}</th><th>{cx.troopLevel}</th><th>{cx.totalQuota}</th></tr></thead>
                    <tbody>
                      {result.result.players.map(p => (
                        <tr key={p.name}><td>{p.name}</td><td>{p.troop_level}</td><td>{p.quota.toFixed(2)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {result.result.excluded && result.result.excluded.length > 0 && (
                  <p>{cx.excludedNote}: {result.result.excluded.join(', ')}</p>
                )}
              </div>
            )}

            <h3>{cx.historyTitle}</h3>
            <ul>
              {c.history.map(h => (
                <li key={h.id}>{h.computed_at} — {h.strategy} — {h.total_quota_millions.toFixed(1)}</li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Register the route**

In `web/src/App.jsx`, add `import AncientsPage from './pages/AncientsPage.jsx'` next to
the `ChestsPage` import (line 22), and inside the `/dashboard` route block add
`<Route path="ancients" element={<AncientsPage />} />` next to
`<Route path="chests" element={<ChestsPage />} />` (line 59).

- [ ] **Step 5: Add the nav entry**

In `web/src/components/Layout.jsx`, add `{ to: '/dashboard/ancients', icon: '🐲', key: 'ancients' }`
to the `NAV_KEYS` array next to the `chests` entry (line 15).

- [ ] **Step 6: Manual verification**

Run the web dev server (check `web/package.json` for the dev script, e.g. `npm run dev`
inside `web/`), log in, navigate to `/dashboard/ancients`, confirm the page loads
without console errors, the roster table renders (empty-state message if no roster
yet), and clicking «Рассчитать» with Strategy A and some officer/veteran counts shows a
result. This is a UI change — do not claim it works without having actually opened it
in a browser.

- [ ] **Step 7: Commit**

```bash
git add web/src/api.js web/src/pages/AncientsPage.jsx web/src/App.jsx \
        web/src/components/Layout.jsx web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "feat(ancients): add Древний dashboard tab (roster, calculator, history)"
```

---

## Out of scope (do not implement, tracked separately)

- Public PIN-protected self-report page (Part B of the original Gemini spec).
- Audit log / rollback / player lock / IP rate-limiting (Part C).
- Both are recorded in memory (`project_ancient_quota_calculator`) as deferred future
  work — do not pull them into this plan even if a task here seems to "need" them.
