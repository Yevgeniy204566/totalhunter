"""feedback_thread_columns

Revision ID: m1s2g3t4h5r6
Revises: f4v5r6t7s8t9
Create Date: 2026-11-07 12:00:00.000000

Переписка админ ↔ игрок: sender ('user'|'admin') и read_at в существующей таблице feedback.
Старые записи — сообщения игроков, уже виденные админом (счётчик «новых» их не считает).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'm1s2g3t4h5r6'
down_revision: Union[str, Sequence[str], None] = 'f4v5r6t7s8t9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feedback',
        sa.Column('sender', sa.String(length=8), nullable=False, server_default=sa.text("'user'")))
    op.add_column('feedback',
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE feedback SET read_at = now() WHERE read_at IS NULL")


def downgrade() -> None:
    op.drop_column('feedback', 'read_at')
    op.drop_column('feedback', 'sender')
