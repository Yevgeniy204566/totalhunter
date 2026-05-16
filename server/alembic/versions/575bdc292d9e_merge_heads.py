"""merge heads: ref_bonus_claimed + web_platform_tables

Revision ID: 575bdc292d9e
Revises: g3h4i5j6k7l8, 22864ea6408d
Create Date: 2026-05-09

Merges two parallel branches:
  g3h4i5j6k7l8 — ref_bonus_claimed (main branch)
  22864ea6408d — web platform tables (feature branch from b2c3d4e5f6a7)
"""
from alembic import op

revision = '575bdc292d9e'
down_revision = ('g3h4i5j6k7l8', '22864ea6408d')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
