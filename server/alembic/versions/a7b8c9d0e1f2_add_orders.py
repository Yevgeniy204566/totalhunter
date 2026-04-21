"""add_orders

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('package', sa.String(10), nullable=False),
        sa.Column('usd_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('credits_total', sa.Integer(), nullable=False),
        sa.Column('freekassa_order_id', sa.String(50), nullable=True),
        sa.Column('status', sa.String(10), server_default="pending", nullable=False),
        sa.Column('idempotency_key', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_orders_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_orders')),
        sa.UniqueConstraint('freekassa_order_id', name=op.f('uq_orders_freekassa_order_id')),
        sa.UniqueConstraint('idempotency_key', name=op.f('uq_orders_idempotency_key')),
    )
    op.create_index(op.f('ix_orders_user_id'), 'orders', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_orders_user_id'), table_name='orders')
    op.drop_table('orders')
