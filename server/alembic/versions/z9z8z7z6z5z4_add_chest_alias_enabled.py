"""add chest_type_aliases.enabled — per-type include/exclude toggle independent of canonical name

Revision ID: z9z8z7z6z5z4
Revises: q1w2e3r4t5y6
Create Date: 2026-06-20

Lets the owner exclude a raw chest type from the summary entirely before (or instead of)
mapping it to an English canonical name — decoupling "do we count this at all" from
"what's its English/points mapping."
"""
from alembic import op
import sqlalchemy as sa

revision      = 'z9z8z7z6z5z4'
down_revision = 'q1w2e3r4t5y6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        'chest_type_aliases',
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )


def downgrade() -> None:
    op.drop_column('chest_type_aliases', 'enabled')
