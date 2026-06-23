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
