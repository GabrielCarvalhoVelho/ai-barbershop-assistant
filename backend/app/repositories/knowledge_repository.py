import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import DB_TIMEOUT_SECONDS, db_operation
from app.core.logger import get_logger
from app.models.enums import DocumentCategory
from app.models.knowledge_document import KnowledgeDocument

logger = get_logger(__name__)


class KnowledgeDocumentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @db_operation("buscar documentos da empresa")
    async def get_by_company(self, company_id: int) -> list[KnowledgeDocument]:
        logger.info("Buscando documentos: company_id=%s", company_id)
        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.company_id == company_id,
                KnowledgeDocument.is_active.is_(True),
            )
            .order_by(KnowledgeDocument.category, KnowledgeDocument.id)
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        docs = list(result.scalars().all())
        logger.info(
            "Documentos encontrados: company_id=%s count=%s", company_id, len(docs)
        )
        return docs

    @db_operation("buscar documentos por categoria")
    async def get_by_category(
        self, company_id: int, category: DocumentCategory
    ) -> list[KnowledgeDocument]:
        logger.info(
            "Buscando documentos: company_id=%s category=%s",
            company_id,
            category.value,
        )
        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.company_id == company_id,
                KnowledgeDocument.category == category,
                KnowledgeDocument.is_active.is_(True),
            )
            .order_by(KnowledgeDocument.id)
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        docs = list(result.scalars().all())
        logger.info(
            "Documentos encontrados: company_id=%s category=%s count=%s",
            company_id,
            category.value,
            len(docs),
        )
        return docs

    @db_operation("buscar todos os documentos da empresa")
    async def get_all_by_company(self, company_id: int) -> list[KnowledgeDocument]:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.company_id == company_id)
            .order_by(KnowledgeDocument.category, KnowledgeDocument.id)
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        return list(result.scalars().all())

    @db_operation("buscar documento por id")
    async def get_by_id(self, doc_id: int, company_id: int) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.company_id == company_id,
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        return result.scalars().first()

    @db_operation("atualizar documento de conhecimento")
    async def update(self, doc_id: int, company_id: int, **fields: Any) -> KnowledgeDocument:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.company_id == company_id,
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        doc = result.scalars().first()
        for key, value in fields.items():
            setattr(doc, key, value)
        doc.updated_at = datetime.now(timezone.utc)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(doc), timeout=DB_TIMEOUT_SECONDS)
        return doc

    @db_operation("desativar documento de conhecimento")
    async def deactivate(self, doc_id: int, company_id: int) -> KnowledgeDocument:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.company_id == company_id,
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        doc = result.scalars().first()
        doc.is_active = False
        doc.updated_at = datetime.now(timezone.utc)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(doc), timeout=DB_TIMEOUT_SECONDS)
        return doc

    @db_operation("criar documento de conhecimento")
    async def create(
        self,
        company_id: int,
        title: str,
        content: str,
        category: DocumentCategory,
    ) -> KnowledgeDocument:
        logger.info(
            "Criando documento: company_id=%s category=%s title=%s",
            company_id,
            category.value,
            title,
        )
        doc = KnowledgeDocument(
            company_id=company_id,
            title=title,
            content=content,
            category=category,
        )
        self._session.add(doc)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(doc), timeout=DB_TIMEOUT_SECONDS)
        logger.info("Documento criado: id=%s", doc.id)
        return doc
