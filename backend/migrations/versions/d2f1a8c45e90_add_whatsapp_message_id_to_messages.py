"""add whatsapp_message_id to messages

Revision ID: d2f1a8c45e90
Revises: bd78da782a5f
Create Date: 2026-05-08 22:00:00.000000

Adiciona coluna whatsapp_message_id (nullable, UNIQUE) em messages para
idempotência do webhook do WhatsApp Cloud API. Eventos repetidos da Meta
são identificados pelo wamid e processados apenas uma vez.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2f1a8c45e90"
down_revision: Union[str, None] = "bd78da782a5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("whatsapp_message_id", sa.String(length=128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_messages_whatsapp_message_id",
        "messages",
        ["whatsapp_message_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_messages_whatsapp_message_id", "messages", type_="unique"
    )
    op.drop_column("messages", "whatsapp_message_id")
