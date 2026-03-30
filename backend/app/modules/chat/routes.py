from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.rate_limiter import limiter
from app.db.database import get_session
from app.modules.chat.controller import ChatController
from app.modules.chat.repository import MessageRepository
from app.modules.chat.schemas import ChatRequest
from app.schemas.base_schema import SuccessResponse
from app.schemas.error_schema import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post(
    "/chat",
    response_model=SuccessResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Erro de regra de negócio (CHAT_001)",
        },
        401: {
            "model": ErrorResponse,
            "description": "API key ausente (AUTH_001)",
        },
        403: {
            "model": ErrorResponse,
            "description": "API key inválida (AUTH_002)",
        },
        409: {
            "model": ErrorResponse,
            "description": "Conflito de dados — violação de constraint (DB_002)",
        },
        422: {
            "model": ErrorResponse,
            "description": "Erro de validação (VAL_001)",
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit excedido (RATE_001)",
        },
        500: {
            "model": ErrorResponse,
            "description": "Erro interno — banco de dados (DB_001) ou não tratado (APP_000)",
        },
        503: {
            "model": ErrorResponse,
            "description": "Serviço indisponível — banco fora do ar ou timeout (DB_003)",
        },
    },
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("10/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    repository = MessageRepository(session)
    return await ChatController.send_message(body, repository=repository)
