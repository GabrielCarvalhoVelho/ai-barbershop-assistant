from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.chat.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationMessagesResponse,
    ConversationResponse,
    ConversationSummaryResponse,
    MessageResponse,
    PaginationResponse,
)

IDS = {"user_id": 1, "company_id": 1}


# ========================
# ChatRequest - válidos
# ========================

class TestChatRequestValid:
    def test_normal_message(self):
        req = ChatRequest(message="Quero agendar um corte", **IDS)
        assert req.message == "Quero agendar um corte"

    def test_short_message(self):
        req = ChatRequest(message="oi", **IDS)
        assert req.message == "oi"

    def test_numbers_only(self):
        req = ChatRequest(message="123", **IDS)
        assert req.message == "123"

    def test_max_length_message(self):
        msg = "a" * 499 + "b"
        req = ChatRequest(message=msg, **IDS)
        assert len(req.message) == 500

    def test_strips_whitespace(self):
        req = ChatRequest(message="  olá  ", **IDS)
        assert req.message == "olá"

    def test_mixed_content(self):
        req = ChatRequest(message="Olá! Tudo bem? #123", **IDS)
        assert req.message == "Olá! Tudo bem? #123"

    def test_accented_characters(self):
        req = ChatRequest(message="Ação, coração, café", **IDS)
        assert req.message == "Ação, coração, café"

    def test_single_char_accepted(self):
        req = ChatRequest(message="a", **IDS)
        assert req.message == "a"

    def test_different_repeated_chars(self):
        req = ChatRequest(message="ababab", **IDS)
        assert req.message == "ababab"


# ========================
# ChatRequest - inválidos
# ========================

class TestChatRequestInvalid:
    def test_empty_string(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="", **IDS)
        assert "at least 1 character" in str(exc_info.value)

    def test_only_whitespace(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="     ", **IDS)
        assert "não pode estar vazia" in str(exc_info.value)

    def test_only_special_chars(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="!!!@#$%", **IDS)
        assert "pelo menos uma letra ou número" in str(exc_info.value)

    def test_only_punctuation(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="...", **IDS)
        assert "pelo menos uma letra ou número" in str(exc_info.value)

    def test_single_repeated_char(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="aaaaaaa", **IDS)
        assert "caracteres repetidos" in str(exc_info.value)

    def test_exceeds_max_length(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="a" * 501, **IDS)
        assert "at most 500 character" in str(exc_info.value)

    def test_missing_field(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest()
        assert "Field required" in str(exc_info.value)

    def test_wrong_type(self):
        with pytest.raises(ValidationError):
            ChatRequest(message=["not", "a", "string"], **IDS)


# ========================
# ChatRequest - user_id e company_id
# ========================

class TestChatRequestUserCompany:
    def test_accepts_valid_ids(self):
        req = ChatRequest(message="Oi", user_id=1, company_id=1)
        assert req.user_id == 1
        assert req.company_id == 1

    def test_rejects_zero_user_id(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Oi", user_id=0, company_id=1)

    def test_rejects_negative_company_id(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Oi", user_id=1, company_id=-1)

    def test_rejects_missing_user_id(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Oi", company_id=1)

    def test_rejects_missing_company_id(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Oi", user_id=1)

    def test_rejects_string_user_id(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Oi", user_id="abc", company_id=1)


# ========================
# ChatRequest - conversation_id
# ========================

class TestChatRequestConversationId:
    def test_defaults_to_none(self):
        req = ChatRequest(message="Olá", **IDS)
        assert req.conversation_id is None

    def test_accepts_valid_id(self):
        req = ChatRequest(message="Olá", **IDS, conversation_id=42)
        assert req.conversation_id == 42

    def test_accepts_explicit_none(self):
        req = ChatRequest(message="Olá", **IDS, conversation_id=None)
        assert req.conversation_id is None

    def test_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Olá", **IDS, conversation_id="abc")


# ========================
# ChatResponse
# ========================

class TestChatResponse:
    def test_creates_with_response(self):
        res = ChatResponse(response="Olá!", conversation_id=1)
        assert res.response == "Olá!"
        assert res.conversation_id == 1

    def test_rejects_missing_conversation_id(self):
        with pytest.raises(ValidationError):
            ChatResponse(response="Olá!")


# ========================
# MessageResponse
# ========================

NOW = datetime(2026, 3, 30, 14, 0, 0, tzinfo=timezone.utc)


class TestMessageResponse:
    def test_creates_with_all_fields(self):
        msg = MessageResponse(
            id=1, sender="user", content="Oi", created_at=NOW
        )
        assert msg.id == 1
        assert msg.sender == "user"
        assert msg.content == "Oi"
        assert msg.created_at == NOW

    def test_sender_accepts_bot(self):
        msg = MessageResponse(
            id=2, sender="bot", content="Olá!", created_at=NOW
        )
        assert msg.sender == "bot"

    def test_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            MessageResponse(id=1)


# ========================
# ConversationResponse
# ========================


class TestConversationSummaryResponse:
    def test_creates_active_conversation(self):
        conv = ConversationSummaryResponse(
            id=1, user_id=1, company_id=1, status="active", started_at=NOW
        )
        assert conv.id == 1
        assert conv.user_id == 1
        assert conv.company_id == 1
        assert conv.status == "active"
        assert conv.ended_at is None

    def test_creates_closed_conversation(self):
        ended = datetime(2026, 3, 30, 15, 0, 0, tzinfo=timezone.utc)
        conv = ConversationSummaryResponse(
            id=1, user_id=1, company_id=1, status="closed",
            started_at=NOW, ended_at=ended,
        )
        assert conv.status == "closed"
        assert conv.ended_at == ended

    def test_rejects_missing_user_id(self):
        with pytest.raises(ValidationError):
            ConversationSummaryResponse(id=1, company_id=1, status="active", started_at=NOW)


class TestConversationResponse:
    def test_creates_active_conversation(self):
        conv = ConversationResponse(
            id=1, user_id=1, company_id=1, status="active",
            started_at=NOW, message_count=3,
        )
        assert conv.id == 1
        assert conv.user_id == 1
        assert conv.company_id == 1
        assert conv.status == "active"
        assert conv.started_at == NOW
        assert conv.ended_at is None
        assert conv.message_count == 3

    def test_creates_closed_conversation(self):
        ended = datetime(2026, 3, 30, 15, 0, 0, tzinfo=timezone.utc)
        conv = ConversationResponse(
            id=1, user_id=2, company_id=3,
            status="closed", started_at=NOW, ended_at=ended, message_count=10,
        )
        assert conv.status == "closed"
        assert conv.ended_at == ended

    def test_ended_at_defaults_to_none(self):
        conv = ConversationResponse(
            id=1, user_id=1, company_id=1, status="active",
            started_at=NOW, message_count=0,
        )
        assert conv.ended_at is None

    def test_rejects_missing_message_count(self):
        with pytest.raises(ValidationError):
            ConversationResponse(
                id=1, user_id=1, company_id=1, status="active", started_at=NOW
            )


# ========================
# ConversationDetailResponse
# ========================


class TestConversationDetailResponse:
    def test_creates_with_empty_messages(self):
        conv = ConversationDetailResponse(
            id=1, status="active", started_at=NOW, messages=[]
        )
        assert conv.messages == []

    def test_creates_with_messages(self):
        msg = MessageResponse(
            id=1, sender="user", content="Oi", created_at=NOW
        )
        conv = ConversationDetailResponse(
            id=1, status="active", started_at=NOW, messages=[msg]
        )
        assert len(conv.messages) == 1
        assert conv.messages[0].content == "Oi"

    def test_ended_at_defaults_to_none(self):
        conv = ConversationDetailResponse(
            id=1, status="active", started_at=NOW, messages=[]
        )
        assert conv.ended_at is None

    def test_rejects_missing_messages(self):
        with pytest.raises(ValidationError):
            ConversationDetailResponse(id=1, status="active", started_at=NOW)


# ========================
# PaginationResponse
# ========================


class TestPaginationResponse:
    def test_creates_with_all_fields(self):
        p = PaginationResponse(limit=50, offset=0, total=100)
        assert p.limit == 50
        assert p.offset == 0
        assert p.total == 100

    def test_rejects_missing_total(self):
        with pytest.raises(ValidationError):
            PaginationResponse(limit=50, offset=0)


# ========================
# ConversationMessagesResponse
# ========================


class TestConversationMessagesResponse:
    def test_creates_with_empty_messages(self):
        p = PaginationResponse(limit=50, offset=0, total=0)
        resp = ConversationMessagesResponse(
            conversation_id=1, messages=[], pagination=p
        )
        assert resp.conversation_id == 1
        assert resp.messages == []
        assert resp.pagination.total == 0

    def test_creates_with_messages(self):
        msg = MessageResponse(id=1, sender="user", content="Oi", created_at=NOW)
        p = PaginationResponse(limit=50, offset=0, total=1)
        resp = ConversationMessagesResponse(
            conversation_id=1, messages=[msg], pagination=p
        )
        assert len(resp.messages) == 1
        assert resp.messages[0].content == "Oi"

    def test_rejects_missing_pagination(self):
        with pytest.raises(ValidationError):
            ConversationMessagesResponse(conversation_id=1, messages=[])
