import pytest
from pydantic import ValidationError

from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.schemas.error_schema import ErrorResponse
from app.schemas.health_schema import HealthResponse


# ========================
# ChatRequest - válidos
# ========================

class TestChatRequestValid:
    def test_normal_message(self):
        req = ChatRequest(message="Quero agendar um corte")
        assert req.message == "Quero agendar um corte"

    def test_short_message(self):
        req = ChatRequest(message="oi")
        assert req.message == "oi"

    def test_numbers_only(self):
        req = ChatRequest(message="123")
        assert req.message == "123"

    def test_max_length_message(self):
        msg = "a" * 499 + "b"
        req = ChatRequest(message=msg)
        assert len(req.message) == 500

    def test_strips_whitespace(self):
        req = ChatRequest(message="  olá  ")
        assert req.message == "olá"

    def test_mixed_content(self):
        req = ChatRequest(message="Olá! Tudo bem? #123")
        assert req.message == "Olá! Tudo bem? #123"

    def test_accented_characters(self):
        req = ChatRequest(message="Ação, coração, café")
        assert req.message == "Ação, coração, café"

    def test_different_repeated_chars(self):
        req = ChatRequest(message="ababab")
        assert req.message == "ababab"


# ========================
# ChatRequest - inválidos
# ========================

class TestChatRequestInvalid:
    def test_empty_string(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        assert "at least 1 character" in str(exc_info.value)

    def test_only_whitespace(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="     ")
        assert "não pode estar vazia" in str(exc_info.value)

    def test_only_special_chars(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="!!!@#$%")
        assert "pelo menos uma letra ou número" in str(exc_info.value)

    def test_only_punctuation(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="...")
        assert "pelo menos uma letra ou número" in str(exc_info.value)

    def test_single_repeated_char(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="aaaaaaa")
        assert "caracteres repetidos" in str(exc_info.value)

    def test_exceeds_max_length(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="a" * 501)
        assert "at most 500 character" in str(exc_info.value)

    def test_missing_field(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest()
        assert "Field required" in str(exc_info.value)

    def test_wrong_type(self):
        with pytest.raises(ValidationError):
            ChatRequest(message=["not", "a", "string"])


# ========================
# ChatResponse
# ========================

class TestChatResponse:
    def test_creates_with_response(self):
        res = ChatResponse(response="Olá!")
        assert res.response == "Olá!"
        assert res.timestamp is not None

    def test_timestamp_auto_generated(self):
        res1 = ChatResponse(response="a")
        res2 = ChatResponse(response="b")
        assert res1.timestamp <= res2.timestamp


# ========================
# HealthResponse
# ========================

class TestHealthResponse:
    def test_default_status(self):
        res = HealthResponse()
        assert res.status == "ok"


# ========================
# ErrorResponse
# ========================

class TestErrorResponse:
    def test_error_only(self):
        res = ErrorResponse(error="Internal Server Error")
        assert res.error == "Internal Server Error"
        assert res.details is None

    def test_with_details(self):
        res = ErrorResponse(
            error="Erro de validação.",
            details=["Campo obrigatório.", "Tamanho inválido."],
        )
        assert res.error == "Erro de validação."
        assert len(res.details) == 2

    def test_exclude_none(self):
        res = ErrorResponse(error="Erro")
        dumped = res.model_dump(exclude_none=True)
        assert "details" not in dumped
