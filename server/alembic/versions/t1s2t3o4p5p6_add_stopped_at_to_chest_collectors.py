"""add stopped_at to chest_collectors

Revision ID: t1s2t3o4p5p6
Revises: s4k5u6r7a8c9
Create Date: 2026-06-26

Set by close_season_early endpoint. Background retention tick in chest_history.py
deletes collectors where stopped_at < now() - 90 days, cascading to all related records.
Cleared back to NULL when a new season is started (period_start/period_end set).
"""
from alembic import op
import sqlalchemy as sa

revision      = 't1s2t3o4p5p6'
down_revision = 's4k5u6r7a8c9'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column(
        'chest_collectors',
        sa.Column('stopped_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('chest_collectors', 'stopped_at')
