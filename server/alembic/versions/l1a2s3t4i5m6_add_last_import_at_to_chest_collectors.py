"""add last_import_at to chest_collectors

Revision ID: l1a2s3t4i5m6
Revises: n1i2c3k4g5n6
Create Date: 2026-09-28

Автоудаление клана через 90 дней без заливок сундуков (владелец 2026-09-28), идёт сезон или
на паузе. Кланам, которые уже заливали, отсчёт начинается с даты выкладки (истинную дату
последней заливки восстановить нельзя — сырые сундуки удаляются при архивации сезона).
Не заливавшие ни разу остаются NULL — для них отсчёт от created_at.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'l1a2s3t4i5m6'
down_revision = 'n1i2c3k4g5n6'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('chest_collectors',
                  sa.Column('last_import_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.execute("""
        UPDATE chest_collectors c SET last_import_at = now()
        WHERE EXISTS (SELECT 1 FROM chests ch WHERE ch.collector_id = c.id)
           OR EXISTS (SELECT 1 FROM chest_season_history h WHERE h.collector_id = c.id)
    """)


def downgrade():
    op.drop_column('chest_collectors', 'last_import_at')
