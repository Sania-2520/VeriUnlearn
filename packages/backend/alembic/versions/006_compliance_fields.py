"""Add compliance fields to unlearning_requests

Revision ID: 006
Revises: 005
Create Date: 2026-07-20 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "unlearning_requests",
        sa.Column("compliance_verified", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "unlearning_requests",
        sa.Column("compliance_timestamp", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("unlearning_requests", "compliance_timestamp")
    op.drop_column("unlearning_requests", "compliance_verified")
