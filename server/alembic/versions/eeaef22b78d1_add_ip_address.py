"""add_ip_address

Revision ID: eeaef22b78d1
Revises: dc8b275f4ed6
Create Date: 2026-04-16

Добавляет поле ip_address в таблицу users.
Нужно для базовой защиты от накрутки trial через смену HWID.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'eeaef22b78d1'
down_revision: Union[str, Sequence[str], None] = 'dc8b275f4ed6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('ip_address', sa.String(45), nullable=True),
    )
    op.create_index('ix_users_ip_address', 'users', ['ip_address'])


def downgrade() -> None:
    op.drop_index('ix_users_ip_address', 'users')
    op.drop_column('users', 'ip_address')
