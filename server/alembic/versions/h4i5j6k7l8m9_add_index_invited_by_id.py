"""add index on users.invited_by_id

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-05-13

Optimization: index on invited_by_id enables efficient L2/L3 referral tree queries
without full table scans when filtering by invited_by_id IN (list_of_user_ids).
"""
from alembic import op

revision = 'h4i5j6k7l8m9'
down_revision = 'g3h4i5j6k7l8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_users_invited_by_id', 'users', ['invited_by_id'])


def downgrade() -> None:
    op.drop_index('ix_users_invited_by_id', table_name='users')
