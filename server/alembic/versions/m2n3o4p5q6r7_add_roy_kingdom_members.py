"""add roy_kingdom_members table

Revision ID: m2n3o4p5q6r7
Revises: k1g2s3t4a5t6
Create Date: 2026-05-23

Persistent hwid→kingdom mapping (no TTL).
Gives registered_count (grey dot) on the ROY dashboard page.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'm2n3o4p5q6r7'
down_revision = 'k1g2s3t4a5t6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'roy_kingdom_members',
        sa.Column('hwid',       sa.String(16),              nullable=False),
        sa.Column('kingdom',    sa.Integer(),               nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('hwid', name=op.f('pk_roy_kingdom_members')),
    )
    op.create_index(op.f('ix_roy_kingdom_members_kingdom'), 'roy_kingdom_members', ['kingdom'])


def downgrade() -> None:
    op.drop_index(op.f('ix_roy_kingdom_members_kingdom'), table_name='roy_kingdom_members')
    op.drop_table('roy_kingdom_members')
