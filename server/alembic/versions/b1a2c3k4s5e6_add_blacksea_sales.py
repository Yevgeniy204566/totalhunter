"""add_blacksea_sales

Revision ID: b1a2c3k4s5e6
Revises: s2e3s4s5i6o7
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'b1a2c3k4s5e6'
down_revision = 's2e3s4s5i6o7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'blacksea_sales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sale_id', sa.String(50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credits_total', sa.Integer(), nullable=False),
        sa.Column('uah_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_blacksea_sales_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_blacksea_sales')),
    )
    op.create_index(op.f('ix_blacksea_sales_sale_id'), 'blacksea_sales',
                    ['sale_id'], unique=True)
    op.create_index(op.f('ix_blacksea_sales_user_id'), 'blacksea_sales', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_blacksea_sales_user_id'), table_name='blacksea_sales')
    op.drop_index(op.f('ix_blacksea_sales_sale_id'), table_name='blacksea_sales')
    op.drop_table('blacksea_sales')
