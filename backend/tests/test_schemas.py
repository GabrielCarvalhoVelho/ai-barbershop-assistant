import pytest
from pydantic import ValidationError

from app.schemas.base_schema import BaseResponse, ErrorDetail, SuccessResponse
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

    def test_single_char_accepted(self):
        req = ChatRequest(message="a")
        assert req.message == "a"

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


# ========================
# HealthResponse
# ========================

class TestHealthResponse:
    def test_default_status(self):
        res = HealthResponse()
        assert res.status == "ok"


# ========================
# BaseResponse
# ========================


class TestBaseResponse:
    def test_success_true(self):
        res = BaseResponse(success=True)
        assert res.success is True
        assert res.timestamp is not None

    def test_success_false(self):
        res = BaseResponse(success=False)
        assert res.success is False

    def test_timestamp_auto_generated(self):
        res1 = BaseResponse(success=True)
        res2 = BaseResponse(success=True)
        assert res1.timestamp <= res2.timestamp

    def test_success_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            BaseResponse()
        assert "success" in str(exc_info.value)


# ========================
# SuccessResponse
# ========================


class TestSuccessResponse:
    def test_creates_with_data_dict(self):
        res = SuccessResponse(data={"message": "API is running"})
        assert res.success is True
        assert res.data == {"message": "API is running"}
        assert res.timestamp is not None

    def test_creates_with_data_list(self):
        res = SuccessResponse(data=[{"id": 1}, {"id": 2}])
        assert res.data == [{"id": 1}, {"id": 2}]

    def test_creates_with_data_string(self):
        res = SuccessResponse(data="ok")
        assert res.data == "ok"

    def test_success_defaults_to_true(self):
        res = SuccessResponse(data={})
        assert res.success is True

    def test_data_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            SuccessResponse()
        assert "data" in str(exc_info.value)


# ========================
# ErrorDetail
# ========================


class TestErrorDetail:
    def test_code_and_message(self):
        detail = ErrorDetail(code="APP_000", message="Erro interno.")
        assert detail.code == "APP_000"
        assert detail.message == "Erro interno."
        assert detail.details is None

    def test_with_details(self):
        detail = ErrorDetail(
            code="VAL_001",
            message="Erro de validação.",
            details=["Campo obrigatório.", "Tamanho inválido."],
        )
        assert detail.code == "VAL_001"
        assert detail.message == "Erro de validação."
        assert len(detail.details) == 2

    def test_code_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            ErrorDetail(message="Erro")
        assert "code" in str(exc_info.value)

    def test_message_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            ErrorDetail(code="APP_000")
        assert "message" in str(exc_info.value)

    def test_exclude_none_hides_details(self):
        detail = ErrorDetail(code="APP_000", message="Erro")
        dumped = detail.model_dump(exclude_none=True)
        assert "details" not in dumped


# ========================
# ErrorResponse
# ========================


class TestErrorResponse:
    def test_creates_with_error_detail(self):
        res = ErrorResponse(
            error=ErrorDetail(code="APP_000", message="Internal Server Error")
        )
        assert res.success is False
        assert res.error.code == "APP_000"
        assert res.error.message == "Internal Server Error"
        assert res.error.details is None
        assert res.timestamp is not None

    def test_with_error_details(self):
        res = ErrorResponse(
            error=ErrorDetail(
                code="VAL_001",
                message="Erro de validação.",
                details=["Campo obrigatório.", "Tamanho inválido."],
            )
        )
        assert res.error.code == "VAL_001"
        assert res.error.message == "Erro de validação."
        assert len(res.error.details) == 2

    def test_success_defaults_to_false(self):
        res = ErrorResponse(
            error=ErrorDetail(code="APP_000", message="Erro")
        )
        assert res.success is False

    def test_exclude_none_hides_error_details(self):
        res = ErrorResponse(
            error=ErrorDetail(code="APP_000", message="Erro")
        )
        dumped = res.model_dump(exclude_none=True)
        assert "details" not in dumped["error"]
