# Ancient Troop Weight Geometric Formula Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 13-entry diagonal `TROOP_QUOTA_PRESETS` lookup table in the Ancient
quota calculator (Strategy B) with a geometric formula (`1.8^(tier-5)` per troop tier)
that works for any independent G/S/M tier combination, since the roster UI now collects
G/S/M tiers via three separate selects instead of one combined dropdown.

**Architecture:** `server/ancient_quota.py` gets three new pure functions
(`_tier_factor`, `troop_weight`, `parse_troop_level`) replacing `TROOP_STEPS` and
`TROOP_QUOTA_PRESETS`. `split_strategy_b` calls the new functions instead of dict lookups.
`server/ancients_dashboard.py` is rewired to the new names — request validation goes
from list-membership to regex-based parsing.

**Tech Stack:** Python 3.13, pytest + pytest-asyncio, FastAPI, no new dependencies.

## Global Constraints

- Storage format of `AncientRoster.troop_level` (`"G# S# M#"` string) does not change —
  no DB migration.
- `split_strategy_b(total, preset, players)` public signature does not change — only its
  internals and the shape of weights it looks up.
- Frontend (`AncientsPage.jsx`) is not touched — it already sends the same string format.
- Design source of truth: `docs/superpowers/specs/2026-07-01-ancient-troop-weight-geometric-formula-design.md`.

---

### Task 1: Geometric weight formula in `ancient_quota.py`

**Files:**
- Modify: `server/ancient_quota.py:1-11` (imports), `server/ancient_quota.py:43-127` (replace `TROOP_STEPS`/`TROOP_QUOTA_PRESETS`/`split_strategy_b`)
- Modify: `server/tests/test_ancient_quota.py` (replace tests for removed constants, add new tests)

**Interfaces:**
- Produces: `VALID_PRESETS: set[str]`, `_tier_factor(tier: int) -> float`,
  `troop_weight(preset: str, g: int, s: int, m: int) -> float`,
  `parse_troop_level(troop_level: str) -> tuple[int, int, int]` (raises `ValueError` on
  malformed input), `split_strategy_b(total, preset, players)` (signature unchanged,
  internals changed).
- Consumes: nothing new (pure functions, no DB/network).

- [ ] **Step 1: Write the failing tests for the new functions**

Replace lines 1-91 of `server/tests/test_ancient_quota.py` (everything up to
`test_total_quota_millions_sums_and_amplifies`, which stays) with:

```python
import pytest

from ancient_quota import (
    ANCIENT_LEVEL_HP, VALID_PRESETS,
    _tier_factor, troop_weight, parse_troop_level,
    total_quota_millions, split_strategy_a, split_strategy_b,
)


def test_ancient_level_hp_covers_full_range():
    assert set(ANCIENT_LEVEL_HP.keys()) == set(range(81, 251))
    assert ANCIENT_LEVEL_HP[81] == 45.1
    assert ANCIENT_LEVEL_HP[250] == 18100.0


def test_ancient_level_hp_monotonically_increasing():
    levels = sorted(ANCIENT_LEVEL_HP)
    for a, b in zip(levels, levels[1:]):
        assert ANCIENT_LEVEL_HP[b] > ANCIENT_LEVEL_HP[a]


def test_valid_presets_are_t5_through_t9():
    assert VALID_PRESETS == {"T5", "T6", "T7", "T8", "T9"}


def test_tier_factor_geometric_progression():
    assert _tier_factor(5) == pytest.approx(1.0)
    assert _tier_factor(6) == pytest.approx(1.8)
    assert _tier_factor(7) == pytest.approx(3.24)
    assert _tier_factor(8) == pytest.approx(5.832)
    assert _tier_factor(9) == pytest.approx(10.4976)


def test_troop_weight_matches_own_preset_tier_exactly():
    # A player whose G/S/M all match the clan's preset tier always gets weight 1.0,
    # for every preset — this is the cap rule from the old manual table.
    for preset, tier in [("T5", 5), ("T6", 6), ("T7", 7), ("T8", 8), ("T9", 9)]:
        assert troop_weight(preset, tier, tier, tier) == pytest.approx(1.0)


def test_troop_weight_caps_at_one_above_preset_tier():
    # Player's tier is higher than the preset -> weight is capped at 1.0, not > 1.0.
    assert troop_weight("T7", 9, 9, 9) == pytest.approx(1.0)
    assert troop_weight("T5", 9, 8, 9) == pytest.approx(1.0)


def test_troop_weight_matches_old_manual_table_within_tolerance():
    # Spot-checks against docs/superpowers/specs/2026-06-23-ancient-quota-calculator-design.md
    # (the old TROOP_QUOTA_PRESETS values), tolerance +/-0.05 as agreed with the owner.
    assert troop_weight("T8", 5, 5, 5) == pytest.approx(0.15, abs=0.05)
    assert troop_weight("T8", 6, 6, 6) == pytest.approx(0.30, abs=0.05)
    assert troop_weight("T8", 7, 7, 7) == pytest.approx(0.55, abs=0.05)
    assert troop_weight("T9", 8, 8, 8) == pytest.approx(0.55, abs=0.05)
    assert troop_weight("T9", 7, 7, 7) == pytest.approx(0.30, abs=0.05)
    assert troop_weight("T9", 6, 6, 6) == pytest.approx(0.15, abs=0.05)


def test_troop_weight_handles_independent_non_diagonal_combos():
    # This is the entire point of the feature: combos that never existed in the old
    # 13-entry diagonal table must compute without raising.
    w = troop_weight("T8", 7, 9, 8)
    assert 0.0 < w <= 1.0
    # Raising any single tier should never decrease the weight.
    assert troop_weight("T8", 8, 9, 8) >= w


def test_parse_troop_level_valid():
    assert parse_troop_level("G7 S7 M8") == (7, 7, 8)
    assert parse_troop_level("G5 S9 M5") == (5, 9, 5)


def test_parse_troop_level_rejects_tier_out_of_range():
    with pytest.raises(ValueError):
        parse_troop_level("G10 S7 M8")
    with pytest.raises(ValueError):
        parse_troop_level("G4 S7 M8")


def test_parse_troop_level_rejects_wrong_letter_order():
    with pytest.raises(ValueError):
        parse_troop_level("S7 G7 M8")


def test_parse_troop_level_rejects_garbage():
    with pytest.raises(ValueError):
        parse_troop_level("not a troop level")
```

Then, further down in the same file, replace the three `test_split_strategy_b_*` tests
(currently referencing `TROOP_QUOTA_PRESETS`) with:

```python
def test_split_strategy_b_basic():
    players = [("Иванов", "G8 S8 M8"), ("Петров", "G7 S7 M8")]
    result = split_strategy_b(total=100.0, preset="T8", players=players)
    w_ivanov = troop_weight("T8", 8, 8, 8)
    w_petrov = troop_weight("T8", 7, 7, 8)
    denom = w_ivanov + w_petrov
    by_name = {p["name"]: p["quota"] for p in result["players"]}
    assert by_name["Иванов"] == pytest.approx(100.0 * w_ivanov / denom)
    assert by_name["Петров"] == pytest.approx(100.0 * w_petrov / denom)
    assert result["excluded"] == []


def test_split_strategy_b_excludes_missing_troop_level():
    players = [("Иванов", "G8 S8 M8"), ("Безуровневый", None)]
    result = split_strategy_b(total=100.0, preset="T8", players=players)
    names_in_result = {p["name"] for p in result["players"]}
    assert "Безуровневый" not in names_in_result
    assert result["excluded"] == ["Безуровневый"]


def test_split_strategy_b_all_excluded_raises():
    with pytest.raises(ValueError):
        split_strategy_b(total=100.0, preset="T8", players=[("Никто", None)])


def test_split_strategy_b_handles_non_diagonal_combo():
    # The scenario the whole feature exists for: a player with an independent G/S/M
    # combo that was never a valid key in the old 13-entry table.
    players = [("Игрок", "G7 S9 M8")]
    result = split_strategy_b(total=100.0, preset="T8", players=players)
    assert result["players"][0]["name"] == "Игрок"
    assert result["players"][0]["quota"] == pytest.approx(100.0)
    assert result["excluded"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_ancient_quota.py -v`
Expected: FAIL — `ImportError: cannot import name 'VALID_PRESETS' from 'ancient_quota'`
(the module doesn't have the new names yet).

- [ ] **Step 3: Implement the new formula in `ancient_quota.py`**

Add `import re` as the first line of `server/ancient_quota.py` (before the module
docstring's closing — place it right after the docstring block, i.e. after the existing
line 6 `"""`).

Replace lines 43-127 of `server/ancient_quota.py` (from the `# 13-ступенчатая матрица...`
comment through the end of the old `split_strategy_b`) with:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_ancient_quota.py -v`
Expected: PASS — all tests green, no import errors.

- [ ] **Step 5: Commit**

```bash
git add server/ancient_quota.py server/tests/test_ancient_quota.py
git commit -m "$(cat <<'EOF'
feat(ancients): geometric 1.8x-per-tier troop weight formula

Replaces the 13-entry diagonal TROOP_QUOTA_PRESETS lookup with a formula
that covers any independent G/S/M tier combination, since the roster UI
now collects G/S/M via three separate selects instead of one dropdown.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Wire `ancients_dashboard.py` to the new module

**Files:**
- Modify: `server/ancients_dashboard.py:21-24` (import), `server/ancients_dashboard.py:198-199` (dashboard payload), `server/ancients_dashboard.py:236-238` (PATCH validation), `server/ancients_dashboard.py:372-373` (calculate validation)
- Modify: `server/tests/test_ancients_dashboard.py` (add 2 new tests)

**Interfaces:**
- Consumes: `VALID_PRESETS`, `parse_troop_level` from Task 1 (`server/ancient_quota.py`).
- Produces: nothing new for later tasks — this is the final integration point.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py`, near the existing
`test_patch_troop_level` test (around line 56):

```python
@pytest.mark.asyncio
async def test_patch_troop_level_accepts_non_diagonal_combo(db_session):
    """A combo like G7 S9 M8 was rejected by the old 13-entry TROOP_STEPS list —
    it must now be accepted since G/S/M are entered independently."""
    user, token = await _create_user_with_token(db_session, "nondiag1@test.com")
    collector = await _create_collector(db_session, user.id, slug="nondiag-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/nondiag-1/troop-level",
            json={"player_name": "Петров", "troop_level": "G7 S9 M8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_patch_troop_level_rejects_malformed_value(db_session):
    user, token = await _create_user_with_token(db_session, "malformed1@test.com")
    collector = await _create_collector(db_session, user.id, slug="malformed-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/malformed-1/troop-level",
            json={"player_name": "Петров", "troop_level": "G10 S9 M8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && python -m pytest tests/test_ancients_dashboard.py -k troop_level -v`
Expected: `test_patch_troop_level_accepts_non_diagonal_combo` FAILS with 400 (old
`TROOP_STEPS` list-membership check still active, `"G7 S9 M8"` isn't one of the 13
strings). `test_patch_troop_level_rejects_malformed_value` currently passes by accident
(also rejected by the same list-membership check) — that's fine, Step 4 must keep it
passing for the right reason.

- [ ] **Step 3: Rewire the dashboard module**

Replace `server/ancients_dashboard.py:21-24`:
```python
from ancient_quota import (
    ANCIENT_LEVEL_HP, TROOP_QUOTA_PRESETS, TROOP_STEPS,
    split_strategy_a, split_strategy_b, total_quota_millions,
)
```
with:
```python
from ancient_quota import (
    ANCIENT_LEVEL_HP, VALID_PRESETS, parse_troop_level,
    split_strategy_a, split_strategy_b, total_quota_millions,
)
```

Replace `server/ancients_dashboard.py:198-199`:
```python
            "troop_steps": TROOP_STEPS,
            "presets": sorted(TROOP_QUOTA_PRESETS.keys()),
```
with:
```python
            "presets": sorted(VALID_PRESETS),
```

Replace `server/ancients_dashboard.py:236-238`:
```python
    if payload.troop_level is not None and payload.troop_level not in TROOP_STEPS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown troop_level: {payload.troop_level!r}")
```
with:
```python
    if payload.troop_level is not None:
        try:
            parse_troop_level(payload.troop_level)
        except ValueError:
            raise HTTPException(status_code=400,
                                detail=f"Unknown troop_level: {payload.troop_level!r}")
```

Replace `server/ancients_dashboard.py:372-373`:
```python
        if payload.clan_preset not in TROOP_QUOTA_PRESETS:
            raise HTTPException(status_code=400, detail="clan_preset must be one of T5-T9")
```
with:
```python
        if payload.clan_preset not in VALID_PRESETS:
            raise HTTPException(status_code=400, detail="clan_preset must be one of T5-T9")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_ancients_dashboard.py -v`
Expected: PASS — full file green, including the two new tests and all pre-existing ones
(`test_calculate_strategy_b_uses_confirmed_mapped_name`,
`test_roster_uses_profile_troop_level_as_fallback`, etc. — none of them assert exact
quota numbers for Strategy B, only structural things like which names appear, so they
are unaffected by the formula change).

- [ ] **Step 5: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): accept independent G/S/M troop combos in dashboard API

PATCH /{slug}/troop-level and POST /{slug}/calculate now validate against
the geometric formula's tier range (5-9 per letter) instead of the old
13-entry diagonal whitelist.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Full regression run

**Files:** none (verification only).

- [ ] **Step 1: Run the full server test suite**

Run: `cd server && python -m pytest -v`
Expected: PASS — every test in `server/tests/` green, in particular
`test_ancient_retention.py` and `test_ancients_dashboard.py` (both touch
`AncientRoster.troop_level` extensively) and `test_ancient_quota.py`.

- [ ] **Step 2: Grep for any remaining references to the removed constants**

Run: `grep -rn "TROOP_STEPS\|TROOP_QUOTA_PRESETS" server/ web/src/`
Expected: no output (both names fully removed from backend; frontend never referenced
them directly — it consumes `c.presets`, unaffected).

## Self-Review Notes

- Spec coverage: formula (Task 1), dashboard validation + calculate endpoint (Task 2),
  dead `troop_steps` payload key removal (Task 2), no-migration guarantee (Task 1 keeps
  string storage format, verified by `test_split_strategy_b_basic` reusing the same
  diagonal strings as before), no frontend change (verified no `Modify` entry touches
  `web/`) — all covered.
- Placeholder scan: none found — every step has literal code/commands.
- Type consistency: `troop_weight(preset: str, g: int, s: int, m: int)` and
  `parse_troop_level(troop_level: str) -> tuple[int, int, int]` are used identically in
  both `ancient_quota.py` and the test files across all three tasks.
