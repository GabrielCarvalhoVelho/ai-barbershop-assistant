"""add password_hash, is_active and role to users

Revision ID: c7d2e4f6a891
Revises: b5d4e7f1a823
Create Date: 2026-04-15 00:00:00.000000

Adiciona os campos de autenticação e controle de acesso ao model User.
server_default em todas as colunas NOT NULL para compatibilidade com
rows existentes no banco (seed de dev).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d2e4f6a891"
down_revision: Union[str, None] = "b5d4e7f1a823"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

userrole = sa.Enum("customer", "admin", name="userrole")


def upgrade() -> None:
    # 1. Criar tipo ENUM nativo no PostgreSQL (ignorado em SQLite)
    userrole.create(op.get_bind(), checkfirst=True)

    # 2. Adicionar colunas com server_default para rows existentes
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            userrole,
            nullable=False,
            server_default=sa.text("'customer'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(255),
            nullable=False,
            server_default=sa.text("'placeholder'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
    op.drop_column("users", "role")
    op.drop_column("users", "is_active")
    userrole.drop(op.get_bind(), checkfirst=True)
