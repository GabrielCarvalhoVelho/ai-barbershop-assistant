from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.logger import get_logger

logger = get_logger(__name__)

async def error_handler_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Erro na requisição: {str(e)}")

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error"
            }
        )