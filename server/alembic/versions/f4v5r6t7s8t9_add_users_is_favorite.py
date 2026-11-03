"""add_users_is_favorite

Revision ID: f4v5r6t7s8t9
Revises: h1d2p3l4a5y6
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4v5r6t7s8t9'
down_revision: Union[str, Sequence[str], None] = 'h1d2p3l4a5y6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users',
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_favorite')
