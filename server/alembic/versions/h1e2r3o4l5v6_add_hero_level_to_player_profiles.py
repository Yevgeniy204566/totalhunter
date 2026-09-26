"""add hero_level to player_profiles

Revision ID: h1e2r3o4l5v6
Revises: q1u2o3t4a5s6
Create Date: 2026-09-26

Уровень Героя игрока (1..999) — вводится лидером в кабинете «Сундуки → Игроки» и игроком
на публичной странице рядом с составом войск. Задел для квоты EM (спека 02).
"""
from alembic import op
import sqlalchemy as sa

revision      = 'h1e2r3o4l5v6'
down_revision = 'q1u2o3t4a5s6'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('player_profiles', sa.Column('hero_level', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('player_profiles', 'hero_level')
