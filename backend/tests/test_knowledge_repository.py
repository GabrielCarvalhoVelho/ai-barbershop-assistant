import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.database import Base
from app.models.company import Company
from app.models.enums import DocumentCategory
from app.models.knowledge_document import KnowledgeDocument
from app.repositories.knowledge_repository import KnowledgeDocumentRepository

engine = create_async_engine("sqlite+aiosqlite://", echo=False)


def _enable_fk(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


event.listen(engine.sync_engine, "connect", _enable_fk)

factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session():
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def company(session):
    company = Company(name="Barbearia Teste", phone="+5511999999999")
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@pytest_asyncio.fixture
async def repo(session):
    return KnowledgeDocumentRepository(session)


async def _create_doc(session, company_id, title, content, category, is_active=True):
    doc = KnowledgeDocument(
        company_id=company_id,
        title=title,
        content=content,
        category=category,
        is_active=is_active,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


# ========================
# create
# ========================


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_and_returns_document(self, repo, company):
        doc = await repo.create(
            company_id=company.id,
            title="Corte masculino",
            content="R$ 40,00",
            category=DocumentCategory.SERVICES,
        )

        assert doc.id is not None
        assert doc.company_id == company.id
        assert doc.title == "Corte masculino"
        assert doc.content == "R$ 40,00"
        assert doc.category == DocumentCategory.SERVICES
        assert doc.is_active is True

    @pytest.mark.asyncio
    async def test_create_sets_created_at(self, repo, company):
        doc = await repo.create(
            company_id=company.id,
            title="Horário",
            content="9h-19h",
            category=DocumentCategory.HOURS,
        )

        assert doc.created_at is not None


# ========================
# get_by_company
# ========================


class TestGetByCompany:
    @pytest.mark.asyncio
    async def test_returns_all_active_documents(self, session, repo, company):
        await _create_doc(session, company.id, "Doc 1", "C1", DocumentCategory.SERVICES)
        await _create_doc(session, company.id, "Doc 2", "C2", DocumentCategory.HOURS)

        docs = await repo.get_by_company(company.id)
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_excludes_inactive_documents(self, session, repo, company):
        await _create_doc(session, company.id, "Ativo", "C1", DocumentCategory.SERVICES)
        await _create_doc(
            session, company.id, "Inativo", "C2", DocumentCategory.SERVICES, is_active=False
        )

        docs = await repo.get_by_company(company.id)
        assert len(docs) == 1
        assert docs[0].title == "Ativo"

    @pytest.mark.asyncio
    async def test_returns_empty_for_company_without_documents(self, repo, company):
        docs = await repo.get_by_company(company.id)
        assert docs == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_nonexistent_company(self, repo):
        docs = await repo.get_by_company(999)
        assert docs == []

    @pytest.mark.asyncio
    async def test_isolates_by_company(self, session, repo, company):
        other = Company(name="Outra Barbearia")
        session.add(other)
        await session.commit()
        await session.refresh(other)

        await _create_doc(session, company.id, "Doc empresa 1", "C1", DocumentCategory.SERVICES)
        await _create_doc(session, other.id, "Doc empresa 2", "C2", DocumentCategory.SERVICES)

        docs = await repo.get_by_company(company.id)
        assert len(docs) == 1
        assert docs[0].title == "Doc empresa 1"

    @pytest.mark.asyncio
    async def test_ordered_by_category_then_id(self, session, repo, company):
        await _create_doc(session, company.id, "Horário", "C1", DocumentCategory.HOURS)
        await _create_doc(session, company.id, "FAQ", "C2", DocumentCategory.FAQ)
        await _create_doc(session, company.id, "Geral", "C3", DocumentCategory.GENERAL)

        docs = await repo.get_by_company(company.id)
        categories = [d.category for d in docs]
        assert categories == sorted(categories, key=lambda c: c.value)


# ========================
# get_by_category
# ========================


class TestGetByCategory:
    @pytest.mark.asyncio
    async def test_filters_by_category(self, session, repo, company):
        await _create_doc(session, company.id, "Corte", "C1", DocumentCategory.SERVICES)
        await _create_doc(session, company.id, "Horário", "C2", DocumentCategory.HOURS)
        await _create_doc(session, company.id, "Barba", "C3", DocumentCategory.SERVICES)

        docs = await repo.get_by_category(company.id, DocumentCategory.SERVICES)
        assert len(docs) == 2
        assert all(d.category == DocumentCategory.SERVICES for d in docs)

    @pytest.mark.asyncio
    async def test_excludes_inactive_in_category(self, session, repo, company):
        await _create_doc(session, company.id, "Ativo", "C1", DocumentCategory.FAQ)
        await _create_doc(
            session, company.id, "Inativo", "C2", DocumentCategory.FAQ, is_active=False
        )

        docs = await repo.get_by_category(company.id, DocumentCategory.FAQ)
        assert len(docs) == 1
        assert docs[0].title == "Ativo"

    @pytest.mark.asyncio
    async def test_returns_empty_for_category_without_documents(self, repo, company):
        docs = await repo.get_by_category(company.id, DocumentCategory.POLICIES)
        assert docs == []

    @pytest.mark.asyncio
    async def test_isolates_by_company_and_category(self, session, repo, company):
        other = Company(name="Outra")
        session.add(other)
        await session.commit()
        await session.refresh(other)

        await _create_doc(session, company.id, "Meu serviço", "C1", DocumentCategory.SERVICES)
        await _create_doc(session, other.id, "Serviço deles", "C2", DocumentCategory.SERVICES)

        docs = await repo.get_by_category(company.id, DocumentCategory.SERVICES)
        assert len(docs) == 1
        assert docs[0].title == "Meu serviço"
