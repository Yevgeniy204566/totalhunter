"""add_feedback_table

Revision ID: f1a2b3c4d5e6
Revises: eeaef22b78d1
Create Date: 2026-04-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'eeaef22b78d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name='fk_feedback_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_feedback'),
    )
    op.create_index('ix_feedback_user_id', 'feedback', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_feedback_user_id', 'feedback')
    op.drop_table('feedback')
