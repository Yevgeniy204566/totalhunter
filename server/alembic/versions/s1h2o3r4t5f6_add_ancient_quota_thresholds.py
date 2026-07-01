"""add_ancient_quota_thresholds

Revision ID: s1h2o3r4t5f6
Revises: m1n2u3a4l5r6
Create Date: 2026-07-01

Three leader-configurable percentage thresholds (light/medium/critical) driving
roster-row conditional formatting for quota shortfall. NULL means "use the
application-level default" (10/30/60) — not stored as a DB server_default so the
distinction between "never configured" and "explicitly set to 10" stays visible.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 's1h2o3r4t5f6'
down_revision: Union[str, None] = 'm1n2u3a4l5r6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_shortfall_light_pct', sa.Float(), nullable=True),
    )
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_shortfall_medium_pct', sa.Float(), nullable=True),
    )
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_shortfall_critical_pct', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('chest_collectors', 'ancient_shortfall_critical_pct')
    op.drop_column('chest_collectors', 'ancient_shortfall_medium_pct')
    op.drop_column('chest_collectors', 'ancient_shortfall_light_pct')
