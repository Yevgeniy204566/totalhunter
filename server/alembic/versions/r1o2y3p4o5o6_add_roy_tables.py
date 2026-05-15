"""add roy tables

Revision ID: r1o2y3p4o5o6
Revises: h4i5j6k7l8m9
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'r1o2y3p4o5o6'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'roy_pool',
        sa.Column('id',            sa.Integer(),    nullable=False),
        sa.Column('kingdom',       sa.Integer(),    nullable=False),
        sa.Column('x',             sa.Integer(),    nullable=False),
        sa.Column('y',             sa.Integer(),    nullable=False),
        sa.Column('percent',       sa.Integer(),    nullable=False),
        sa.Column('reporter_hwid', sa.String(16),   nullable=False),
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',    sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at',    sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roy_pool')),
    )
    op.create_index(op.f('ix_roy_pool_kingdom'),       'roy_pool', ['kingdom'],       unique=False)
    op.create_index(op.f('ix_roy_pool_reporter_hwid'), 'roy_pool', ['reporter_hwid'], unique=False)
    op.create_index(op.f('ix_roy_pool_expires_at'),    'roy_pool', ['expires_at'],    unique=False)

    op.create_table(
        'roy_balance',
        sa.Column('hwid',        sa.String(16),  nullable=False),
        sa.Column('balance_sec', sa.Integer(),   nullable=False, server_default=sa.text('0')),
        sa.Column('updated_at',  sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('hwid', name=op.f('pk_roy_balance')),
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_roy_pool_expires_at'),    table_name='roy_pool')
    op.drop_index(op.f('ix_roy_pool_reporter_hwid'), table_name='roy_pool')
    op.drop_index(op.f('ix_roy_pool_kingdom'),       table_name='roy_pool')
    op.drop_table('roy_pool')
    op.drop_table('roy_balance')
