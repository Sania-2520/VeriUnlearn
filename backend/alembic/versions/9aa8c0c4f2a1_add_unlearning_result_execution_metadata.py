"""add unlearning result execution metadata

Revision ID: 9aa8c0c4f2a1
Revises: 6f052e58b34c
Create Date: 2026-07-12 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9aa8c0c4f2a1"
down_revision: Union[str, None] = "6f052e58b34c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("unlearning_results", sa.Column("algorithm", sa.String(length=64), nullable=True))
    op.add_column("unlearning_results", sa.Column("execution_mode", sa.String(length=64), nullable=True))
    op.add_column("unlearning_results", sa.Column("guarantees", sa.String(length=64), nullable=True))
    op.add_column("unlearning_results", sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("unlearning_results", sa.Column("privacy_score", sa.Float(), nullable=True))
    op.add_column("unlearning_results", sa.Column("estimated_cost", sa.Float(), nullable=True))
    op.add_column("unlearning_results", sa.Column("estimated_latency", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("unlearning_results", "estimated_latency")
    op.drop_column("unlearning_results", "estimated_cost")
    op.drop_column("unlearning_results", "privacy_score")
    op.drop_column("unlearning_results", "simulated")
    op.drop_column("unlearning_results", "guarantees")
    op.drop_column("unlearning_results", "execution_mode")
    op.drop_column("unlearning_results", "algorithm")
