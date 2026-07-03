"""add_ancient_roster_raw_ocr_name

Revision ID: r2a3w4o5c6r7
Revises: s1h2o3r4t5f6
Create Date: 2026-07-03

Stores the last raw OCR text seen for a roster row, separate from
player_name (which becomes the row's stable canonical/display identity
once a name mapping is confirmed and physically merged).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'r2a3w4o5c6r7'
down_revision: Union[str, None] = 's1h2o3r4t5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'ancient_roster',
        sa.Column('raw_ocr_name', sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ancient_roster', 'raw_ocr_name')
