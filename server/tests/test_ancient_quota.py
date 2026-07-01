import pytest

from ancient_quota import (
    ANCIENT_LEVEL_HP, VALID_PRESETS,
    _tier_factor, troop_weight, parse_troop_level,
    total_quota_millions, split_strategy_a, split_strategy_b,
)
from ancient_quota import shortfall_pct


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


def test_shortfall_pct_basic_case():
    assert shortfall_pct(100, 50) == pytest.approx(50.0)


def test_shortfall_pct_zero_shortfall():
    assert shortfall_pct(100, 100) == pytest.approx(0.0)


def test_shortfall_pct_full_miss():
    assert shortfall_pct(100, 0) == pytest.approx(100.0)


def test_shortfall_pct_zero_quota_returns_none():
    # Division-by-zero guard — owner-mandated explicit test.
    assert shortfall_pct(0, 50) is None


def test_shortfall_pct_overshoot_is_negative_not_an_error():
    # Owner-mandated: exceeding quota must not raise, and must be negative
    # (falls into the "no highlight" zone at the call site, not a special case here).
    assert shortfall_pct(100, 150) == pytest.approx(-50.0)


def test_shortfall_pct_none_quota_returns_none():
    assert shortfall_pct(None, 50) is None


def test_shortfall_pct_none_points_returns_none():
    assert shortfall_pct(100, None) is None
