"""add clan_members table (ERP Phase 0)

Revision ID: c1l2a3n4m5b6
Revises: p1q2r3s4t5u6
Create Date: 2026-06-16

Stores clan roster collected by bot from 'My Clan -> Members' panel.
PK = name (unique player name). might uses BigInteger (values > 4B possible).
"""
from alembic import op
import sqlalchemy as sa

revision      = 'c1l2a3n4m5b6'
down_revision = 'p1q2r3s4t5u6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'clan_members',
        sa.Column('name',       sa.String(100),             nullable=False),
        sa.Column('rank',       sa.String(20),              nullable=False),
        sa.Column('might',      sa.BigInteger(),            nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('name', name=op.f('pk_clan_members')),
    )


def downgrade() -> None:
    op.drop_table('clan_members')
