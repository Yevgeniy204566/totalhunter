"""add clan_roster table

Revision ID: r1o2s3t4e5r6
Revises: x1y2z3a4b5c6
Create Date: 2026-06-29

Per-collector clan roster for leader-editable OCR name corrections from clan chat.
Same pattern as player_aliases but separate table for roster-specific use.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'r1o2s3t4e5r6'
down_revision = 'a9b8c7d6e5f4'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'clan_roster',
        sa.Column('id',             sa.Integer(),    nullable=False),
        sa.Column('collector_id',   sa.Integer(),    nullable=False),
        sa.Column('raw_name',       sa.String(100),  nullable=False),
        sa.Column('canonical_name', sa.String(100),  nullable=False),
        sa.ForeignKeyConstraint(['collector_id'], ['chest_collectors.id'],
                                name=op.f('fk_clan_roster_collector_id_chest_collectors')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_clan_roster')),
        sa.UniqueConstraint('collector_id', 'raw_name',
                            name='uq_clan_roster_raw_name'),
    )
    op.create_index('ix_clan_roster_collector_id', 'clan_roster', ['collector_id'])


def downgrade() -> None:
    op.drop_index('ix_clan_roster_collector_id', table_name='clan_roster')
    op.drop_table('clan_roster')
