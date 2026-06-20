"""add chest catalog, localizations, collector pattern/language (Phase 2: points & i18n)

Revision ID: q1w2e3r4t5y6
Revises: h7c8e9s0t1c2
Create Date: 2026-06-20

chest_type_catalog = global points table, keyed by (canonical_type, pattern).
chest_localizations = global display-text table, keyed by (canonical_type, language).
chest_collectors gains pattern/language — admin-set constants for the whole clan.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'q1w2e3r4t5y6'
down_revision = 'h7c8e9s0t1c2'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column('chest_collectors', sa.Column('pattern', sa.String(8), nullable=True))
    op.add_column('chest_collectors', sa.Column('language', sa.String(8), nullable=True))

    op.create_table(
        'chest_type_catalog',
        sa.Column('id',             sa.Integer(),   primary_key=True),
        sa.Column('canonical_type', sa.String(200), nullable=False),
        sa.Column('pattern',        sa.String(8),   nullable=False),
        sa.Column('points',         sa.Integer(),   nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chest_type_catalog')),
        sa.UniqueConstraint('canonical_type', 'pattern',
                            name='uq_chest_catalog_type_pattern'),
    )

    op.create_table(
        'chest_localizations',
        sa.Column('id',             sa.Integer(),   primary_key=True),
        sa.Column('canonical_type', sa.String(200), nullable=False),
        sa.Column('language',       sa.String(8),   nullable=False),
        sa.Column('display_text',   sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chest_localizations')),
        sa.UniqueConstraint('canonical_type', 'language',
                            name='uq_chest_localizations_type_lang'),
    )


def downgrade() -> None:
    op.drop_table('chest_localizations')
    op.drop_table('chest_type_catalog')
    op.drop_column('chest_collectors', 'language')
    op.drop_column('chest_collectors', 'pattern')
