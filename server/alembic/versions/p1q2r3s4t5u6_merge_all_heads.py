"""merge all heads before clan_members

Revision ID: p1q2r3s4t5u6
Revises: n3o4p5q6r7s8
Create Date: 2026-06-16

n3o4p5q6r7s8 (roypool unique constraint) already descends from
14e8d8e2a95a (final_merge) via h4i5j6k7l8m9 -> r1o2y3p4o5o6 ->
k1g2s3t4a5t6 -> m2n3o4p5q6r7 -> n3o4p5q6r7s8 — not a parallel branch,
so the original two-parent merge was redundant and Alembic rejected
it as overlapping ancestry.
"""
from alembic import op

revision      = 'p1q2r3s4t5u6'
down_revision = 'n3o4p5q6r7s8'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
