import pytest

from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)


# ========================
# AppError (base)
# ========================

class TestAppError:
    def test_default_attributes(self):
        err = AppError(message="algo deu errado")
        assert err.message == "algo deu errado"
        assert err.code == "APP_000"
        assert err.status_code == 500
        assert err.details is None
        assert str(err) == "algo deu errado"

    def test_custom_code_override(self):
        err = AppError(message="erro", code="CUSTOM_001")
        assert err.code == "CUSTOM_001"

    def test_with_details(self):
        err = AppError(message="erro", details=["detalhe 1", "detalhe 2"])
        assert err.details == ["detalhe 1", "detalhe 2"]

    def test_is_exception(self):
        err = AppError(message="erro")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(AppError) as exc_info:
            raise AppError(message="teste")
        assert exc_info.value.message == "teste"


# ========================
# Hierarquia — herança
# ========================

class TestExceptionHierarchy:
    """Todas as exceções customizadas devem herdar de AppError."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            AuthenticationError,
            AuthorizationError,
            BusinessError,
            ValidationError,
            NotFoundError,
            ConflictError,
            DatabaseError,
            ServiceUnavailableError,
            RateLimitError,
        ],
    )
    def test_inherits_from_app_error(self, exc_class):
        assert issubclass(exc_class, AppError)

    @pytest.mark.parametrize(
        "exc_class",
        [
            AuthenticationError,
            AuthorizationError,
            BusinessError,
            ValidationError,
            NotFoundError,
            ConflictError,
            DatabaseError,
            ServiceUnavailableError,
            RateLimitError,
        ],
    )
    def test_can_be_caught_as_app_error(self, exc_class):
        with pytest.raises(AppError):
            raise exc_class(message="teste")


# ========================
# Status codes
# ========================

class TestStatusCodes:
    @pytest.mark.parametrize(
        "exc_class, expected_status",
        [
            (AppError, 500),
            (AuthenticationError, 401),
            (AuthorizationError, 403),
            (BusinessError, 400),
            (ValidationError, 422),
            (NotFoundError, 404),
            (ConflictError, 409),
            (DatabaseError, 500),
            (ServiceUnavailableError, 503),
            (RateLimitError, 429),
        ],
    )
    def test_status_code(self, exc_class, expected_status):
        err = exc_class(message="teste")
        assert err.status_code == expected_status


# ========================
# Error codes
# ========================

class TestErrorCodes:
    @pytest.mark.parametrize(
        "exc_class, expected_code",
        [
            (AppError, "APP_000"),
            (AuthenticationError, "AUTH_001"),
            (AuthorizationError, "AUTH_002"),
            (BusinessError, "CHAT_001"),
            (ValidationError, "VAL_001"),
            (NotFoundError, "RES_001"),
            (ConflictError, "DB_002"),
            (DatabaseError, "DB_001"),
            (ServiceUnavailableError, "DB_003"),
            (RateLimitError, "RATE_001"),
        ],
    )
    def test_default_error_code(self, exc_class, expected_code):
        err = exc_class(message="teste")
        assert err.code == expected_code

    def test_code_can_be_overridden(self):
        err = BusinessError(message="teste", code="CHAT_999")
        assert err.code == "CHAT_999"

    def test_override_does_not_affect_class_default(self):
        BusinessError(message="override", code="CHAT_999")
        err2 = BusinessError(message="default")
        assert err2.code == "CHAT_001"


# ========================
# Atributos — message e details
# ========================

class TestAttributes:
    def test_message_propagated(self):
        err = NotFoundError(message="Conversa não encontrada")
        assert err.message == "Conversa não encontrada"
        assert str(err) == "Conversa não encontrada"

    def test_details_default_none(self):
        err = DatabaseError(message="erro de conexão")
        assert err.details is None

    def test_details_propagated(self):
        details = ["campo 'email' duplicado", "constraint: uq_user_email"]
        err = ConflictError(message="Conflito de dados", details=details)
        assert err.details == details

    def test_all_attributes_together(self):
        err = AuthenticationError(
            message="Token expirado",
            code="AUTH_003",
            details=["Faça login novamente"],
        )
        assert err.message == "Token expirado"
        assert err.code == "AUTH_003"
        assert err.status_code == 401
        assert err.details == ["Faça login novamente"]
