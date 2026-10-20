"""Перенос квот в модель «две квоты + тумблер Героя» (alembic p1e2r3s4o5n6): ничего не теряем."""
import importlib.util
import os

_p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic", "versions",
                  "p1e2r3s4o5n6_personal_scale_two_quotas.py")
_spec = importlib.util.spec_from_file_location("mig_personal", _p)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)
convert = mig.convert

HERO = {"norm": 1.2, "weights": 0.9, "ranges": []}


def test_fixed_clan_unchanged_no_personal():
    qs = [{"slot": 1, "name": "Склепы", "target": 200, "mode": "fixed"},
          {"slot": 2, "name": "EM", "target": 100, "mode": "fixed"}]
    new, personal = convert(qs)
    assert new == qs and personal is None


def test_eldorado_three_hero_points_slots():
    qs = [{"slot": 1, "name": "Epic Crypts", "target": 200, "mode": "hero_points", "hero": HERO},
          {"slot": 2, "name": "E M C", "target": 50, "mode": "hero_points", "hero": HERO},
          {"slot": 3, "name": "ALL", "target": None, "mode": "hero_points", "hero": HERO}]
    new, personal = convert(qs)
    assert [q["slot"] for q in new] == [1, 2]
    assert new[0] == {"slot": 1, "name": "Epic Crypts", "target": 200, "mode": "fixed"}
    assert new[1]["mode"] == "emc_table" and new[1]["target"] == 50 and new[1]["emc"]["global"] == 1.0
    assert personal == {"crypts": True, "emc": True, "norm": 1.2, "weights": 0.9, "ranges": []}


def test_existing_emc_levers_kept():
    emc = {"global": 1.3, "monsters": {"hydra": 1, "undead": 1, "arachna": 1, "shadow": 1}, "ranges": []}
    qs = [{"slot": 2, "name": "EMC", "target": 50, "mode": "emc_table", "emc": emc}]
    new, personal = convert(qs)
    assert new[0]["emc"] == emc and personal["emc"] is True


def test_personal_without_slot2_creates_emc():
    new, personal = convert([{"slot": 1, "name": "C", "target": 5, "mode": "per_player"}])
    assert [q["slot"] for q in new] == [1, 2] and new[1]["name"] == "EMC" and personal["emc"]


def test_empty_quotas_stay_empty():
    assert convert([]) == ([], None) and convert(None) == ([], None)
