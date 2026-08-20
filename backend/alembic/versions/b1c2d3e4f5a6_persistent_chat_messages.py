"""persistent chat messages

Adds structured message history to chat_sessions so Assistant conversations
survive page reloads and can be replayed exactly.

Revision ID: b1c2d3e4f5a6
Revises: 10a9fd591a22
Create Date: 2026-08-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = '10a9fd591a22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('messages_json', sa.Text(), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'messages_json')