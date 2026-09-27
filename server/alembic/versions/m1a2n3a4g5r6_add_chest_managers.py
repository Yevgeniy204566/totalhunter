"""add chest_managers

Revision ID: m1a2n3a4g5r6
Revises: h1e2r3o4l5v6
Create Date: 2026-09-27

Руководители ростера сундуков: хозяин приглашает кодом, руководитель помогает вести ЕГО
ростер на сайте. Хозяин (chest_collectors.user_id) всегда один и не меняется.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'm1a2n3a4g5r6'
down_revision = 'h1e2r3o4l5v6'
branch_labels = None
depends_on    = None


def upgrade():
    op.create_table(
        'chest_managers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(),
                  sa.ForeignKey('chest_collectors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('collector_id', 'user_id', name='uq_chest_manager'),
    )
    op.create_index('ix_chest_managers_collector_id', 'chest_managers', ['collector_id'])
    op.create_index('ix_chest_managers_user_id', 'chest_managers', ['user_id'])


def downgrade():
    op.drop_index('ix_chest_managers_user_id', table_name='chest_managers')
    op.drop_index('ix_chest_managers_collector_id', table_name='chest_managers')
    op.drop_table('chest_managers')
