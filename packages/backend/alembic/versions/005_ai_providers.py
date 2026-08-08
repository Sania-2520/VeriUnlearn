"""Add ai_providers table

Revision ID: 005
Revises: 004
Create Date: 2026-07-13 20:45:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_providers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("api_key_encrypted", sa.String(1024), nullable=True),
        sa.Column("models", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_ai_providers_tenant", "ai_providers", ["tenant_id", "name"])


def downgrade() -> None:
    op.drop_index("idx_ai_providers_tenant", table_name="ai_providers")
    op.drop_table("ai_providers")
