"""add_roy_scout_finds

Revision ID: s3c4o5u6t7f8
Revises: b1a2c3k4s5e6
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa


revision = 's3c4o5u6t7f8'
down_revision = 'b1a2c3k4s5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'roy_scout_finds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kingdom', sa.Integer(), nullable=False),
        sa.Column('x', sa.Integer(), nullable=False),
        sa.Column('y', sa.Integer(), nullable=False),
        sa.Column('reporter_hwid', sa.String(16), nullable=False),
        sa.Column('found_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roy_scout_finds')),
    )
    # Единственный индекс таблицы — found_at (architecture-04.md:12,14). kingdom БЕЗ индекса:
    # GET /roy/scout-finds не фильтрует по kingdom, индексировать нечего.
    op.create_index(op.f('ix_roy_scout_finds_found_at'), 'roy_scout_finds', ['found_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_roy_scout_finds_found_at'), table_name='roy_scout_finds')
    op.drop_table('roy_scout_finds')
