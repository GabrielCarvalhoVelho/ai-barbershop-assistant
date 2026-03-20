from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.exceptions import BusinessError
from app.core.logger import get_logger
from app.schemas.error_schema import ErrorResponse

logger = get_logger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = []
    for error in exc.errors():
        msg = error.get("msg", "")
        if msg.startswith("Value error, "):
            msg = msg.removeprefix("Value error, ")
        details.append(msg)

    logger.warning("Validação falhou: %s", details)

    error_response = ErrorResponse(
        error="Erro de validação na mensagem.",
        details=details,
    )
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(exclude_none=True),
    )


async def business_exception_handler(
    request: Request, exc: BusinessError
) -> JSONResponse:
    logger.warning("Erro de negócio: %s", exc.message)

    error_response = ErrorResponse(error=exc.message)
    return JSONResponse(
        status_code=400,
        content=error_response.model_dump(exclude_none=True),
    )


async def error_handler_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error("Erro na requisição: %s", e)

        error = ErrorResponse(error="Internal Server Error")
        return JSONResponse(
            status_code=500,
            content=error.model_dump(exclude_none=True),
        )