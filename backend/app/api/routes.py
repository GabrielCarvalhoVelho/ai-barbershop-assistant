from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.chat_controller import ChatController
from app.controllers.health_controller import HealthController
from app.core.auth import require_api_key
from app.core.rate_limiter import limiter
from app.db.database import get_session
from app.repositories.message_repository import MessageRepository
from app.schemas.base_schema import SuccessResponse
from app.schemas.chat_schema import ChatRequest
from app.schemas.error_schema import ErrorResponse

root_router = APIRouter()
router = APIRouter(prefix="/api/v1")


@root_router.get("/", response_model=SuccessResponse)
@limiter.exempt
async def read_root():
    return SuccessResponse(data={"message": "API is running"})


@router.get("/health", response_model=SuccessResponse)
@limiter.exempt
async def health_check():
    return HealthController.check()


@router.post(
    "/chat",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Erro de regra de negócio"},
        422: {"model": ErrorResponse, "description": "Erro de validação"},
        429: {"model": ErrorResponse, "description": "Rate limit excedido"},
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