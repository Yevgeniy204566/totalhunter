"""personal_scale: тумблеры «Персонализированный учёт по Герою» по каждой квоте, квот две (Crypts, EMC)

Revision ID: p1e2r3s4o5n6
Revises: l1a2s3t4i5m6
Create Date: 2026-10-20

Квот у клана две (слот 1 Crypts, слот 2 EMC); «Всего» — производная, не слот. Личная цель по Герою
включается тумблером на каждой квоте (crypts/emc) клана chest_collectors.personal_scale = {crypts, emc, norm, weights, ranges}
(NULL = выключено). Перенос не меняет то, что клан уже настроил: режимы hero_points/emc_table/per_player
→ оба тумблера включены, слот 2 = emc_table; слот 3 убирается, его сундуки остаются «в учёте».
Старые режимы в историях сезонов (quotas_snapshot) не трогаем — архив читается как раньше.
"""
import json

from alembic import op
import sqlalchemy as sa

revision = 'p1e2r3s4o5n6'
down_revision = 'l1a2s3t4i5m6'
branch_labels = None
depends_on = None

_PERSONAL_MODES = {"hero_points", "emc_table", "per_player"}
_DEFAULT_EMC = {"global": 1.0, "monsters": {"hydra": 1.0, "undead": 1.0, "arachna": 1.0, "shadow": 1.0},
                "ranges": [{"from": 100, "to": 299, "k": 1.0}, {"from": 300, "to": 399, "k": 1.0},
                           {"from": 400, "to": 499, "k": 1.0}, {"from": 500, "to": 600, "k": 1.0}]}


def convert(quotas):
    """(новые квоты, personal_scale|None). Чистая функция — проверяется в тесте."""
    quotas = quotas or []
    personal = None
    for q in quotas:
        if q.get("mode") in _PERSONAL_MODES:
            hero = q.get("hero") or {}
            personal = personal or {"crypts": True, "emc": True, "norm": hero.get("norm", 1.0),
                                    "weights": hero.get("weights", 1.0), "ranges": hero.get("ranges", [])}
    out = []
    for q in quotas:
        slot = q.get("slot")
        if slot not in (1, 2):
            continue
        new = {"slot": slot, "name": q.get("name"), "target": q.get("target"), "mode": "fixed"}
        if slot == 2 and personal:
            new["mode"] = "emc_table"
            new["emc"] = q.get("emc") or _DEFAULT_EMC
        elif q.get("emc"):
            new["emc"] = q["emc"]
        out.append(new)
    if personal and not any(q["slot"] == 2 for q in out):
        out.append({"slot": 2, "name": "EMC", "target": None, "mode": "emc_table", "emc": _DEFAULT_EMC})
        out.sort(key=lambda q: q["slot"])
    return out, personal


def upgrade():
    op.add_column('chest_collectors', sa.Column('personal_scale', sa.JSON(), nullable=True))
    bind = op.get_bind()
    for cid, quotas in bind.execute(sa.text("SELECT id, quotas FROM chest_collectors")).fetchall():
        if isinstance(quotas, str):
            quotas = json.loads(quotas)
        new, personal = convert(quotas)
        if new == (quotas or []) and personal is None:
            continue
        bind.execute(sa.text("UPDATE chest_collectors SET quotas = CAST(:q AS json), "
                             "personal_scale = CAST(:p AS json) WHERE id = :id"),
                     {"q": json.dumps(new), "p": json.dumps(personal) if personal else None, "id": cid})
    # слота 3 больше нет: сундуки остаются «в учёте» (is_in_pattern не трогаем)
    op.execute("UPDATE chest_configurations SET quota_slot = NULL WHERE quota_slot = 3")


def downgrade():
    op.drop_column('chest_collectors', 'personal_scale')
