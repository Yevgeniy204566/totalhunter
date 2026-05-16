"""add web platform tables

Revision ID: 22864ea6408d
Revises: b2c3d4e5f6a7
Create Date: 2026-05-09

Web platform feature branch: crash_reports, link_codes, hwid_history.
Developed in parallel with ref_bonus_claimed (g3h4i5j6k7l8) — merged via 575bdc292d9e.
"""
from alembic import op
import sqlalchemy as sa

revision = '22864ea6408d'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # crash_reports — Silent Observer: automatic crash telemetry from bot clients
    op.create_table(
        'crash_reports',
        sa.Column('id',         sa.Integer(),    nullable=False),
        sa.Column('hwid',       sa.String(16),   nullable=True),
        sa.Column('version',    sa.String(20),   nullable=True),
        sa.Column('os_info',    sa.String(150),  nullable=True),
        sa.Column('traceback',  sa.Text(),       nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_crash_reports')),
    )
    op.create_index(op.f('ix_crash_reports_hwid'),       'crash_reports', ['hwid'])
    op.create_index(op.f('ix_crash_reports_created_at'), 'crash_reports', ['created_at'])

    # link_codes — 6-digit codes for linking HWID via website dashboard
    op.create_table(
        'link_codes',
        sa.Column('id',         sa.Integer(),   nullable=False),
        sa.Column('hwid',       sa.String(16),  nullable=False),
        sa.Column('code',       sa.String(6),   nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_link_codes')),
        sa.UniqueConstraint('code', name=op.f('uq_link_codes_code')),
    )
    op.create_index(op.f('ix_link_codes_hwid'), 'link_codes', ['hwid'])

    # hwid_history — anti-abuse: tracks all HWIDs ever linked to a user account
    op.create_table(
        'hwid_history',
        sa.Column('id',        sa.Integer(),  nullable=False),
        sa.Column('hwid',      sa.String(16), nullable=False),
        sa.Column('user_id',   sa.Integer(),  nullable=False),
        sa.Column('linked_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_hwid_history_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_hwid_history')),
    )
    op.create_index(op.f('ix_hwid_history_hwid'),    'hwid_history', ['hwid'])
    op.create_index(op.f('ix_hwid_history_user_id'), 'hwid_history', ['user_id'])

    # users: add hwid_reset_at + make hwid nullable (bot can exist before HWID link)
    op.add_column('users',
        sa.Column('hwid_reset_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.alter_column('users', 'hwid',
                    existing_type=sa.String(16),
                    nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'hwid',
                    existing_type=sa.String(16),
                    nullable=False)
    op.drop_column('users', 'hwid_reset_at')

    op.drop_index(op.f('ix_hwid_history_user_id'), table_name='hwid_history')
    op.drop_index(op.f('ix_hwid_history_hwid'),    table_name='hwid_history')
    op.drop_table('hwid_history')

    op.drop_index(op.f('ix_link_codes_hwid'), table_name='link_codes')
    op.drop_table('link_codes')

    op.drop_index(op.f('ix_crash_reports_created_at'), table_name='crash_reports')
    op.drop_index(op.f('ix_crash_reports_hwid'),       table_name='crash_reports')
    op.drop_table('crash_reports')
