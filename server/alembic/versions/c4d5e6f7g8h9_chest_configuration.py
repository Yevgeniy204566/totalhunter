"""add chest_configurations (per-collector points/pattern), rename chest_type_aliases.
canonical_type to catalog_id, drop enabled/custom_display_name, add management_token

Revision ID: c4d5e6f7g8h9
Revises: q1w2e3r4t5y6
Create Date: 2026-06-20

Phase 4: points and pattern-membership move from the global ChestTypeCatalog (one shared
table for every clan) to a new per-collector ChestConfiguration — each clan sets its own
points and decides which chests count, per docs/superpowers/specs/2026-06-20-chest-dashboard-
phase4-design.md. Existing collectors with a pattern set get their current catalog points
backfilled so they don't lose data on deploy.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'c4d5e6f7g8h9'
down_revision = 'q1w2e3r4t5y6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'chest_configurations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey('chest_collectors.id'),
                  nullable=False, index=True),
        sa.Column('catalog_id', sa.String(200), nullable=False),
        sa.Column('custom_name', sa.String(200), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_in_pattern', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
        sa.UniqueConstraint('collector_id', 'catalog_id',
                            name='uq_chest_config_collector_catalog'),
    )

    op.alter_column('chest_type_aliases', 'canonical_type', new_column_name='catalog_id')
    op.drop_column('chest_type_aliases', 'enabled')

    op.add_column(
        'chest_collectors',
        sa.Column('management_token', sa.String(32), nullable=True, unique=True),
    )

    # Backfill: collectors that already have a pattern keep their current catalog points.
    op.execute("""
        INSERT INTO chest_configurations (collector_id, catalog_id, points, is_in_pattern)
        SELECT cc.id, ctc.canonical_type, ctc.points, true
        FROM chest_collectors cc
        JOIN chest_type_catalog ctc ON ctc.pattern = cc.pattern
        WHERE cc.pattern IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column('chest_collectors', 'management_token')
    op.add_column(
        'chest_type_aliases',
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.alter_column('chest_type_aliases', 'catalog_id', new_column_name='canonical_type')
    op.drop_table('chest_configurations')
