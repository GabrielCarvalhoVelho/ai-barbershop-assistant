from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AuthorizationError, BusinessError, NotFoundError
from app.modules.chat.controller import ChatController
from app.modules.chat.schemas import ChatRequest
from app.schemas.base_schema import SuccessResponse


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


def _make_repos(conversation=None):
    conv_repo = AsyncMock()
    msg_repo = AsyncMock()
    user_repo = AsyncMock()
    company_repo = AsyncMock()

    conv_repo.create.return_value = conversation or _make_conversation()
    conv_repo.get_by_id.return_value = conversation
    msg_repo.save_pair.return_value = (_make_message(id_=1), _make_message(id_=2))
    user_repo.get_by_id.return_value = AsyncMock(id=1)
    company_repo.get_by_id.return_value = AsyncMock(id=1)

    return conv_repo, msg_repo, user_repo, company_repo


# ========================
# Fluxo sem conversation_id (nova conversa)
# ========================


class TestChatControllerNewConversation:
    @pytest.mark.asyncio
    async def test_creates_conversation_when_no_id(self):
        conv = _make_conversation(id_=10)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)

        request = ChatRequest(message="Quero agendar", user_id=1, company_id=1)
        response = await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        conv_repo.create.assert_called_once_with(user_id=1, company_id=1)
        assert response.data["conversation_id"] == 10

    @pytest.mark.asyncio
    async def test_passes_user_and_company_to_create(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()
        user_repo.get_by_id.return_value = AsyncMock(id=7)
        company_repo.get_by_id.return_value = AsyncMock(id=3)

        request = ChatRequest(message="Oi", user_id=7, company_id=3)
        await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        conv_repo.create.assert_called_once_with(user_id=7, company_id=3)

    @pytest.mark.asyncio
    async def test_returns_success_response(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()

        request = ChatRequest(message="Olá", user_id=1, company_id=1)
        response = await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        assert isinstance(response, SuccessResponse)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_data_contains_response_and_conversation_id(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()

        request = ChatRequest(message="Olá", user_id=1, company_id=1)
        response = await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        assert "response" in response.data
        assert "conversation_id" in response.data

    @pytest.mark.asyncio
    async def test_response_has_echo(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()

        request = ChatRequest(message="Olá", user_id=1, company_id=1)
        response = await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        assert response.data["response"] == "Você disse: Olá"

    @pytest.mark.asyncio
    async def test_saves_user_and_bot_messages_atomically(self):
        conv = _make_conversation(id_=5)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)

        request = ChatRequest(message="Oi", user_id=1, company_id=1)
        await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        msg_repo.save_pair.assert_called_once_with(
            conversation_id=5,
            user_content="Oi",
            bot_content="Você disse: Oi",
        )


# ========================
# Fluxo com conversation_id (conversa existente)
# ========================


class TestChatControllerExistingConversation:
    @pytest.mark.asyncio
    async def test_uses_existing_conversation(self):
        conv = _make_conversation(id_=42)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)

        request = ChatRequest(message="Oi", user_id=1, company_id=1, conversation_id=42)
        response = await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        conv_repo.get_by_id.assert_called_once_with(42)
        conv_repo.create.assert_not_called()
        assert response.data["conversation_id"] == 42

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()
        conv_repo.get_by_id.return_value = None

        request = ChatRequest(message="Oi", user_id=1, company_id=1, conversation_id=999)

        with pytest.raises(NotFoundError) as exc_info:
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

        assert "999" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_closed_conversation_raises_400(self):
        conv = _make_conversation(id_=42, status="closed")
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)

        request = ChatRequest(message="Oi", user_id=1, company_id=1, conversation_id=42)

        with pytest.raises(BusinessError) as exc_info:
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

        assert "encerrada" in exc_info.value.message
        msg_repo.save_pair.assert_not_called()


# ========================
# Validação de user e company
# ========================


class TestChatControllerUserCompanyValidation:
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()
        user_repo.get_by_id.return_value = None

        request = ChatRequest(message="Oi", user_id=999, company_id=1)

        with pytest.raises(NotFoundError) as exc_info:
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

        assert "999" in exc_info.value.message
        conv_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_company_not_found_raises_404(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()
        company_repo.get_by_id.return_value = None

        request = ChatRequest(message="Oi", user_id=1, company_id=888)

        with pytest.raises(NotFoundError) as exc_info:
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

        assert "888" in exc_info.value.message
        conv_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_validates_user_before_company(self):
        """Se user não existe, nem checa company."""
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()
        user_repo.get_by_id.return_value = None

        request = ChatRequest(message="Oi", user_id=999, company_id=1)

        with pytest.raises(NotFoundError):
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

        company_repo.get_by_id.assert_not_called()


# ========================
# Validação de ownership da conversa
# ========================


class TestChatControllerConversationOwnership:
    @pytest.mark.asyncio
    async def test_wrong_user_id_raises_403(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)
        user_repo.get_by_id.return_value = AsyncMock(id=99)
        company_repo.get_by_id.return_value = AsyncMock(id=1)

        request = ChatRequest(message="Oi", user_id=99, company_id=1, conversation_id=42)

        with pytest.raises(AuthorizationError) as exc_info:
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

        assert "não pertence" in exc_info.value.message
        msg_repo.save_pair.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_company_id_raises_403(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)
        user_repo.get_by_id.return_value = AsyncMock(id=1)
        company_repo.get_by_id.return_value = AsyncMock(id=99)

        request = ChatRequest(message="Oi", user_id=1, company_id=99, conversation_id=42)

        with pytest.raises(AuthorizationError) as exc_info:
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

        assert "não pertence" in exc_info.value.message
        msg_repo.save_pair.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_user_and_company_raises_403(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)
        user_repo.get_by_id.return_value = AsyncMock(id=50)
        company_repo.get_by_id.return_value = AsyncMock(id=60)

        request = ChatRequest(message="Oi", user_id=50, company_id=60, conversation_id=42)

        with pytest.raises(AuthorizationError):
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )

    @pytest.mark.asyncio
    async def test_correct_ownership_passes(self):
        conv = _make_conversation(id_=42, user_id=1, company_id=1)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)

        request = ChatRequest(message="Oi", user_id=1, company_id=1, conversation_id=42)
        response = await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        assert response.data["conversation_id"] == 42

    @pytest.mark.asyncio
    async def test_ownership_checked_before_closed_status(self):
        """Se a conversa não pertence ao user, retorna 403 mesmo que esteja closed."""
        conv = _make_conversation(id_=42, status="closed", user_id=1, company_id=1)
        conv_repo, msg_repo, user_repo, company_repo = _make_repos(conv)
        user_repo.get_by_id.return_value = AsyncMock(id=99)
        company_repo.get_by_id.return_value = AsyncMock(id=1)

        request = ChatRequest(message="Oi", user_id=99, company_id=1, conversation_id=42)

        with pytest.raises(AuthorizationError):
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )


# ========================
# Delegação ao service
# ========================


class TestChatControllerServiceDelegation:
    @pytest.mark.asyncio
    async def test_delegates_sanitization_to_service(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()

        request = ChatRequest(message="quero   agendar    corte", user_id=1, company_id=1)
        response = await ChatController.send_message(
            request, conv_repo, msg_repo, user_repo, company_repo
        )

        assert response.data["response"] == "Você disse: quero agendar corte"

    @pytest.mark.asyncio
    async def test_delegates_business_validation_to_service(self):
        conv_repo, msg_repo, user_repo, company_repo = _make_repos()

        request = ChatRequest(message="spam spam spam spam spam", user_id=1, company_id=1)
        with pytest.raises(BusinessError):
            await ChatController.send_message(
                request, conv_repo, msg_repo, user_repo, company_repo
            )
