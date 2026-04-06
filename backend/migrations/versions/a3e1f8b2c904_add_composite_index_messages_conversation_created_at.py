"""add composite index messages conversation_created_at

Revision ID: a3e1f8b2c904
Revises: f97c79dc2341
Create Date: 2026-04-05 14:00:00.000000

Substitui o índice simples em messages.conversation_id pelo índice composto
(conversation_id, created_at), que cobre tanto o lookup por conversa quanto
o ORDER BY created_at da query paginada de mensagens.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a3e1f8b2c904"
down_revision: Union[str, None] = "f97c79dc2341"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.create_index(
        "ix_messages_conversation_created_at",
        "messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created_at", table_name="messages")
    op.create_index(
        "ix_messages_conversation_id",
        "messages",
        ["conversation_id"],
    )
