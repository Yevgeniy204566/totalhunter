"""rename_freekassa_to_nowpayments

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-05-07 10:00:00.000000
"""
from alembic import op


revision = 'b2c3d4e5f6a7'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('uq_orders_freekassa_order_id', 'orders', type_='unique')
    op.alter_column('orders', 'freekassa_order_id', new_column_name='nowpayments_payment_id')
    op.create_unique_constraint('uq_orders_nowpayments_payment_id', 'orders', ['nowpayments_payment_id'])


def downgrade() -> None:
    op.drop_constraint('uq_orders_nowpayments_payment_id', 'orders', type_='unique')
    op.alter_column('orders', 'nowpayments_payment_id', new_column_name='freekassa_order_id')
    op.create_unique_constraint('uq_orders_freekassa_order_id', 'orders', ['freekassa_order_id'])
