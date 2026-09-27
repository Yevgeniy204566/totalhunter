"""add game_nick to users

Revision ID: n1i2c3k4g5n6
Revises: m1a2n3a4g5r6
Create Date: 2026-09-27

Игровой ник аккаунта: в руководителях ростера хозяин и руководители видят друг друга только
по нику, почта не показывается никому (владелец 2026-09-27).
"""
from alembic import op
import sqlalchemy as sa

revision      = 'n1i2c3k4g5n6'
down_revision = 'm1a2n3a4g5r6'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('users', sa.Column('game_nick', sa.String(32), nullable=True))


def downgrade():
    op.drop_column('users', 'game_nick')
