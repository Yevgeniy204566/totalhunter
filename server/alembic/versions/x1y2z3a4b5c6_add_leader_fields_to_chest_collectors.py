"""add_leader_fields_to_chest_collectors

Revision ID: x1y2z3a4b5c6
Revises: ('p1r2o3f4i5l6', 't1s2t3o4p5p6')
Create Date: 2026-06-28 19:20:39.947529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'x1y2z3a4b5c6'
down_revision: Union[str, Sequence[str], None] = ('p1r2o3f4i5l6', 't1s2t3o4p5p6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chest_collectors',
        sa.Column('leader_canonical_name', sa.String(200), nullable=True))
    op.add_column('chest_collectors',
        sa.Column('leader_excluded_catalog_ids', sa.JSON(), nullable=False,
                  server_default=sa.text("'[]'")))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chest_collectors', 'leader_excluded_catalog_ids')
    op.drop_column('chest_collectors', 'leader_canonical_name')
