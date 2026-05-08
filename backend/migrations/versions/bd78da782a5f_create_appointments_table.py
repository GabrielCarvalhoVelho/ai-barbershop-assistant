"""create appointments table

Revision ID: bd78da782a5f
Revises: c7d2e4f6a891
Create Date: 2026-05-07 19:05:24.603638

Cria tabela appointments com status enum, FKs para users e companies,
índice composto (company_id, scheduled_at) para query de conflito de slot
e índice em user_id para listagem por usuário.

Padrão de criação: tabela com status como VARCHAR, depois ALTER para ENUM —
evita conflito entre op.create_table e a criação automática do tipo pelo SQLAlchemy.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bd78da782a5f"
down_revision: Union[str, None] = "c7d2e4f6a891"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

appointmentstatus = sa.Enum(
    "scheduled", "confirmed", "cancelled", "completed",
    name="appointmentstatus",
)


def upgrade() -> None:
    # 1. Criar o tipo ENUM no PostgreSQL
    appointmentstatus.create(op.get_bind(), checkfirst=True)

    # 2. Criar tabela com status como VARCHAR — evita criação dupla do ENUM
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("service", sa.String(length=150), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Converter status VARCHAR → ENUM
    op.alter_column(
        "appointments", "status",
        existing_type=sa.String(length=20),
        type_=appointmentstatus,
        existing_nullable=False,
        postgresql_using="status::appointmentstatus",
    )

    op.create_index("ix_appointments_user_id", "appointments", ["user_id"])
    op.create_index(
        "ix_appointments_company_scheduled_at",
        "appointments",
        ["company_id", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_company_scheduled_at", table_name="appointments")
    op.drop_index("ix_appointments_user_id", table_name="appointments")
    op.drop_table("appointments")
    appointmentstatus.drop(op.get_bind(), checkfirst=True)
