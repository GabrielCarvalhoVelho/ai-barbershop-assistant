from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.rate_limiter import limiter
from app.db.database import get_session
from app.models.user import User
from app.modules.auth.controller import AuthController
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.repositories.user_repository import UserRepository
from app.schemas.base_schema import SuccessResponse
from app.schemas.error_schema import ErrorResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=SuccessResponse,
    summary="Autenticar usuário",
    description="Autentica com telefone e senha. Retorna JWT Bearer token.",
    responses={
        401: {"model": ErrorResponse, "description": "Credenciais inválidas (AUTH_001)"},
        422: {"model": ErrorResponse, "description": "Dados inválidos (VAL_001)"},
        429: {"model": ErrorResponse, "description": "Rate limit excedido (RATE_001)"},
    },
)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, session: AsyncSession = Depends(get_session)):
    user_repo = UserRepository(session)
    return await AuthController.login(body, user_repo)


@router.post(
    "/register",
    response_model=SuccessResponse,
    status_code=201,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Phone ou email já cadastrado (AUTH_004)",
        },
        409: {
            "model": ErrorResponse,
            "description": "Conflito de constraint no banco (DB_002)",
        },
        422: {
            "model": ErrorResponse,
            "description": "Dados inválidos — campo obrigatório faltando ou fora do tamanho (VAL_001)",
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit excedido (RATE_001)",
        },
        500: {
            "model": ErrorResponse,
            "description": "Erro interno (DB_001 ou APP_000)",
        },
        503: {
            "model": ErrorResponse,
            "description": "Banco indisponível (DB_003)",
        },
    },
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    user_repo = UserRepository(session)
    return await AuthController.register(body, user_repo)


@router.get(
    "/me",
    response_model=SuccessResponse,
    openapi_extra={"security": [{"bearerAuth": []}]},
    responses={
        401: {"model": ErrorResponse, "description": "Token ausente ou inválido (AUTH_003)"},
    },
)
async def me(current_user: User = Depends(get_current_user)):
    return await AuthController.me(current_user)
