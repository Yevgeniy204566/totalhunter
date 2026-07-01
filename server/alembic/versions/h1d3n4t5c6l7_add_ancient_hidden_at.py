"""add_ancient_hidden_at

Revision ID: h1d3n4t5c6l7
Revises: a9h2i3d4e5n6
Create Date: 2026-07-01

Timer for the "hidden and unused for 60 days -> Ancient data auto-purged"
retention rule. NULL means "not counting down" (visible, or never hidden).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'h1d3n4t5c6l7'
down_revision: Union[str, None] = 'a9h2i3d4e5n6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_hidden_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('chest_collectors', 'ancient_hidden_at')
