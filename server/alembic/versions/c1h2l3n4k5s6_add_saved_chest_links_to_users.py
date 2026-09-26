"""add saved_chest_links to users

Revision ID: c1h2l3n4k5s6
Revises: f1x2t3y4p5o6
Create Date: 2026-09-26

Сохранённые в «Профиле» кабинета таблицы сундуков кланов: JSON-список
[{"kingdom": "229", "clan": "ELDORADO"}, ...]. Пустой список по умолчанию.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'c1h2l3n4k5s6'
down_revision = 'f1x2t3y4p5o6'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('saved_chest_links', sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade():
    op.drop_column('users', 'saved_chest_links')
