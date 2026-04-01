from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.rate_limiter import limiter
from app.db.database import get_session
from app.modules.chat.controller import ConversationController
from app.modules.chat.repository import (
    CompanyRepository,
    ConversationRepository,
    MessageRepository,
    UserRepository,
)
from app.modules.chat.schemas import CreateConversationRequest
from app.schemas.base_schema import SuccessResponse
from app.schemas.error_schema import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["conversations"])


@router.post(
    "/conversations",
    response_model=SuccessResponse,
    status_code=201,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "API key ausente (AUTH_001)",
        },
        403: {
            "model": ErrorResponse,
            "description": "API key inválida (AUTH_002)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Usuário ou empresa não encontrados (RES_001)",
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
async def create_conversation(
    request: Request,
    body: CreateConversationRequest,
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    user_repo = UserRepository(session)
    company_repo = CompanyRepository(session)
    return await ConversationController.create(
        body,
        conversation_repo=conversation_repo,
        user_repo=user_repo,
        company_repo=company_repo,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=SuccessResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "API key ausente (AUTH_001)",
        },
        403: {
            "model": ErrorResponse,
            "description": "API key inválida (AUTH_002)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Conversa não encontrada (RES_001)",
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
async def get_conversation(
    request: Request,
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    message_repo = MessageRepository(session)
    return await ConversationController.get_by_id(
        conversation_id,
        conversation_repo=conversation_repo,
        message_repo=message_repo,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "API key ausente (AUTH_001)",
        },
        403: {
            "model": ErrorResponse,
            "description": "API key inválida (AUTH_002)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Conversa não encontrada (RES_001)",
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
async def get_conversation_messages(
    request: Request,
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Quantidade de mensagens por página."),
    offset: int = Query(default=0, ge=0, description="Quantidade de mensagens a pular."),
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    message_repo = MessageRepository(session)
    return await ConversationController.get_messages(
        conversation_id,
        limit=limit,
        offset=offset,
        conversation_repo=conversation_repo,
        message_repo=message_repo,
    )


@router.patch(
    "/conversations/{conversation_id}/close",
    response_model=SuccessResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Conversa já encerrada (CHAT_001)",
        },
        401: {
            "model": ErrorResponse,
            "description": "API key ausente (AUTH_001)",
        },
        403: {
            "model": ErrorResponse,
            "description": "API key inválida (AUTH_002)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Conversa não encontrada (RES_001)",
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
async def close_conversation(
    request: Request,
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    return await ConversationController.close(
        conversation_id,
        conversation_repo=conversation_repo,
    )
