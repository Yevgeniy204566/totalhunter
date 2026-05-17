import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from earn import SECTORS, pick_sector, sector_to_angle, calculate_ad_reward

VALID_REWARDS = {5, 7, 15, 30, 50}


def test_sectors_has_20_elements():
    assert len(SECTORS) == 20


def test_sectors_contain_only_valid_rewards():
    assert set(SECTORS) == VALID_REWARDS


def test_pick_sector_returns_correct_value_for_each_reward():
    for reward in VALID_REWARDS:
        idx = pick_sector(reward)
        assert SECTORS[idx] == reward, f"pick_sector({reward}) → sector {idx} has value {SECTORS[idx]}"


def test_pick_sector_index_in_range():
    for reward in VALID_REWARDS:
        idx = pick_sector(reward)
        assert 0 <= idx < 20


def test_jackpot_sector_is_only_index_15():
    for _ in range(30):
        idx = pick_sector(50)
        assert idx == 15, f"50 must always be at index 15, got {idx}"


def test_sector_to_angle_formula():
    assert sector_to_angle(0)  == 9
    assert sector_to_angle(1)  == 27
    assert sector_to_angle(15) == 279
    assert sector_to_angle(19) == 351


def test_calculate_ad_reward_always_valid():
    for _ in range(200):
        r = calculate_ad_reward()
        assert r in VALID_REWARDS, f"Invalid reward: {r}"
