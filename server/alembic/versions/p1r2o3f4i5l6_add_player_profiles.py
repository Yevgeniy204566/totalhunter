"""add player_profiles table for per-player rank and troop composition

Revision ID: p1r2o3f4i5l6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa

revision      = 'p1r2o3f4i5l6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'player_profiles',
        sa.Column('id',             sa.Integer(),               primary_key=True),
        sa.Column('collector_id',   sa.Integer(),               nullable=False),
        sa.Column('canonical_name', sa.String(100),             nullable=False),
        sa.Column('rank',           sa.String(20),              nullable=True),
        sa.Column('troop_level',    sa.String(20),              nullable=True),
        sa.Column('updated_at',     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(
            ['collector_id'], ['chest_collectors.id'],
            name=op.f('fk_player_profiles_collector_id_chest_collectors'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_player_profiles')),
        sa.UniqueConstraint('collector_id', 'canonical_name', name='uq_player_profile'),
    )
    op.create_index(op.f('ix_player_profiles_collector_id'), 'player_profiles', ['collector_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_player_profiles_collector_id'), table_name='player_profiles')
    op.drop_table('player_profiles')
