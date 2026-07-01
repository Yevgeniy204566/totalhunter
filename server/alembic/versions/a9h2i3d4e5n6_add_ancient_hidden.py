"""add_ancient_hidden

Revision ID: a9h2i3d4e5n6
Revises: e1d2i3t4o5r6
Create Date: 2026-07-01

«Скрыть коллектор» во вкладке «Древний» — коллектор общий с Сундуками,
поэтому вместо удаления (риск потерять историю Сундуков) он просто
перестаёт показываться в списке /web/dashboard/ancients, данные не трогаются.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a9h2i3d4e5n6'
down_revision: Union[str, None] = 'e1d2i3t4o5r6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_hidden', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('chest_collectors', 'ancient_hidden')
