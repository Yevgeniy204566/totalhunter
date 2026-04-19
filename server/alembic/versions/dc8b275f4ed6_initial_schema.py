"""initial_schema

Revision ID: dc8b275f4ed6
Revises:
Create Date: 2026-04-16

Первая миграция — создаёт все таблицы Total Hunter SaaS.
Применить на GCP: DATABASE_URL=... alembic upgrade head
Откатить:        DATABASE_URL=... alembic downgrade base
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

revision: str = 'dc8b275f4ed6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id',            sa.Integer(),     primary_key=True),
        sa.Column('hwid',          sa.String(16),    nullable=False),
        sa.Column('email',         sa.String(255)),
        sa.Column('username',      sa.String(50)),
        sa.Column('credits',       sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('ref_credits',   sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('ref_code',      sa.String(12),    nullable=False),
        sa.Column('invited_by_id', sa.Integer(),     sa.ForeignKey('users.id'), nullable=True),
        sa.Column('trial_used',    sa.Boolean(),     nullable=False, server_default='false'),
        sa.Column('is_banned',     sa.Boolean(),     nullable=False, server_default='false'),
        sa.Column('bot_version',   sa.String(20)),
        sa.Column('last_seen',     TIMESTAMP(timezone=True)),
        sa.Column('created_at',    TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('ix_users_hwid',     'users', ['hwid'],     unique=True)
    op.create_index('ix_users_email',    'users', ['email'],    unique=True)
    op.create_index('ix_users_ref_code', 'users', ['ref_code'], unique=True)

    # ── transactions ─────────────────────────────────────────────────────────
    op.create_table(
        'transactions',
        sa.Column('id',         sa.Integer(),       primary_key=True),
        sa.Column('user_id',    sa.Integer(),       sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type',       sa.String(30),      nullable=False),
        sa.Column('amount',     sa.Integer(),       nullable=False),
        sa.Column('usd_amount', sa.Numeric(10, 2)),
        sa.Column('package',    sa.String(10)),
        sa.Column('meta',       JSONB),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('ix_transactions_user_id',   'transactions', ['user_id'])
    op.create_index('ix_transactions_type',      'transactions', ['type'])
    op.create_index('ix_transactions_created_at','transactions', ['created_at'])

    # ── hunts ────────────────────────────────────────────────────────────────
    op.create_table(
        'hunts',
        sa.Column('id',         sa.Integer(),  primary_key=True),
        sa.Column('user_id',    sa.Integer(),  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('hunt_type',  sa.String(20), nullable=False),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('ix_hunts_user_id',   'hunts', ['user_id'])
    op.create_index('ix_hunts_created_at','hunts', ['created_at'])  # для запросов today/week/month

    # ── logs ─────────────────────────────────────────────────────────────────
    op.create_table(
        'logs',
        sa.Column('id',         sa.Integer(),  primary_key=True),
        sa.Column('hwid',       sa.String(16)),
        sa.Column('event_type', sa.String(50)),
        sa.Column('payload',    sa.Text()),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('ix_logs_hwid',       'logs', ['hwid'])
    op.create_index('ix_logs_created_at', 'logs', ['created_at'])

    # ── broadcasts ───────────────────────────────────────────────────────────
    op.create_table(
        'broadcasts',
        sa.Column('id',         sa.Integer(), primary_key=True),
        sa.Column('message',    sa.Text(),    nullable=False),
        sa.Column('is_active',  sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )

    # ── app_settings ─────────────────────────────────────────────────────────
    op.create_table(
        'app_settings',
        sa.Column('key',        sa.String(50), primary_key=True),
        sa.Column('value',      sa.Text(),     nullable=False),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )

    # Стартовые записи версионирования
    op.execute("""
        INSERT INTO app_settings (key, value) VALUES
            ('current_version', '1.0.0'),
            ('min_version',     '1.0.0'),
            ('force_update',    'false')
    """)


def downgrade() -> None:
    # Удаляем в обратном порядке (ForeignKey зависимости)
    op.execute("DELETE FROM app_settings WHERE key IN ('current_version','min_version','force_update')")
    op.drop_table('app_settings')
    op.drop_table('broadcasts')
    op.drop_index('ix_logs_created_at', 'logs')
    op.drop_index('ix_logs_hwid', 'logs')
    op.drop_table('logs')
    op.drop_index('ix_hunts_created_at', 'hunts')
    op.drop_index('ix_hunts_user_id', 'hunts')
    op.drop_table('hunts')
    op.drop_index('ix_transactions_created_at', 'transactions')
    op.drop_index('ix_transactions_type', 'transactions')
    op.drop_index('ix_transactions_user_id', 'transactions')
    op.drop_table('transactions')
    op.drop_index('ix_users_ref_code', 'users')
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_hwid', 'users')
    op.drop_table('users')
