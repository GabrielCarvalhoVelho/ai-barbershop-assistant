from app.core.exceptions import NotFoundError, UserManagementError
from app.core.logger import get_logger
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


async def list_users(
    admin: User,
    repo: UserRepository,
    *,
    limit: int,
    offset: int,
    role: UserRole | None,
) -> tuple[list[User], int]:
    return await repo.list_by_company(
        company_id=admin.company_id,
        limit=limit,
        offset=offset,
        role=role,
    )


async def _get_target_in_same_company(
    admin: User, target_id: int, repo: UserRepository
) -> User:
    target = await repo.get_by_id(target_id)
    if target is None or target.company_id != admin.company_id:
        raise NotFoundError(message="Usuário não encontrado.")
    return target


async def update_role(
    admin: User,
    target_id: int,
    new_role: UserRole,
    repo: UserRepository,
) -> User:
    target = await _get_target_in_same_company(admin, target_id, repo)

    if target.id == admin.id and new_role != UserRole.ADMIN:
        raise UserManagementError(
            message="Você não pode rebaixar a si mesmo."
        )

    if (
        target.role == UserRole.ADMIN
        and new_role != UserRole.ADMIN
        and target.is_active
    ):
        active_admins = await repo.count_active_admins(admin.company_id)
        if active_admins <= 1:
            raise UserManagementError(
                message="Não é possível rebaixar o último admin ativo da empresa."
            )

    if target.role == new_role:
        return target

    updated = await repo.update_role(target_id, new_role)
    logger.info(
        "Role atualizado: admin_id=%s target_id=%s old=%s new=%s",
        admin.id,
        target_id,
        target.role.value,
        new_role.value,
    )
    return updated


async def update_active(
    admin: User,
    target_id: int,
    is_active: bool,
    repo: UserRepository,
) -> User:
    target = await _get_target_in_same_company(admin, target_id, repo)

    if target.id == admin.id and not is_active:
        raise UserManagementError(
            message="Você não pode desativar a si mesmo."
        )

    if (
        target.role == UserRole.ADMIN
        and target.is_active
        and not is_active
    ):
        active_admins = await repo.count_active_admins(admin.company_id)
        if active_admins <= 1:
            raise UserManagementError(
                message="Não é possível desativar o último admin ativo da empresa."
            )

    if target.is_active == is_active:
        return target

    updated = await repo.update_active(target_id, is_active)
    logger.info(
        "Status atualizado: admin_id=%s target_id=%s is_active=%s",
        admin.id,
        target_id,
        is_active,
    )
    return updated
