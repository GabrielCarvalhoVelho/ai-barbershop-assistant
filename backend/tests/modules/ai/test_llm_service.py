from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AIServiceError
from app.models.enums import MessageSender
from app.modules.ai.llm_service import _build_history_messages, generate_ai_response

MOCK_TARGET = "app.modules.ai.llm_service.ChatGroq"
FAKE_SYSTEM_PROMPT = "Você é um assistente de teste."


def _make_message(sender: MessageSender, content: str):
    msg = MagicMock()
    msg.sender = sender
    msg.content = content
    return msg


# ========================
# Formatação do histórico
# ========================


class TestBuildHistoryMessages:
    def test_empty_history_returns_empty_list(self):
        result = _build_history_messages([])
        assert result == []

    def test_user_message_becomes_human_message(self):
        from langchain_core.messages import HumanMessage

        history = [_make_message(MessageSender.USER, "Quero agendar")]
        result = _build_history_messages(history)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Quero agendar"

    def test_bot_message_becomes_ai_message(self):
        from langchain_core.messages import AIMessage

        history = [_make_message(MessageSender.BOT, "Claro! Qual serviço?")]
        result = _build_history_messages(history)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "Claro! Qual serviço?"

    def test_alternating_messages_preserve_order(self):
        from langchain_core.messages import AIMessage, HumanMessage

        history = [
            _make_message(MessageSender.USER, "Oi"),
            _make_message(MessageSender.BOT, "Olá!"),
            _make_message(MessageSender.USER, "Quero cortar"),
        ]
        result = _build_history_messages(history)

        assert len(result) == 3
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)
        assert isinstance(result[2], HumanMessage)


# ========================
# generate_ai_response
# ========================


class TestGenerateAiResponse:
    @pytest.mark.asyncio
    async def test_returns_llm_response(self):
        mock_response = MagicMock()
        mock_response.content = "Posso agendar para amanhã!"

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        with patch(MOCK_TARGET, return_value=mock_llm):
            result = await generate_ai_response("Quero agendar", [], FAKE_SYSTEM_PROMPT)

        assert result == "Posso agendar para amanhã!"

    @pytest.mark.asyncio
    async def test_uses_provided_system_prompt(self):
        from langchain_core.messages import SystemMessage

        mock_response = MagicMock()
        mock_response.content = "Ok!"
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        with patch(MOCK_TARGET, return_value=mock_llm):
            await generate_ai_response("Oi", [], FAKE_SYSTEM_PROMPT)

        call_args = mock_llm.ainvoke.call_args[0][0]
        assert isinstance(call_args[0], SystemMessage)
        assert call_args[0].content == FAKE_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_includes_history_in_messages(self):
        from langchain_core.messages import HumanMessage

        mock_response = MagicMock()
        mock_response.content = "Ok!"
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        history = [_make_message(MessageSender.USER, "Mensagem anterior")]

        with patch(MOCK_TARGET, return_value=mock_llm):
            await generate_ai_response("Nova mensagem", history, FAKE_SYSTEM_PROMPT)

        call_args = mock_llm.ainvoke.call_args[0][0]
        # system + 1 history + current = 3 messages
        assert len(call_args) == 3
        assert isinstance(call_args[1], HumanMessage)
        assert call_args[1].content == "Mensagem anterior"

    @pytest.mark.asyncio
    async def test_current_message_is_last(self):
        from langchain_core.messages import HumanMessage

        mock_response = MagicMock()
        mock_response.content = "Ok!"
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response

        with patch(MOCK_TARGET, return_value=mock_llm):
            await generate_ai_response("Mensagem atual", [], FAKE_SYSTEM_PROMPT)

        call_args = mock_llm.ainvoke.call_args[0][0]
        assert isinstance(call_args[-1], HumanMessage)
        assert call_args[-1].content == "Mensagem atual"

    @pytest.mark.asyncio
    async def test_raises_ai_service_error_on_exception(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("Groq timeout")

        with patch(MOCK_TARGET, return_value=mock_llm):
            with pytest.raises(AIServiceError) as exc_info:
                await generate_ai_response("Oi", [], FAKE_SYSTEM_PROMPT)

        assert "indisponível" in exc_info.value.message
        assert exc_info.value.code == "AI_001"
        assert exc_info.value.status_code == 503
