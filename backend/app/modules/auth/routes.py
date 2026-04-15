from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.modules.auth.controller import AuthController
from app.modules.auth.schemas import LoginRequest
from app.repositories.user_repository import UserRepository
from app.schemas.base_schema import SuccessResponse
from app.schemas.error_schema import ErrorResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=SuccessResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Credenciais inválidas (AUTH_001)"},
        422: {"model": ErrorResponse, "description": "Dados inválidos (VAL_001)"},
    },
)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)):
    user_repo = UserRepository(session)
    return await AuthController.login(request, user_repo)


@router.get(
    "/me",
    response_model=SuccessResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Token ausente ou inválido (AUTH_003)"},
    },
)
async def me(current_user: User = Depends(get_current_user)):
    return await AuthController.me(current_user)
