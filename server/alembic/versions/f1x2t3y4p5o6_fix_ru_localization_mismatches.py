"""fix RU chest localization text mismatches found live on Феникс

Сессия #149, 2026-09-25: живая проверка на реальных данных владельца выявила, что
2 из исходных 33 (введённых раньше вручную) записей не совпадают с тем, что реально
показывает игра — формат отличался (не хватало/лишнее слово), поэтому автосопоставление
не срабатывало, хотя перевод по смыслу верный.

Revision ID: f1x2t3y4p5o6
Revises: r9u2l0o8c0v1
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1x2t3y4p5o6'
down_revision = 'r9u2l0o8c0v1'
branch_labels = None
depends_on = None

# (canonical_type, старый текст, реальный текст игры)
FIXES = [
    ("Rare Crypt 25", "Редкий склеп 25", "Редкий склеп 25 уровня"),
    ("Elven Citadel 30", "Эльфийская цитадель 30", "Цитадель 30 уровня"),
]


def upgrade():
    conn = op.get_bind()
    meta = sa.MetaData()
    t = sa.Table('chest_localizations', meta, autoload_with=conn)
    for canonical_type, _old_text, new_text in FIXES:
        conn.execute(
            t.update()
            .where(t.c.canonical_type == canonical_type, t.c.language == 'ru')
            .values(display_text=new_text)
        )


def downgrade():
    conn = op.get_bind()
    meta = sa.MetaData()
    t = sa.Table('chest_localizations', meta, autoload_with=conn)
    for canonical_type, old_text, _new_text in FIXES:
        conn.execute(
            t.update()
            .where(t.c.canonical_type == canonical_type, t.c.language == 'ru')
            .values(display_text=old_text)
        )
