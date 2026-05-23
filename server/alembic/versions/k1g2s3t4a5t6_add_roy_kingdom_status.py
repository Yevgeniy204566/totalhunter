"""add roy_kingdom_status table

Revision ID: k1g2s3t4a5t6
Revises: r1o2y3p4o5o6
Create Date: 2026-05-23

Tracks live active_count per Kingdom for the ROY swarm feature.
Backend cleanup task expires sessions after 5 min of no /roy/scan pings.
Frontend reads via GET /roy/kingdoms or SSE /roy/status-stream.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'k1g2s3t4a5t6'
down_revision = 'r1o2y3p4o5o6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'roy_kingdom_status',
        sa.Column('kingdom',      sa.Integer(),               nullable=False),
        sa.Column('active_count', sa.Integer(),               nullable=False,
                  server_default=sa.text('0')),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('kingdom', name=op.f('pk_roy_kingdom_status')),
    )


def downgrade() -> None:
    op.drop_table('roy_kingdom_status')
