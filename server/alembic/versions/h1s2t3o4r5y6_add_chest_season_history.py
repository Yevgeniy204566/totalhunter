"""add chest_season_history table

Revision ID: h1s2t3o4r5y6
Revises: s1e2a3s4o5n6
Create Date: 2026-06-23

Frozen per-season snapshot — summary_json + target snapshots never get
recomputed after insert. Raw chests rows for an archived period are deleted
by the application code (chest_history.py), not by this migration.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'h1s2t3o4r5y6'
down_revision = 's1e2a3s4o5n6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'chest_season_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(),
                  sa.ForeignKey('chest_collectors.id'), nullable=False),
        sa.Column('period_start', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('period_end', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('target_points_snapshot', sa.Integer(), nullable=True),
        sa.Column('target_chests_snapshot', sa.Integer(), nullable=True),
        sa.Column('summary_json', sa.JSON(), nullable=False),
        sa.Column('closed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_chest_season_history_collector_id',
                    'chest_season_history', ['collector_id'])


def downgrade() -> None:
    op.drop_index('ix_chest_season_history_collector_id',
                  table_name='chest_season_history')
    op.drop_table('chest_season_history')
