"""add custom_slug to chest_collectors for short public URLs (/c/{kingdom}/{slug})

Revision ID: a1b2c3d4e5f6
Revises: q1w2e3r4t5y6
Create Date: 2026-06-27

Enables readable short URLs like total-hunter.com/c/229/eldorado
instead of the random UUID slug.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'q1w2e3r4t5y6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chest_collectors', sa.Column('custom_slug', sa.String(100), nullable=True))
    op.create_unique_constraint(
        'uq_chest_collectors_kingdom_custom_slug',
        'chest_collectors',
        ['kingdom', 'custom_slug'],
    )


def downgrade():
    op.drop_constraint('uq_chest_collectors_kingdom_custom_slug', 'chest_collectors', type_='unique')
    op.drop_column('chest_collectors', 'custom_slug')
