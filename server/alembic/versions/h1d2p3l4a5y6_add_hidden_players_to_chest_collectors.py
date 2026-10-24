"""add_hidden_players_to_chest_collectors

Revision ID: h1d2p3l4a5y6
Revises: p1e2r3s4o5n6
Create Date: 2026-10-24 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h1d2p3l4a5y6'
down_revision: Union[str, Sequence[str], None] = 'p1e2r3s4o5n6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chest_collectors',
        sa.Column('hidden_players', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chest_collectors', 'hidden_players')
