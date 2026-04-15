import os

# DEBUG=true antes de qualquer import da app — garante que Settings()
# não exija API_KEY no ambiente de teste.
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-tests")

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.rate_limiter import limiter
from app.db.database import Base, get_session
from app.main import app
from app.models.company import Company
from app.models.enums import DocumentCategory
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User

test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)


def _enable_fk(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


event.listen(test_engine.sync_engine, "connect", _enable_fk)

test_async_session = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_session():
    async with test_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_async_session() as session:
        company = Company(name="Barbearia Teste")
        session.add(company)
        await session.commit()
        await session.refresh(company)

        user = User(
            company_id=company.id,
            name="Teste",
            phone="+5511999000000",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()

        # Documentos de conhecimento para testes de RAG (company 1 apenas)
        session.add(KnowledgeDocument(
            company_id=company.id,
            title="Corte masculino",
            content="Corte masculino tradicional — R$ 40,00. Tempo estimado: 30 minutos.",
            category=DocumentCategory.SERVICES,
        ))
        session.add(KnowledgeDocument(
            company_id=company.id,
            title="Horário de funcionamento",
            content="Segunda a sexta: 9h às 19h. Sábado: 8h às 17h.",
            category=DocumentCategory.HOURS,
        ))
        await session.commit()

        # Segunda company + user para testes de ownership/isolamento
        company2 = Company(name="Outra Barbearia")
        session.add(company2)
        await session.commit()
        await session.refresh(company2)

        user2 = User(
            company_id=company2.id,
            name="Outro Cliente",
            phone="+5511988888888",
            password_hash="placeholder",
        )
        session.add(user2)
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


MOCK_AI_TARGET = "app.modules.chat.service.generate_ai_response"
MOCK_AI_RESPONSE = "Olá! Posso ajudar com agendamentos."


@pytest.fixture(autouse=True)
def mock_llm():
    """Mock global do LLM — nenhum teste chama a API real do Groq."""
    with patch(MOCK_AI_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
        yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest_asyncio.fixture
async def db_session():
    async with test_async_session() as session:
        yield session
