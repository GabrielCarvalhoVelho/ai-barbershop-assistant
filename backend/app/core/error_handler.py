from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.exceptions import AppError
from app.core.logger import get_logger
from app.schemas.base_schema import ErrorDetail
from app.schemas.error_schema import ErrorResponse

logger = get_logger(__name__)


async def app_exception_handler(
    request: Request, exc: AppError
) -> JSONResponse:
    """Handler unificado para todas as exceções que herdam de AppError."""
    logger.warning(
        "[%s] %s — %s", exc.code, exc.__class__.__name__, exc.message
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação do Pydantic (RequestValidationError)."""
    details = []
    for error in exc.errors():
        msg = error.get("msg", "")
        if msg.startswith("Value error, "):
            msg = msg.removeprefix("Value error, ")
        details.append(msg)

    logger.warning("[VAL_001] Validação falhou: %s", details)

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="VAL_001",
            message="Erro de validação na mensagem.",
            details=details,
        )
    )
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


async def rate_limit_exception_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handler para rate limit do slowapi (exceção de terceiro, não herda AppError)."""
    logger.warning("[RATE_001] Rate limit excedido: %s", exc.detail)

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="RATE_001",
            message="Limite de requisições excedido. Tente novamente mais tarde.",
        )
    )
    return JSONResponse(
        status_code=429,
        content=error_response.model_dump(mode="json", exclude_none=True),
    )


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

        error_response = ErrorResponse(
            error=ErrorDetail(
                code="APP_000",
                message="Internal Server Error",
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(mode="json", exclude_none=True),
        )
