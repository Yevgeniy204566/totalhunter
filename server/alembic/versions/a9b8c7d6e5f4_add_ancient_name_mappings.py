"""add_ancient_name_mappings

Revision ID: a9b8c7d6e5f4
Revises: x1y2z3a4b5c6
Create Date: 2026-06-28 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = 'x1y2z3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ancient_name_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey(
            'chest_collectors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('raw_ocr_name', sa.String(200), nullable=False),
        sa.Column('canonical_name', sa.String(200), nullable=False),
        sa.Column('confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collector_id', 'raw_ocr_name',
                            name='uq_ancient_name_mapping'),
    )
    op.create_index('ix_ancient_name_mappings_lookup',
                    'ancient_name_mappings', ['collector_id', 'raw_ocr_name'])


def downgrade() -> None:
    op.drop_index('ix_ancient_name_mappings_lookup',
                  table_name='ancient_name_mappings')
    op.drop_table('ancient_name_mappings')
