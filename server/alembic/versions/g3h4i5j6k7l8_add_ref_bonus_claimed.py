"""add ref_bonus_claimed to users

Revision ID: g3h4i5j6k7l8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-08

Security fix: ref bonuses now require HWID verification before payout.
ref_bonus_claimed = True means bonus was already paid for this user.
"""
from alembic import op
import sqlalchemy as sa

revision = 'g3h4i5j6k7l8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users',
        sa.Column('ref_bonus_claimed', sa.Boolean(), nullable=False,
                  server_default=sa.text('false'))
    )
    # Mark existing users who already received ref_welcome bonus as claimed
    # to prevent double-payout on next link/verify
    op.execute("""
        UPDATE users SET ref_bonus_claimed = true
        WHERE id IN (
            SELECT DISTINCT user_id FROM transactions WHERE type = 'ref_welcome'
        )
    """)


def downgrade() -> None:
    op.drop_column('users', 'ref_bonus_claimed')
