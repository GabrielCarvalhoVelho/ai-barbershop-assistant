"""convert status and sender to enum types

Revision ID: f97c79dc2341
Revises: 18a92ac95d06
Create Date: 2026-04-05 11:54:55.683222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f97c79dc2341'
down_revision: Union[str, None] = '18a92ac95d06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum types para PostgreSQL
conversationstatus = sa.Enum('active', 'closed', name='conversationstatus')
messagesender = sa.Enum('user', 'bot', name='messagesender')


def upgrade() -> None:
    # 1. Criar os tipos enum no PostgreSQL
    conversationstatus.create(op.get_bind(), checkfirst=True)
    messagesender.create(op.get_bind(), checkfirst=True)

    # 2. Converter colunas VARCHAR → ENUM (com USING cast)
    op.alter_column(
        'conversations', 'status',
        existing_type=sa.VARCHAR(length=20),
        type_=conversationstatus,
        existing_nullable=False,
        postgresql_using='status::conversationstatus',
    )
    op.alter_column(
        'messages', 'sender',
        existing_type=sa.VARCHAR(length=10),
        type_=messagesender,
        existing_nullable=False,
        postgresql_using='sender::messagesender',
    )


def downgrade() -> None:
    # 1. Converter colunas ENUM → VARCHAR
    op.alter_column(
        'messages', 'sender',
        existing_type=messagesender,
        type_=sa.VARCHAR(length=10),
        existing_nullable=False,
        postgresql_using='sender::varchar',
    )
    op.alter_column(
        'conversations', 'status',
        existing_type=conversationstatus,
        type_=sa.VARCHAR(length=20),
        existing_nullable=False,
        postgresql_using='status::varchar',
    )

    # 2. Dropar os tipos enum
    messagesender.drop(op.get_bind(), checkfirst=True)
    conversationstatus.drop(op.get_bind(), checkfirst=True)
