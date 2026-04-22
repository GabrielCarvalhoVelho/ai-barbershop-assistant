import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.exceptions import ConflictError, DatabaseError, ServiceUnavailableError
from app.db.database import Base
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.user import User
from app.modules.chat.repository import ConversationRepository, MessageRepository


# ========================
# Fixtures isoladas para testes de repositório
# ========================

@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def conversation(session):
    company = Company(name="Barbearia Teste")
    session.add(company)
    await session.commit()
    await session.refresh(company)

    user = User(
        company_id=company.id,
        name="João",
        phone="+5511999000111",
        password_hash="placeholder",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    conv = Conversation(user_id=user.id, company_id=company.id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


# ========================
# Repository — IntegrityError → ConflictError
# ========================

class TestRepositoryIntegrityError:
    @pytest.mark.asyncio
    async def test_save_fk_invalid_raises_conflict_error(
        self, session, conversation
    ):
        """IntegrityError no commit → ConflictError."""
        repo = MessageRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=IntegrityError(
                statement="INSERT",
                params={},
                orig=Exception("FOREIGN KEY constraint failed"),
            ),
        ), pytest.raises(ConflictError) as exc_info:
            await repo.save(conversation.id, "user", "teste")
        assert exc_info.value.code == "DB_002"

    @pytest.mark.asyncio
    async def test_save_conflict_error_has_message(self, session, conversation):
        repo = MessageRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=IntegrityError(
                statement="INSERT",
                params={},
                orig=Exception("UNIQUE constraint failed"),
            ),
        ), pytest.raises(ConflictError) as exc_info:
            await repo.save(conversation.id, "user", "x")
        assert "salvar" in exc_info.value.message


# ========================
# Repository — OperationalError → ServiceUnavailableError
# ========================

class TestRepositoryOperationalError:
    @pytest.mark.asyncio
    async def test_save_db_down_raises_service_unavailable(self, session, conversation):
        """OperationalError no commit → ServiceUnavailableError."""
        repo = MessageRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=OperationalError(
                statement="INSERT", params={}, orig=Exception("connection refused")
            ),
        ), pytest.raises(ServiceUnavailableError) as exc_info:
            await repo.save(conversation.id, "user", "teste")
        assert exc_info.value.code == "DB_003"

    @pytest.mark.asyncio
    async def test_get_by_id_db_down_raises_service_unavailable(self, session):
        """OperationalError no get → ServiceUnavailableError."""
        repo = MessageRepository(session)
        with patch.object(
            session,
            "get",
            new_callable=AsyncMock,
            side_effect=OperationalError(
                statement="SELECT", params={}, orig=Exception("timeout")
            ),
        ), pytest.raises(ServiceUnavailableError):
            await repo.get_by_id(1)

    @pytest.mark.asyncio
    async def test_get_by_conversation_db_down_raises_service_unavailable(
        self, session
    ):
        """OperationalError no execute → ServiceUnavailableError."""
        repo = MessageRepository(session)
        with patch.object(
            session,
            "execute",
            new_callable=AsyncMock,
            side_effect=OperationalError(
                statement="SELECT", params={}, orig=Exception("pool exhausted")
            ),
        ), pytest.raises(ServiceUnavailableError):
            await repo.get_by_conversation(1)


# ========================
# Repository — SQLAlchemyError → DatabaseError
# ========================

class TestRepositorySQLAlchemyError:
    @pytest.mark.asyncio
    async def test_save_generic_db_error_raises_database_error(
        self, session, conversation
    ):
        repo = MessageRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=SQLAlchemyError("unexpected"),
        ), pytest.raises(DatabaseError) as exc_info:
            await repo.save(conversation.id, "user", "teste")
        assert exc_info.value.code == "DB_001"


# ========================
# Repository — Timeout → ServiceUnavailableError
# ========================

class TestRepositoryTimeout:
    @pytest.mark.asyncio
    async def test_save_timeout_raises_service_unavailable(
        self, session, conversation
    ):
        """asyncio.TimeoutError no flush → ServiceUnavailableError."""
        repo = MessageRepository(session)

        async def slow_flush():
            await asyncio.sleep(999)

        with patch.object(session, "flush", side_effect=slow_flush), patch(
            "app.modules.chat.repository.DB_TIMEOUT_SECONDS", 0.01
        ), pytest.raises(ServiceUnavailableError) as exc_info:
            await repo.save(conversation.id, "user", "teste")
        assert exc_info.value.code == "DB_003"

    @pytest.mark.asyncio
    async def test_get_by_id_timeout_raises_service_unavailable(self, session):
        repo = MessageRepository(session)

        async def slow_get(*args, **kwargs):
            await asyncio.sleep(999)

        with patch.object(session, "get", side_effect=slow_get), patch(
            "app.modules.chat.repository.DB_TIMEOUT_SECONDS", 0.01
        ), pytest.raises(ServiceUnavailableError):
            await repo.get_by_id(1)


# ========================
# ConversationRepository — IntegrityError → ConflictError
# ========================

class TestConversationRepositoryIntegrityError:
    @pytest.mark.asyncio
    async def test_create_fk_invalid_raises_conflict_error(self, session):
        """IntegrityError no commit → ConflictError."""
        repo = ConversationRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=IntegrityError(
                statement="INSERT",
                params={},
                orig=Exception("FOREIGN KEY constraint failed"),
            ),
        ), pytest.raises(ConflictError) as exc_info:
            await repo.create(user_id=1, company_id=1)
        assert exc_info.value.code == "DB_002"


# ========================
# ConversationRepository — OperationalError → ServiceUnavailableError
# ========================

class TestConversationRepositoryOperationalError:
    @pytest.mark.asyncio
    async def test_create_db_down_raises_service_unavailable(self, session):
        repo = ConversationRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=OperationalError(
                statement="INSERT", params={}, orig=Exception("connection refused")
            ),
        ), pytest.raises(ServiceUnavailableError) as exc_info:
            await repo.create(user_id=1, company_id=1)
        assert exc_info.value.code == "DB_003"

    @pytest.mark.asyncio
    async def test_get_by_id_db_down_raises_service_unavailable(self, session):
        repo = ConversationRepository(session)
        with patch.object(
            session,
            "get",
            new_callable=AsyncMock,
            side_effect=OperationalError(
                statement="SELECT", params={}, orig=Exception("timeout")
            ),
        ), pytest.raises(ServiceUnavailableError):
            await repo.get_by_id(1)

    @pytest.mark.asyncio
    async def test_close_db_down_raises_service_unavailable(self, session):
        repo = ConversationRepository(session)
        with patch.object(
            session,
            "get",
            new_callable=AsyncMock,
            side_effect=OperationalError(
                statement="SELECT", params={}, orig=Exception("connection refused")
            ),
        ), pytest.raises(ServiceUnavailableError):
            await repo.close(1)


# ========================
# ConversationRepository — Timeout → ServiceUnavailableError
# ========================

class TestConversationRepositoryTimeout:
    @pytest.mark.asyncio
    async def test_create_timeout_raises_service_unavailable(self, session):
        repo = ConversationRepository(session)

        async def slow_flush():
            await asyncio.sleep(999)

        with patch.object(session, "flush", side_effect=slow_flush), patch(
            "app.modules.chat.repository.DB_TIMEOUT_SECONDS", 0.01
        ), pytest.raises(ServiceUnavailableError) as exc_info:
            await repo.create(user_id=1, company_id=1)
        assert exc_info.value.code == "DB_003"


# ========================
# Repositories — erro propaga para o session manager fazer rollback
# ========================

class TestRepositoryErrorPropagation:
    @pytest.mark.asyncio
    async def test_conversation_integrity_error_propagates_as_conflict(self, session):
        """IntegrityError no flush propaga como ConflictError — session manager faz rollback."""
        repo = ConversationRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=IntegrityError(
                statement="INSERT",
                params={},
                orig=Exception("FK failed"),
            ),
        ), pytest.raises(ConflictError):
            await repo.create(user_id=999, company_id=999)

    @pytest.mark.asyncio
    async def test_message_integrity_error_propagates_as_conflict(
        self, session, conversation
    ):
        """IntegrityError no flush propaga como ConflictError — session manager faz rollback."""
        repo = MessageRepository(session)
        with patch.object(
            session,
            "flush",
            new_callable=AsyncMock,
            side_effect=IntegrityError(
                statement="INSERT",
                params={},
                orig=Exception("FK failed"),
            ),
        ), pytest.raises(ConflictError):
            await repo.save(conversation.id, "user", "x")


# ========================
# Controller — AppError propagado do repository
# ========================

class TestControllerErrorPropagation:
    @pytest.mark.asyncio
    async def test_conflict_error_propagates_from_repository(self):
        from app.modules.chat.controller import ChatController
        from app.modules.chat.schemas import ChatRequest

        mock_user = AsyncMock()
        mock_user.id = 1
        mock_user.company_id = 1
        mock_conv_repo = AsyncMock()
        mock_conv_repo.create.return_value = AsyncMock(id=1)
        mock_msg_repo = AsyncMock()
        mock_msg_repo.save_pair.side_effect = ConflictError(
            message="FK violation",
        )
        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id.return_value = AsyncMock(id=1)
        mock_knowledge_repo = AsyncMock()
        mock_knowledge_repo.get_by_company.return_value = []

        request = ChatRequest(message="Quero agendar")
        with pytest.raises(ConflictError):
            await ChatController.send_message(
                request, current_user=mock_user,
                conversation_repo=mock_conv_repo, message_repo=mock_msg_repo,
                company_repo=mock_company_repo,
                knowledge_repo=mock_knowledge_repo,
            )

    @pytest.mark.asyncio
    async def test_service_unavailable_propagates_from_repository(self):
        from app.modules.chat.controller import ChatController
        from app.modules.chat.schemas import ChatRequest

        mock_user = AsyncMock()
        mock_user.id = 1
        mock_user.company_id = 1
        mock_conv_repo = AsyncMock()
        mock_conv_repo.create.return_value = AsyncMock(id=1)
        mock_msg_repo = AsyncMock()
        mock_msg_repo.save_pair.side_effect = ServiceUnavailableError(
            message="DB down",
        )
        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id.return_value = AsyncMock(id=1)
        mock_knowledge_repo = AsyncMock()
        mock_knowledge_repo.get_by_company.return_value = []

        request = ChatRequest(message="Quero agendar")
        with pytest.raises(ServiceUnavailableError):
            await ChatController.send_message(
                request, current_user=mock_user,
                conversation_repo=mock_conv_repo, message_repo=mock_msg_repo,
                company_repo=mock_company_repo,
                knowledge_repo=mock_knowledge_repo,
            )


# ========================
# Validation handler — field name nos detalhes
# ========================

class TestValidationFieldName:
    def test_empty_message_includes_field_in_details(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": ""},
            headers=auth_headers,
        )
        body = response.json()
        assert body["error"]["field"] == "message"

    def test_missing_field_includes_field_name(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={},
            headers=auth_headers,
        )
        body = response.json()
        assert body["error"]["field"] == "message"

    def test_details_include_field_prefix(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "!!!"},
            headers=auth_headers,
        )
        details = response.json()["error"]["details"]
        assert any("message:" in d for d in details)

    def test_field_is_absent_on_non_validation_errors(self, client, auth_headers):
        """Erros não-validação não devem ter campo field."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "spam spam spam spam spam"},
            headers=auth_headers,
        )
        body = response.json()
        assert "field" not in body.get("error", {})
