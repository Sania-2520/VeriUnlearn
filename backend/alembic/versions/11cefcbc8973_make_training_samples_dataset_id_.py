"""make training_samples.dataset_id nullable

Revision ID: 11cefcbc8973
Revises: ef002d399363
Create Date: 2026-07-12 01:22:57.724428
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '11cefcbc8973'
down_revision: Union[str, None] = 'ef002d399363'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('training_samples') as batch_op:
        batch_op.alter_column('dataset_id', existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('training_samples') as batch_op:
        batch_op.alter_column('dataset_id', existing_type=sa.INTEGER(), nullable=False)
