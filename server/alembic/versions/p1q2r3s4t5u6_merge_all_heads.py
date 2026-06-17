"""merge all heads before clan_members

Revision ID: p1q2r3s4t5u6
Revises: 14e8d8e2a95a, n3o4p5q6r7s8
Create Date: 2026-06-16

Merges two parallel branches:
  14e8d8e2a95a — final_merge (web platform branch)
  n3o4p5q6r7s8 — roypool unique constraint (roy branch)
"""
from alembic import op

revision      = 'p1q2r3s4t5u6'
down_revision = ('14e8d8e2a95a', 'n3o4p5q6r7s8')
branch_labels = None
depends_on    = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
