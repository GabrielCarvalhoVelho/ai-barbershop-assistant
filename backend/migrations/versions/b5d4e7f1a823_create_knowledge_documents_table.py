"""create knowledge_documents table

Revision ID: b5d4e7f1a823
Revises: a3e1f8b2c904
Create Date: 2026-04-06 15:00:00.000000

Tabela para armazenar a base de conhecimento da barbearia — serviços,
preços, horários, políticas e FAQ. Dados consumidos pelo RAG para
contextualizar respostas do LLM.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5d4e7f1a823"
down_revision: Union[str, None] = "a3e1f8b2c904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum("services", "hours", "policies", "faq", "general",
                    name="documentcategory", create_constraint=True),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_documents_company_category",
        "knowledge_documents",
        ["company_id", "category"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_documents_company_category",
        table_name="knowledge_documents",
    )
    op.drop_table("knowledge_documents")
    op.execute("DROP TYPE IF EXISTS documentcategory")
