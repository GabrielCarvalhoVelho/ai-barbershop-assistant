import pytest
from pydantic import ValidationError

from app.schemas.base_schema import BaseResponse, ErrorDetail, SuccessResponse
from app.schemas.error_schema import ErrorResponse


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
        assert detail.field is None
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

    def test_with_field(self):
        detail = ErrorDetail(
            code="VAL_001",
            message="Campo inválido.",
            field="message",
        )
        assert detail.field == "message"

    def test_with_field_and_details(self):
        detail = ErrorDetail(
            code="VAL_001",
            message="Erro de validação.",
            field="email",
            details=["Formato de email inválido."],
        )
        assert detail.field == "email"
        assert detail.details == ["Formato de email inválido."]

    def test_code_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            ErrorDetail(message="Erro")
        assert "code" in str(exc_info.value)

    def test_message_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            ErrorDetail(code="APP_000")
        assert "message" in str(exc_info.value)

    def test_exclude_none_hides_field_and_details(self):
        detail = ErrorDetail(code="APP_000", message="Erro")
        dumped = detail.model_dump(exclude_none=True)
        assert "field" not in dumped
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
