"""multi-quota chests: quota_slot, collector.quotas, history.quotas_snapshot

Revision ID: q1u2o3t4a5s6
Revises: c1h2l3n4k5s6
Create Date: 2026-09-26

Несколько квот вместо тумблеров «В пресете»/«Считать в квоту» (спека
docs/superpowers/specs/2026-09-26-chest-multi-quota-design-01.md). Перенос сохраняет числа
публичной страницы: отмеченное «Считать в квоту» (и «в учёте») → квота 1; старая цель
target_chests → цель квоты 1 «Epic Crypts». counts_toward_quota и target_chests остаются в
БД для отката, кодом больше не используются.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'q1u2o3t4a5s6'
down_revision = 'c1h2l3n4k5s6'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('chest_configurations', sa.Column('quota_slot', sa.Integer(), nullable=True))
    op.add_column('chest_collectors',
                  sa.Column('quotas', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column('chest_season_history', sa.Column('quotas_snapshot', sa.JSON(), nullable=True))

    # Квота требует «в учёте»: counts без is_in_pattern сейчас и так скрыт целиком → NULL.
    op.execute("""
        UPDATE chest_configurations SET quota_slot = 1
        WHERE counts_toward_quota AND is_in_pattern
    """)
    op.execute("""
        UPDATE chest_collectors c
        SET quotas = json_build_array(json_build_object(
            'slot', 1, 'name', 'Epic Crypts', 'target', c.target_chests, 'mode', 'fixed'))
        WHERE c.target_chests IS NOT NULL
           OR EXISTS (SELECT 1 FROM chest_configurations cf
                      WHERE cf.collector_id = c.id AND cf.quota_slot = 1)
    """)

    op.create_check_constraint('ck_chest_config_quota_slot', 'chest_configurations',
                               'quota_slot IS NULL OR quota_slot IN (1, 2, 3)')
    op.create_check_constraint('ck_chest_config_slot_in_account', 'chest_configurations',
                               'quota_slot IS NULL OR is_in_pattern')


def downgrade():
    op.drop_constraint('ck_chest_config_slot_in_account', 'chest_configurations', type_='check')
    op.drop_constraint('ck_chest_config_quota_slot', 'chest_configurations', type_='check')
    op.drop_column('chest_season_history', 'quotas_snapshot')
    op.drop_column('chest_collectors', 'quotas')
    op.drop_column('chest_configurations', 'quota_slot')
