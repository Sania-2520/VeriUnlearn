"""Add security_assessments table

Revision ID: 004
Revises: 003
Create Date: 2026-07-13 20:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("model_version_id", sa.String(255), nullable=False),
        sa.Column("tests", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("scores", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("results", sa.JSON, nullable=True),
        sa.Column("recommendations", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_security_assessments_tenant", "security_assessments", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_security_assessments_tenant", table_name="security_assessments")
    op.drop_table("security_assessments")
