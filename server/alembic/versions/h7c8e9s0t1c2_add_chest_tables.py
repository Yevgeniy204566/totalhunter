"""add chest tables (backend foundation: tenant isolation + alias dictionary)

Revision ID: h7c8e9s0t1c2
Revises: c1l2a3n4m5b6
Create Date: 2026-06-18

chest_collectors = tenant unit [kingdom, clan, user_id], slug for future public dashboard.
chests = one opened chest, unique on (collector_id, sender_raw, chest_type_raw, collected_at)
for idempotent re-import after network failure.
player_aliases / chest_type_aliases = OCR-correction dictionaries, scoped per collector.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'h7c8e9s0t1c2'
down_revision = 'c1l2a3n4m5b6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'chest_collectors',
        sa.Column('id',         sa.Integer(),                primary_key=True),
        sa.Column('kingdom',    sa.String(50),               nullable=False),
        sa.Column('clan',       sa.String(100),              nullable=False),
        sa.Column('user_id',    sa.Integer(),                nullable=False),
        sa.Column('slug',       sa.String(32),                nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),  nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_chest_collectors_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chest_collectors')),
        sa.UniqueConstraint('kingdom', 'clan', 'user_id',
                            name='uq_chest_collectors_tenant'),
        sa.UniqueConstraint('slug', name='uq_chest_collectors_slug'),
    )
    op.create_index(op.f('ix_chest_collectors_user_id'), 'chest_collectors', ['user_id'])

    op.create_table(
        'chests',
        sa.Column('id',                    sa.Integer(),               primary_key=True),
        sa.Column('collector_id',          sa.Integer(),               nullable=False),
        sa.Column('chest_type_raw',        sa.String(200),            nullable=False),
        sa.Column('chest_type_canonical',  sa.String(200),            nullable=False),
        sa.Column('sender_raw',            sa.String(100),            nullable=False),
        sa.Column('sender_canonical',      sa.String(100),            nullable=False),
        sa.Column('collected_at',          sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at',            sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['collector_id'], ['chest_collectors.id'],
                                name=op.f('fk_chests_collector_id_chest_collectors')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chests')),
        sa.UniqueConstraint('collector_id', 'sender_raw', 'chest_type_raw', 'collected_at',
                            name='uq_chests_idempotent'),
    )
    op.create_index(op.f('ix_chests_collector_id'), 'chests', ['collector_id'])

    op.create_table(
        'player_aliases',
        sa.Column('id',             sa.Integer(),   primary_key=True),
        sa.Column('collector_id',   sa.Integer(),   nullable=False),
        sa.Column('raw_name',       sa.String(100), nullable=False),
        sa.Column('canonical_name', sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(['collector_id'], ['chest_collectors.id'],
                                name=op.f('fk_player_aliases_collector_id_chest_collectors')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_player_aliases')),
        sa.UniqueConstraint('collector_id', 'raw_name', name='uq_player_aliases_raw_name'),
    )
    op.create_index(op.f('ix_player_aliases_collector_id'), 'player_aliases', ['collector_id'])

    op.create_table(
        'chest_type_aliases',
        sa.Column('id',             sa.Integer(),   primary_key=True),
        sa.Column('collector_id',   sa.Integer(),   nullable=False),
        sa.Column('raw_type',       sa.String(200), nullable=False),
        sa.Column('canonical_type', sa.String(200), nullable=False),
        sa.ForeignKeyConstraint(['collector_id'], ['chest_collectors.id'],
                                name=op.f('fk_chest_type_aliases_collector_id_chest_collectors')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chest_type_aliases')),
        sa.UniqueConstraint('collector_id', 'raw_type', name='uq_chest_type_aliases_raw_type'),
    )
    op.create_index(op.f('ix_chest_type_aliases_collector_id'), 'chest_type_aliases',
                    ['collector_id'])


def downgrade() -> None:
    op.drop_table('chest_type_aliases')
    op.drop_table('player_aliases')
    op.drop_table('chests')
    op.drop_table('chest_collectors')
