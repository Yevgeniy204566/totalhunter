"""add_ancient_editors

Revision ID: e1d2i3t4o5r6
Revises: r1o2s3t4e5r6
Create Date: 2026-06-30

Invite codes (24h TTL) + editor access records (30-day expiry) for the
"Редактор клана" feature — clanmates can edit troop levels and name mappings
without being the collector owner.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e1d2i3t4o5r6'
down_revision: Union[str, None] = 'r1o2s3t4e5r6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ancient_invite_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collector_id', sa.Integer(),
                  sa.ForeignKey('chest_collectors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_by_user_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_ancient_invite_code'),
    )
    op.create_index('ix_ancient_invite_codes_collector',
                    'ancient_invite_codes', ['collector_id'])

    op.create_table(
        'ancient_editors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collector_id', sa.Integer(),
                  sa.ForeignKey('chest_collectors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collector_id', 'user_id', name='uq_ancient_editor'),
    )
    op.create_index('ix_ancient_editors_user', 'ancient_editors', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_ancient_editors_user', table_name='ancient_editors')
    op.drop_table('ancient_editors')
    op.drop_index('ix_ancient_invite_codes_collector', table_name='ancient_invite_codes')
    op.drop_table('ancient_invite_codes')
