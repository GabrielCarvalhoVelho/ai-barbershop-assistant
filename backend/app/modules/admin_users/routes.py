from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_role
from app.db.database import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.modules.admin_users.controller import AdminUsersController
from app.modules.admin_users.schemas import (
    UpdateUserActiveRequest,
    UpdateUserRoleRequest,
)
from app.repositories.user_repository import UserRepository
from app.schemas.base_schema import SuccessResponse
from app.schemas.error_schema import ErrorResponse

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin - users"])

_SECURITY = {"security": [{"bearerAuth": []}]}
_401 = {"model": ErrorResponse, "description": "Token ausente ou inválido (AUTH_003)"}
_403 = {"model": ErrorResponse, "description": "Acesso negado — requer role ADMIN (AUTH_002)"}
_404 = {"model": ErrorResponse, "description": "Usuário não encontrado (RES_001)"}
_400 = {"model": ErrorResponse, "description": "Regra de gestão violada (USR_001)"}


@router.get(
    "/",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={401: _401, 403: _403},
)
async def list_users(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    role: UserRole | None = Query(default=None),
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    return await AdminUsersController.list_users(
        admin, repo, limit=limit, offset=offset, role=role
    )


@router.patch(
    "/{user_id}/role",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={400: _400, 401: _401, 403: _403, 404: _404},
)
async def update_role(
    user_id: int,
    body: UpdateUserRoleRequest,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    return await AdminUsersController.update_role(admin, user_id, body, repo)


@router.patch(
    "/{user_id}/active",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={400: _400, 401: _401, 403: _403, 404: _404},
)
async def update_active(
    user_id: int,
    body: UpdateUserActiveRequest,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    return await AdminUsersController.update_active(admin, user_id, body, repo)
