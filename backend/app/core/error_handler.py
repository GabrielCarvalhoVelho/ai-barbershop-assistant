from fastapi import Request
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.core.context import get_request_id
from app.core.exceptions import AppError
from app.core.logger import get_logger
from app.schemas.base_schema import ErrorDetail
from app.schemas.error_schema import ErrorResponse

logger = get_logger(__name__)


def _build_error_response(
    code: str,
    message: str,
    details: list[str] | None = None,
    field: str | None = None,
) -> ErrorResponse:
    return ErrorResponse(
        request_id=get_request_id(),
        error=ErrorDetail(
            code=code,
            message=message,
            field=field,
            details=details,
        ),
    )


def _json_response(status_code: int, error_response: ErrorResponse) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


# --- Handlers de exceções da aplicação ---


async def app_exception_handler(
    request: Request, exc: AppError
) -> JSONResponse:
    """Handler unificado para todas as exceções que herdam de AppError."""
    logger.warning(
        "[%s] %s — %s", exc.code, exc.__class__.__name__, exc.message
    )
    return _json_response(
        exc.status_code,
        _build_error_response(code=exc.code, message=exc.message, details=exc.details),
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handler para HTTPException do FastAPI/Starlette (404, 405, etc.)."""
    logger.warning(
        "[HTTP_%s] HTTPException — %s", exc.status_code, exc.detail
    )
    return _json_response(
        exc.status_code,
        _build_error_response(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        ),
    )


# --- Handlers de validação e rate limit ---


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação do Pydantic (RequestValidationError)."""
    details = []
    field_name = None

    for error in exc.errors():
        msg = error.get("msg", "")
        if msg.startswith("Value error, "):
            msg = msg.removeprefix("Value error, ")

        loc = error.get("loc", ())
        if loc:
            field_name = field_name or str(loc[-1])
            msg = f"{loc[-1]}: {msg}"

        details.append(msg)

    logger.warning("[VAL_001] Validação falhou: %s", details)
    return _json_response(
        422,
        _build_error_response(
            code="VAL_001",
            message="Erro de validação na mensagem.",
            details=details,
            field=field_name,
        ),
    )


async def rate_limit_exception_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handler para rate limit do slowapi (exceção de terceiro, não herda AppError)."""
    logger.warning("[RATE_001] Rate limit excedido: %s", exc.detail)
    return _json_response(
        429,
        _build_error_response(
            code="RATE_001",
            message="Limite de requisições excedido. Tente novamente mais tarde.",
        ),
    )


# --- Handlers de banco de dados (SQLAlchemy) ---


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Handler para violações de constraint (FK, UNIQUE, NOT NULL) → 409."""
    logger.warning(
        "[DB_002] IntegrityError — %s", exc.orig,
    )
    return _json_response(
        409,
        _build_error_response(
            code="DB_002",
            message="Conflito de dados. Verifique os valores enviados.",
        ),
    )


async def operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    """Handler para banco indisponível, timeout, connection refused → 503."""
    logger.error(
        "[DB_003] OperationalError — %s", exc.orig,
        exc_info=True,
    )
    return _json_response(
        503,
        _build_error_response(
            code="DB_003",
            message="Serviço temporariamente indisponível. Tente novamente mais tarde.",
        ),
    )


async def sqlalchemy_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handler genérico para erros de SQLAlchemy não capturados acima → 500."""
    logger.error(
        "[DB_001] SQLAlchemyError — %s: %s",
        type(exc).__name__,
        exc,
        exc_info=True,
    )
    return _json_response(
        500,
        _build_error_response(
            code="DB_001",
            message="Erro interno no banco de dados.",
        ),
    )


# --- Middleware catch-all ---


async def error_handler_middleware(request: Request, call_next):
    """Middleware catch-all para exceções não tratadas pelos handlers acima."""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(
            "[APP_000] Erro não tratado: %s — %s",
            type(e).__name__,
            e,
            exc_info=True,
        )
        return _json_response(
            500,
            _build_error_response(code="APP_000", message="Internal Server Error"),
        )
