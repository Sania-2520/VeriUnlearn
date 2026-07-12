"""add user_prompt to training_samples

Revision ID: c3a1b2d4e5f6
Revises: 9aa8c0c4f2a1
Create Date: 2026-07-12 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3a1b2d4e5f6'
down_revision: Union[str, None] = '9aa8c0c4f2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('training_samples') as batch_op:
        batch_op.add_column(sa.Column('user_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('training_samples') as batch_op:
        batch_op.drop_column('user_prompt')
