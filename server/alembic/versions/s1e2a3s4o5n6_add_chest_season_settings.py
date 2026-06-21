"""add season settings to chest_collectors, counts_toward_quota to chest_configurations

Revision ID: s1e2a3s4o5n6
Revises: c4d5e6f7g8h9
Create Date: 2026-06-21

All 6 new columns are nullable or have a server_default — existing rows need no
backfill. NULL season fields mean "season not configured" for that collector.
"""
from alembic import op
import sqlalchemy as sa

revision      = 's1e2a3s4o5n6'
down_revision = 'c4d5e6f7g8h9'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column('chest_collectors', sa.Column('timezone_offset_minutes', sa.Integer(), nullable=True))
    op.add_column('chest_collectors', sa.Column('period_start', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chest_collectors', sa.Column('period_end', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chest_collectors', sa.Column('target_points', sa.Integer(), nullable=True))
    op.add_column('chest_collectors', sa.Column('target_chests', sa.Integer(), nullable=True))
    op.add_column('chest_configurations', sa.Column('counts_toward_quota', sa.Boolean(),
                                                     nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('chest_configurations', 'counts_toward_quota')
    op.drop_column('chest_collectors', 'target_chests')
    op.drop_column('chest_collectors', 'target_points')
    op.drop_column('chest_collectors', 'period_end')
    op.drop_column('chest_collectors', 'period_start')
    op.drop_column('chest_collectors', 'timezone_offset_minutes')
