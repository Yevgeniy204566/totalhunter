"""add UniqueConstraint(kingdom, x, y) to roy_pool + scan rate limit (server-only)

Revision ID: n3o4p5q6r7s8
Revises: m2n3o4p5q6r7
Create Date: 2026-05-26

BUG-3: без уникального индекса два конкурентных репорта одной биржи
создавали дубликаты в таблице. ON CONFLICT DO UPDATE не требуется —
логика UPDATE vs INSERT уже реализована в Python-коде с try/except IntegrityError.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'n3o4p5q6r7s8'
down_revision = 'm2n3o4p5q6r7'
branch_labels = None
depends_on    = None


def upgrade():
    # Удаляем устаревшие дубликаты перед созданием индекса.
    # Оставляем запись с максимальным id (последний репорт) для каждого (kingdom, x, y).
    op.execute("""
        DELETE FROM roy_pool
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM roy_pool
            GROUP BY kingdom, x, y
        )
    """)
    op.create_unique_constraint(
        'uq_roypool_kingdom_x_y',
        'roy_pool',
        ['kingdom', 'x', 'y'],
    )


def downgrade():
    op.drop_constraint('uq_roypool_kingdom_x_y', 'roy_pool', type_='unique')
