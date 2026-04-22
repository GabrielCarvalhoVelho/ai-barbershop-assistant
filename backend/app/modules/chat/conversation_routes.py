from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.rate_limiter import limiter
from app.db.database import get_session
from app.models.user import User
from app.modules.chat.controller import ConversationController
from app.modules.chat.repository import ConversationRepository, MessageRepository
from app.repositories import CompanyRepository
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
            "description": "Token ausente ou inválido (AUTH_003)",
        },
        403: {
            "model": ErrorResponse,
            "description": "Sem permissão (AUTH_002)",
        },
        404: {
            "model": ErrorResponse,
            "description": "Usuário não encontrado ou empresa não encontrada (RES_001)",
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
)
@limiter.limit("10/minute")
async def create_conversation(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    company_repo = CompanyRepository(session)
    return await ConversationController.create(
        current_user=current_user,
        conversation_repo=conversation_repo,
        company_repo=company_repo,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=SuccessResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Token ausente ou inválido (AUTH_003)",
        },
        403: {
            "model": ErrorResponse,
            "description": "Sem permissão ou conversa de outro usuário (AUTH_002)",
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
)
@limiter.limit("10/minute")
async def get_conversation(
    request: Request,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    message_repo = MessageRepository(session)
    return await ConversationController.get_by_id(
        conversation_id,
        current_user=current_user,
        conversation_repo=conversation_repo,
        message_repo=message_repo,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Token ausente ou inválido (AUTH_003)",
        },
        403: {
            "model": ErrorResponse,
            "description": "Sem permissão ou conversa de outro usuário (AUTH_002)",
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
)
@limiter.limit("10/minute")
async def get_conversation_messages(
    request: Request,
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Quantidade de mensagens por página."),
    offset: int = Query(default=0, ge=0, description="Quantidade de mensagens a pular."),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    message_repo = MessageRepository(session)
    return await ConversationController.get_messages(
        conversation_id,
        current_user=current_user,
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
            "description": "Token ausente ou inválido (AUTH_003)",
        },
        403: {
            "model": ErrorResponse,
            "description": "Sem permissão ou conversa de outro usuário (AUTH_002)",
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
)
@limiter.limit("10/minute")
async def close_conversation(
    request: Request,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation_repo = ConversationRepository(session)
    return await ConversationController.close(
        conversation_id,
        current_user=current_user,
        conversation_repo=conversation_repo,
    )
