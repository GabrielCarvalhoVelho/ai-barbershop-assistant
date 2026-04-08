from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import BusinessError
from app.modules.ai.prompts import BusinessInfo
from app.modules.chat.service import (
    _sanitize_message,
    _validate_business_rules,
    generate_response,
)

MOCK_AI_RESPONSE = "Olá! Como posso ajudar?"
MOCK_TARGET = "app.modules.chat.service.generate_ai_response"
FAKE_BUSINESS = BusinessInfo(name="Barbearia Teste")


# ========================
# Sanitização
# ========================

class TestSanitizeMessage:
    def test_collapses_internal_spaces(self):
        assert _sanitize_message("quero   agendar    corte") == "quero agendar corte"

    def test_strips_edges(self):
        assert _sanitize_message("  olá  ") == "olá"

    def test_normalizes_tabs_and_newlines(self):
        assert _sanitize_message("olá\t\nmundo") == "olá mundo"

    def test_already_clean(self):
        assert _sanitize_message("mensagem limpa") == "mensagem limpa"


# ========================
# Regras de negócio
# ========================

class TestBusinessRules:
    def test_valid_message_passes(self):
        _validate_business_rules("Quero agendar um corte para sábado")

    def test_short_repetition_passes(self):
        _validate_business_rules("oi oi oi")

    def test_nine_repeated_chars_passes(self):
        _validate_business_rules("aaaaaaaaa é muito")  # 9 'a' - abaixo do limite

    def test_ten_repeated_chars_blocked(self):
        with pytest.raises(BusinessError) as exc_info:
            _validate_business_rules("olha isso aaaaaaaaaa que legal")
        assert "repetitivo" in exc_info.value.message

    def test_word_repeated_four_times_passes(self):
        _validate_business_rules("corte corte corte corte")  # 4x - abaixo do limite

    def test_word_repeated_five_times_blocked(self):
        with pytest.raises(BusinessError) as exc_info:
            _validate_business_rules("spam spam spam spam spam")
        assert "repetitivo" in exc_info.value.message

    def test_repeated_word_case_insensitive(self):
        with pytest.raises(BusinessError):
            _validate_business_rules("Spam SPAM spam SpAm sPaM")


# ========================
# generate_response
# ========================

class TestGenerateResponse:
    @pytest.mark.asyncio
    async def test_returns_string(self):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)):
            res = await generate_response("Olá", [], FAKE_BUSINESS)
        assert isinstance(res, str)

    @pytest.mark.asyncio
    async def test_calls_llm_with_sanitized_message(self):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await generate_response("quero   agendar    corte", [], FAKE_BUSINESS)
        args = mock_llm.call_args
        assert args[0][0] == "quero agendar corte"

    @pytest.mark.asyncio
    async def test_passes_history_to_llm(self):
        history = [object(), object()]
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await generate_response("Olá", history, FAKE_BUSINESS)
        args = mock_llm.call_args
        assert args[0][1] is history

    @pytest.mark.asyncio
    async def test_passes_system_prompt_to_llm(self):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await generate_response("Olá", [], FAKE_BUSINESS)
        system_prompt = mock_llm.call_args[0][2]
        assert "Barbearia Teste" in system_prompt

    @pytest.mark.asyncio
    async def test_blocks_spam(self):
        with pytest.raises(BusinessError):
            await generate_response("spam spam spam spam spam", [], FAKE_BUSINESS)


# ========================
# Propagação de context (RAG)
# ========================

class TestGenerateResponseContext:
    @pytest.mark.asyncio
    async def test_default_context_omits_section(self):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await generate_response("Olá", [], FAKE_BUSINESS)
        system_prompt = mock_llm.call_args[0][2]
        assert "Use as informações abaixo" not in system_prompt

    @pytest.mark.asyncio
    async def test_context_included_in_system_prompt(self):
        context = "Corte masculino: R$ 40,00"
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await generate_response("Olá", [], FAKE_BUSINESS, context=context)
        system_prompt = mock_llm.call_args[0][2]
        assert "Use as informações abaixo" in system_prompt
        assert "Corte masculino: R$ 40,00" in system_prompt

    @pytest.mark.asyncio
    async def test_empty_context_omits_section(self):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=MOCK_AI_RESPONSE)) as mock_llm:
            await generate_response("Olá", [], FAKE_BUSINESS, context="")
        system_prompt = mock_llm.call_args[0][2]
        assert "Use as informações abaixo" not in system_prompt
