from app.models.enums import UserRole
from app.models.user import User
from app.modules.admin_users import service
from app.modules.admin_users.schemas import (
    UpdateUserActiveRequest,
    UpdateUserRoleRequest,
    UserListItemResponse,
    UserListResponse,
)
from app.modules.chat.schemas import PaginationResponse
from app.repositories.user_repository import UserRepository
from app.schemas.base_schema import SuccessResponse


class AdminUsersController:
    @staticmethod
    async def list_users(
        admin: User,
        repo: UserRepository,
        *,
        limit: int,
        offset: int,
        role: UserRole | None,
    ) -> SuccessResponse:
        users, total = await service.list_users(
            admin, repo, limit=limit, offset=offset, role=role
        )
        data = UserListResponse(
            users=[UserListItemResponse.model_validate(u) for u in users],
            pagination=PaginationResponse(limit=limit, offset=offset, total=total),
        )
        return SuccessResponse(data=data.model_dump())

    @staticmethod
    async def update_role(
        admin: User,
        target_id: int,
        body: UpdateUserRoleRequest,
        repo: UserRepository,
    ) -> SuccessResponse:
        user = await service.update_role(admin, target_id, body.role, repo)
        return SuccessResponse(data=UserListItemResponse.model_validate(user).model_dump())

    @staticmethod
    async def update_active(
        admin: User,
        target_id: int,
        body: UpdateUserActiveRequest,
        repo: UserRepository,
    ) -> SuccessResponse:
        user = await service.update_active(admin, target_id, body.is_active, repo)
        return SuccessResponse(data=UserListItemResponse.model_validate(user).model_dump())
