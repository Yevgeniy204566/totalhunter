"""add_ancient_roster_manual_fields

Revision ID: m1n2u3a4l5r6
Revises: h1d3n4t5c6l7
Create Date: 2026-07-01

Manual roster entries (leader/editor adds a participant missing from both
the tournament OCR scan and the Chests name base): source distinguishes
'ocr' from 'manual' rows, manual_expires_at is the Trade-Routes-anchored
expiry (NULL for 'ocr' rows), rank is a display-only field for manual
entries (never used by the quota formulas).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'm1n2u3a4l5r6'
down_revision: Union[str, None] = 'h1d3n4t5c6l7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'ancient_roster',
        sa.Column('source', sa.String(8), nullable=False, server_default=sa.text("'ocr'")),
    )
    op.add_column(
        'ancient_roster',
        sa.Column('manual_expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'ancient_roster',
        sa.Column('rank', sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ancient_roster', 'rank')
    op.drop_column('ancient_roster', 'manual_expires_at')
    op.drop_column('ancient_roster', 'source')
