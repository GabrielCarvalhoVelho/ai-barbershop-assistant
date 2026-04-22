from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import BusinessError, NotFoundError
from app.modules.chat.controller import ConversationController
from app.schemas.base_schema import SuccessResponse


def _make_conversation(id_: int = 1, user_id: int = 1, company_id: int = 1):
    from datetime import datetime, timezone

    conv = AsyncMock()
    conv.id = id_
    conv.user_id = user_id
    conv.company_id = company_id
    conv.status = "active"
    conv.started_at = datetime(2026, 3, 30, 14, 0, 0, tzinfo=timezone.utc)
    conv.ended_at = None
    return conv


def _make_user(id_: int = 1, company_id: int = 1):
    user = AsyncMock()
    user.id = id_
    user.company_id = company_id
    return user


def _make_repos(conversation=None):
    conv_repo = AsyncMock()
    company_repo = AsyncMock()

    conv_repo.create.return_value = conversation or _make_conversation()
    company_repo.get_by_id.return_value = AsyncMock(id=1)

    return conv_repo, company_repo


# ========================
# POST /conversations — sucesso
# ========================


class TestConversationControllerCreate:
    @pytest.mark.asyncio
    async def test_creates_conversation(self):
        conv = _make_conversation(id_=10, user_id=1, company_id=1)
        conv_repo, company_repo = _make_repos(conv)

        response = await ConversationController.create(
            current_user=_make_user(id_=1, company_id=1),
            conversation_repo=conv_repo, company_repo=company_repo,
        )

        conv_repo.create.assert_called_once_with(user_id=1, company_id=1)
        assert response.data["id"] == 10

    @pytest.mark.asyncio
    async def test_returns_success_response(self):
        conv_repo, company_repo = _make_repos()

        response = await ConversationController.create(
            current_user=_make_user(),
            conversation_repo=conv_repo, company_repo=company_repo,
        )

        assert isinstance(response, SuccessResponse)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_data_contains_all_fields(self):
        conv = _make_conversation(id_=5, user_id=1, company_id=1)
        conv_repo, company_repo = _make_repos(conv)

        response = await ConversationController.create(
            current_user=_make_user(id_=1, company_id=1),
            conversation_repo=conv_repo, company_repo=company_repo,
        )

        data = response.data
        assert data["id"] == 5
        assert data["user_id"] == 1
        assert data["company_id"] == 1
        assert data["status"] == "active"
        assert data["started_at"] is not None
        assert data["ended_at"] is None

    @pytest.mark.asyncio
    async def test_passes_correct_ids_to_repo(self):
        conv_repo, company_repo = _make_repos()

        await ConversationController.create(
            current_user=_make_user(id_=7, company_id=3),
            conversation_repo=conv_repo, company_repo=company_repo,
        )

        conv_repo.create.assert_called_once_with(user_id=7, company_id=3)


# ========================
# POST /conversations — user/company não encontrados
# ========================


class TestConversationControllerNotFound:
    @pytest.mark.asyncio
    async def test_company_not_found_raises_404(self):
        conv_repo, company_repo = _make_repos()
        company_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await ConversationController.create(
                current_user=_make_user(id_=1, company_id=888),
                conversation_repo=conv_repo, company_repo=company_repo,
            )

        assert "888" in exc_info.value.message
        conv_repo.create.assert_not_called()


# ========================
# GET /conversations/{id} — sucesso
# ========================


class TestConversationControllerGetById:
    @pytest.mark.asyncio
    async def test_returns_conversation(self):
        conv = _make_conversation(id_=10, user_id=1, company_id=1)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.count_by_conversation.return_value = 5

        response = await ConversationController.get_by_id(
            10, conv_repo, msg_repo
        )

        conv_repo.get_by_id.assert_called_once_with(10)
        assert isinstance(response, SuccessResponse)
        assert response.data["id"] == 10

    @pytest.mark.asyncio
    async def test_data_contains_all_fields(self):
        conv = _make_conversation(id_=3, user_id=2, company_id=4)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.count_by_conversation.return_value = 8

        response = await ConversationController.get_by_id(
            3, conv_repo, msg_repo
        )

        data = response.data
        assert data["id"] == 3
        assert data["user_id"] == 2
        assert data["company_id"] == 4
        assert data["status"] == "active"
        assert data["started_at"] is not None
        assert data["ended_at"] is None
        assert data["message_count"] == 8

    @pytest.mark.asyncio
    async def test_includes_message_count(self):
        conv = _make_conversation(id_=1)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.count_by_conversation.return_value = 42

        response = await ConversationController.get_by_id(
            1, conv_repo, msg_repo
        )

        msg_repo.count_by_conversation.assert_called_once_with(1)
        assert response.data["message_count"] == 42

    @pytest.mark.asyncio
    async def test_zero_messages(self):
        conv = _make_conversation(id_=1)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.count_by_conversation.return_value = 0

        response = await ConversationController.get_by_id(
            1, conv_repo, msg_repo
        )

        assert response.data["message_count"] == 0

    @pytest.mark.asyncio
    async def test_ended_at_is_serialized(self):
        from datetime import datetime, timezone

        conv = _make_conversation(id_=1)
        conv.ended_at = datetime(2026, 3, 31, 18, 0, 0, tzinfo=timezone.utc)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.count_by_conversation.return_value = 3

        response = await ConversationController.get_by_id(
            1, conv_repo, msg_repo
        )

        assert response.data["ended_at"] is not None


# ========================
# GET /conversations/{id} — não encontrada
# ========================


class TestConversationControllerGetByIdNotFound:
    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await ConversationController.get_by_id(
                999, conv_repo, msg_repo
            )

        assert "999" in exc_info.value.message
        msg_repo.count_by_conversation.assert_not_called()


# ========================
# GET /conversations/{id}/messages — sucesso
# ========================


def _make_message(id_: int = 1, sender: str = "user", content: str = "Oi"):
    from datetime import datetime, timezone

    msg = AsyncMock()
    msg.id = id_
    msg.sender = sender
    msg.content = content
    msg.created_at = datetime(2026, 3, 30, 14, 0, 0, tzinfo=timezone.utc)
    return msg


class TestConversationControllerGetMessages:
    @pytest.mark.asyncio
    async def test_returns_messages(self):
        conv = _make_conversation(id_=1)
        msg1 = _make_message(id_=1, sender="user", content="Oi")
        msg2 = _make_message(id_=2, sender="bot", content="Olá!")

        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.get_by_conversation.return_value = [msg1, msg2]
        msg_repo.count_by_conversation.return_value = 2

        response = await ConversationController.get_messages(
            1, limit=50, offset=0,
            conversation_repo=conv_repo, message_repo=msg_repo
        )

        assert isinstance(response, SuccessResponse)
        assert response.data["conversation_id"] == 1
        assert len(response.data["messages"]) == 2

    @pytest.mark.asyncio
    async def test_message_fields(self):
        conv = _make_conversation(id_=1)
        msg = _make_message(id_=5, sender="user", content="Quero cortar")

        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.get_by_conversation.return_value = [msg]
        msg_repo.count_by_conversation.return_value = 1

        response = await ConversationController.get_messages(
            1, limit=50, offset=0,
            conversation_repo=conv_repo, message_repo=msg_repo
        )

        m = response.data["messages"][0]
        assert m["id"] == 5
        assert m["sender"] == "user"
        assert m["content"] == "Quero cortar"
        assert m["created_at"] is not None

    @pytest.mark.asyncio
    async def test_pagination_metadata(self):
        conv = _make_conversation(id_=1)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.get_by_conversation.return_value = [_make_message()]
        msg_repo.count_by_conversation.return_value = 15

        response = await ConversationController.get_messages(
            1, limit=10, offset=5,
            conversation_repo=conv_repo, message_repo=msg_repo
        )

        pagination = response.data["pagination"]
        assert pagination["limit"] == 10
        assert pagination["offset"] == 5
        assert pagination["total"] == 15

    @pytest.mark.asyncio
    async def test_passes_limit_and_offset_to_repo(self):
        conv = _make_conversation(id_=1)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.get_by_conversation.return_value = []
        msg_repo.count_by_conversation.return_value = 0

        await ConversationController.get_messages(
            1, limit=20, offset=10,
            conversation_repo=conv_repo, message_repo=msg_repo
        )

        msg_repo.get_by_conversation.assert_called_once_with(
            1, limit=20, offset=10
        )

    @pytest.mark.asyncio
    async def test_empty_messages(self):
        conv = _make_conversation(id_=1)
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        msg_repo.get_by_conversation.return_value = []
        msg_repo.count_by_conversation.return_value = 0

        response = await ConversationController.get_messages(
            1, limit=50, offset=0,
            conversation_repo=conv_repo, message_repo=msg_repo
        )

        assert response.data["messages"] == []
        assert response.data["pagination"]["total"] == 0


# ========================
# GET /conversations/{id}/messages — não encontrada
# ========================


class TestConversationControllerGetMessagesNotFound:
    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        conv_repo = AsyncMock()
        msg_repo = AsyncMock()
        conv_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await ConversationController.get_messages(
                999, limit=50, offset=0,
                conversation_repo=conv_repo, message_repo=msg_repo
            )

        assert "999" in exc_info.value.message
        msg_repo.get_by_conversation.assert_not_called()


# ========================
# PATCH /conversations/{id}/close — sucesso
# ========================


def _make_closed_conversation(id_: int = 1):
    from datetime import datetime, timezone

    conv = _make_conversation(id_=id_)
    conv.status = "closed"
    conv.ended_at = datetime(2026, 3, 31, 18, 0, 0, tzinfo=timezone.utc)
    return conv


class TestConversationControllerClose:
    @pytest.mark.asyncio
    async def test_closes_conversation(self):
        conv = _make_conversation(id_=10)
        closed = _make_closed_conversation(id_=10)

        conv_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        conv_repo.close.return_value = closed

        response = await ConversationController.close(10, conv_repo)

        conv_repo.close.assert_called_once_with(10)
        assert isinstance(response, SuccessResponse)
        assert response.data["id"] == 10
        assert response.data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_data_contains_all_fields(self):
        conv = _make_conversation(id_=5, user_id=2, company_id=3)
        closed = _make_closed_conversation(id_=5)
        closed.user_id = 2
        closed.company_id = 3

        conv_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        conv_repo.close.return_value = closed

        response = await ConversationController.close(5, conv_repo)

        data = response.data
        assert data["id"] == 5
        assert data["user_id"] == 2
        assert data["company_id"] == 3
        assert data["status"] == "closed"
        assert data["started_at"] is not None
        assert data["ended_at"] is not None

    @pytest.mark.asyncio
    async def test_ended_at_is_filled(self):
        conv = _make_conversation(id_=1)
        closed = _make_closed_conversation(id_=1)

        conv_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv
        conv_repo.close.return_value = closed

        response = await ConversationController.close(1, conv_repo)

        assert response.data["ended_at"] is not None


# ========================
# PATCH /conversations/{id}/close — erros
# ========================


class TestConversationControllerCloseErrors:
    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        conv_repo = AsyncMock()
        conv_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await ConversationController.close(999, conv_repo)

        assert "999" in exc_info.value.message
        conv_repo.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_closed_raises_400(self):
        conv = _make_conversation(id_=1)
        conv.status = "closed"

        conv_repo = AsyncMock()
        conv_repo.get_by_id.return_value = conv

        with pytest.raises(BusinessError) as exc_info:
            await ConversationController.close(1, conv_repo)

        assert "já está encerrada" in exc_info.value.message
        conv_repo.close.assert_not_called()
