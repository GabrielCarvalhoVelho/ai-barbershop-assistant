from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AuthorizationError, BusinessError, NotFoundError
from app.modules.chat.controller import ChatController
from app.modules.chat.schemas import ChatRequest
from app.schemas.base_schema import SuccessResponse

MOCK_AI_RESPONSE = "Olá! Posso ajudar com agendamentos."
MOCK_TARGET = "app.modules.chat.service.generate_ai_response"


def _make_conversation(id_: int = 1, status: str = "active", user_id: int = 1, company_id: int = 1):
    conv = AsyncMock()
    conv.id = id_
    conv.status = status
    conv.user_id = user_id
    conv.company_id = company_id
    return conv


def _make_message(id_: int = 1):
    msg = AsyncMock()
    msg.id = id_
    return msg


def _make_company(id_: int = 1, name: str = "Barbearia Teste", phone: str | None = None, address: str | None = None):
    company = AsyncMock()
    company.id = id_
    company.name = name
    company.phone = phone
    company.address = address
    return company


def _make_user(id_: int = 1, company_id: int = 1):
    user = AsyncMock()
    user.id = id_
    user.company_id = company_id
    return user


def _make_repos(conversation=None):
    conv_repo = AsyncMock()
    msg_repo = AsyncMock()
    company_repo = AsyncMock()
    knowledge_repo = AsyncMock()

    conv_repo.create.return_value = conversation or _make_conversation()
    conv_repo.get_by_id.return_value = conversation
    msg_repo.save_pair.return_value = (_make_message(id_=1), _make_message(id_=2))
    msg_repo.get_by_conversation.return_value = []
    company_repo.get_by_id.return_value = _make_company()
    knowledge_repo.get_by_company.return_value = []

    return conv_repo, msg_repo, company_repo, knowledge_repo


def _call(request, *repos, user_id=1, company_id=1):
    conv_repo, msg_repo, company_repo, knowledge_repo = repos
    return ChatController.send_message(
        request,
        current_user=_make_user(id_=user_id, company_id=company_id),
        conversation_repo=conv_repo,
        message_repo=msg_repo,
        company_repo=company_repo,
        knowledge_repo=knowledge_repo,
    )


# ========================
# Fluxo sem conversation_id (nova conversa)
# ========================


class TestChatControllerNewConversation:
    @pytest.mark.asyncio
    async def test_creates_conversation_when_no_id(self):
        conv = _make_conversation(id_=10)
        repos = _make_repos(conv)

        request = ChatRequest(message="Quero agendar")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            response = await _call(request, *repos)

        repos[0].create.assert_called_once_with(user_id=1, company_id=1)
        assert response.data["conversation_id"] == 10

    @pytest.mark.asyncio
    async def test_passes_user_and_company_to_create(self):
        repos = _make_repos()
        conv_repo, _, company_repo, _ = repos
        company_repo.get_by_id.return_value = _make_company(id_=3)

        request = ChatRequest(message="Oi")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            await _call(request, *repos, user_id=7, company_id=3)

        conv_repo.create.assert_called_once_with(user_id=7, company_id=3)

    @pytest.mark.asyncio
    async def test_returns_success_response(self):
        repos = _make_repos()

        request = ChatRequest(message="Olá")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            response = await _call(request, *repos)

        assert isinstance(response, SuccessResponse)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_data_contains_response_and_conversation_id(self):
        repos = _make_repos()

        request = ChatRequest(message="Olá")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            response = await _call(request, *repos)

        assert "response" in response.data
        assert "conversation_id" in response.data

    @pytest.mark.asyncio
    async def test_response_comes_from_llm(self):
        repos = _make_repos()

        request = ChatRequest(message="Olá")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            response = await _call(request, *repos)

        assert response.data["response"] == MOCK_AI_RESPONSE

    @pytest.mark.asyncio
    async def test_saves_user_and_bot_messages_atomically(self):
        conv = _make_conversation(id_=5)
        repos = _make_repos(conv)
        _, msg_repo, *_ = repos

        request = ChatRequest(message="Oi")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            await _call(request, *repos)

        msg_repo.save_pair.assert_called_once_with(
            conversation_id=5,
            user_content="Oi",
            bot_content=MOCK_AI_RESPONSE,
        )


# ========================
# Fluxo com conversation_id (conversa existente)
# ========================


class TestChatControllerExistingConversation:
    @pytest.mark.asyncio
    async def test_uses_existing_conversation(self):
        conv = _make_conversation(id_=42)
        repos = _make_repos(conv)

        request = ChatRequest(message="Oi", conversation_id=42)
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            response = await _call(request, *repos)

        repos[0].get_by_id.assert_called_once_with(42)
        repos[0].create.assert_not_called()
        assert response.data["conversation_id"] == 42

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        repos = _make_repos()
        repos[0].get_by_id.return_value = None

        request = ChatRequest(message="Oi", conversation_id=999)

        with pytest.raises(NotFoundError) as exc_info:
            await _call(request, *repos)

        assert "999" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_closed_conversation_raises_400(self):
        conv = _make_conversation(id_=42, status="closed")
        repos = _make_repos(conv)

        request = ChatRequest(message="Oi", conversation_id=42)

        with pytest.raises(BusinessError) as exc_info:
            await _call(request, *repos)

        assert "encerrada" in exc_info.value.message
        repos[1].save_pair.assert_not_called()


# ========================
# Validação de company
# ========================


class TestChatControllerCompanyValidation:
    @pytest.mark.asyncio
    async def test_company_not_found_raises_404(self):
        repos = _make_repos()
        repos[2].get_by_id.return_value = None

        request = ChatRequest(message="Oi")

        with pytest.raises(NotFoundError) as exc_info:
            await _call(request, *repos, user_id=1, company_id=888)

        assert "888" in exc_info.value.message
        repos[0].create.assert_not_called()


# ========================
# Validação de ownership da conversa
# ========================


class TestChatControllerConversationOwnership:
    @pytest.mark.asyncio
    async def test_wrong_user_id_raises_403(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        repos = _make_repos(conv)

        request = ChatRequest(message="Oi", conversation_id=42)

        with pytest.raises(AuthorizationError) as exc_info:
            await _call(request, *repos, user_id=99, company_id=1)

        assert "não pertence" in exc_info.value.message
        repos[1].save_pair.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_company_id_raises_403(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        repos = _make_repos(conv)

        request = ChatRequest(message="Oi", conversation_id=42)

        with pytest.raises(AuthorizationError) as exc_info:
            await _call(request, *repos, user_id=1, company_id=99)

        assert "não pertence" in exc_info.value.message
        repos[1].save_pair.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_user_and_company_raises_403(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        repos = _make_repos(conv)

        request = ChatRequest(message="Oi", conversation_id=42)

        with pytest.raises(AuthorizationError):
            await _call(request, *repos, user_id=50, company_id=60)

    @pytest.mark.asyncio
    async def test_correct_ownership_passes(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        repos = _make_repos(conv)

        request = ChatRequest(message="Oi", conversation_id=42)
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            response = await _call(request, *repos)

        assert response.data["conversation_id"] == 42

    @pytest.mark.asyncio
    async def test_ownership_checked_before_closed_status(self):
        """Se a conversa não pertence ao user, retorna 403 mesmo que esteja closed."""
        conv = _make_conversation(id_=42, status="closed", user_id=1, company_id=1)
        repos = _make_repos(conv)

        request = ChatRequest(message="Oi", conversation_id=42)

        with pytest.raises(AuthorizationError):
            await _call(request, *repos, user_id=99, company_id=1)


# ========================
# Delegação ao service
# ========================


class TestChatControllerServiceDelegation:
    @pytest.mark.asyncio
    async def test_delegates_sanitization_to_service(self):
        repos = _make_repos()

        request = ChatRequest(message="quero   agendar    corte")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            response = await _call(request, *repos)

        assert response.data["response"] == MOCK_AI_RESPONSE

    @pytest.mark.asyncio
    async def test_delegates_business_validation_to_service(self):
        repos = _make_repos()

        request = ChatRequest(message="spam spam spam spam spam")
        with pytest.raises(BusinessError):
            await _call(request, *repos)


# ========================
# Busca de contexto (RAG)
# ========================


class TestChatControllerKnowledgeContext:
    @pytest.mark.asyncio
    async def test_fetches_documents_for_company(self):
        repos = _make_repos()

        request = ChatRequest(message="Quanto custa o corte?")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            await _call(request, *repos, company_id=1)

        repos[3].get_by_company.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_passes_context_to_system_prompt(self):
        """Com documentos, o system_prompt contém os dados do knowledge base."""
        from types import SimpleNamespace
        from app.models.enums import DocumentCategory

        doc = SimpleNamespace(
            title="Corte masculino",
            content="R$ 40,00",
            category=DocumentCategory.SERVICES,
        )
        repos = _make_repos()
        repos[3].get_by_company.return_value = [doc]

        request = ChatRequest(message="Quanto custa?")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await _call(request, *repos)

        system_prompt = mock_llm.call_args[0][2]
        assert "Corte masculino" in system_prompt
        assert "R$ 40,00" in system_prompt

    @pytest.mark.asyncio
    async def test_empty_documents_omits_context_section(self):
        """Sem documentos, o system_prompt não contém seção de contexto."""
        repos = _make_repos()
        repos[3].get_by_company.return_value = []

        request = ChatRequest(message="Olá")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await _call(request, *repos)

        system_prompt = mock_llm.call_args[0][2]
        assert "Use as informações abaixo" not in system_prompt

    @pytest.mark.asyncio
    async def test_fetches_docs_with_correct_company_id(self):
        """Usa o company_id do token, não um valor hardcoded."""
        repos = _make_repos()
        repos[2].get_by_id.return_value = _make_company(id_=5)

        request = ChatRequest(message="Oi")
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            await _call(request, *repos, user_id=7, company_id=5)

        repos[3].get_by_company.assert_called_once_with(5)
