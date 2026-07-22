"""add_user_session_started_at

Revision ID: s2e3s4s5i6o7
Revises: r2a3w4o5c6r7
Create Date: 2026-07-22

Marks when the CURRENT online session began — set only on the
offline→online transition (login or first heartbeat/long-poll after
being offline), never overwritten by later pings within the same
session. Lets the admin panel show "Онлайн с HH:MM (Xч Yм)" instead
of just a last-ping timestamp.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 's2e3s4s5i6o7'
down_revision: Union[str, None] = 'r2a3w4o5c6r7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('session_started_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'session_started_at')
