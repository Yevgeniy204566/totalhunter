"""add ancient_roster and ancient_calculations (Древний calculator, Part A)

Revision ID: a1n2c3i4e5n6
Revises: h1s2t3o4r5y6
Create Date: 2026-06-23

Per docs/superpowers/specs/2026-06-23-ancient-quota-calculator-design.md. Both tables
are scoped to the existing chest_collectors tenant (same collector_id as Chests).
"""
from alembic import op
import sqlalchemy as sa

revision      = 'a1n2c3i4e5n6'
down_revision = 'h1s2t3o4r5y6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'ancient_roster',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey('chest_collectors.id'),
                  nullable=False, index=True),
        sa.Column('player_name', sa.String(100), nullable=False),
        sa.Column('place', sa.Integer(), nullable=True),
        sa.Column('points', sa.BigInteger(), nullable=True),
        sa.Column('troop_level', sa.String(20), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('collector_id', 'player_name',
                            name='uq_ancient_roster_player'),
    )
    op.create_table(
        'ancient_calculations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey('chest_collectors.id'),
                  nullable=False, index=True),
        sa.Column('computed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('strategy', sa.String(1), nullable=False),
        sa.Column('clan_preset', sa.String(8), nullable=True),
        sa.Column('summon_levels', sa.JSON(), nullable=False),
        sa.Column('amplification_coef', sa.Float(), nullable=False),
        sa.Column('officer_count', sa.Integer(), nullable=True),
        sa.Column('veteran_count', sa.Integer(), nullable=True),
        sa.Column('total_quota_millions', sa.Float(), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('ancient_calculations')
    op.drop_table('ancient_roster')
