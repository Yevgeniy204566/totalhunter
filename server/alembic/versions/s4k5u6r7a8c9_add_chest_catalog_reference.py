"""add chest_catalog_reference — the single master list of all known chest type IDs

Revision ID: s4k5u6r7a8c9
Revises: a1n2c3i4e5n6
Create Date: 2026-06-24

chest_catalog_reference = global list of canonical_id strings, one row per known chest
type in the game. Sole source for the dashboard's chest-picker dropdown — independent of
whether points (chest_type_catalog) or a translation (chest_localizations) exist for it yet.
"""
from alembic import op
import sqlalchemy as sa

revision      = 's4k5u6r7a8c9'
down_revision = 'a1n2c3i4e5n6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'chest_catalog_reference',
        sa.Column('id',         sa.Integer(),   primary_key=True),
        sa.Column('catalog_id', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chest_catalog_reference')),
        sa.UniqueConstraint('catalog_id', name='uq_chest_catalog_reference_catalog_id'),
    )


def downgrade() -> None:
    op.drop_table('chest_catalog_reference')
