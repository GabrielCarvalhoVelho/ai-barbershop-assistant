import pytest

from app.core.exceptions import BusinessError
from app.services.chat_service import (
    _sanitize_message,
    _validate_business_rules,
    generate_response,
)


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
    def test_returns_echo(self):
        res = generate_response("Olá")
        assert res.response == "Você disse: Olá"

    def test_sanitizes_before_responding(self):
        res = generate_response("quero   agendar    corte")
        assert res.response == "Você disse: quero agendar corte"

    def test_has_timestamp(self):
        res = generate_response("teste")
        assert res.timestamp is not None

    def test_blocks_spam(self):
        with pytest.raises(BusinessError):
            generate_response("spam spam spam spam spam")
