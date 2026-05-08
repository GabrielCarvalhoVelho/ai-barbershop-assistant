from app.core.exceptions import AuthorizationError
from app.models.enums import UserRole
from app.models.user import User


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def ensure_owner_or_admin(
    user: User,
    *,
    resource_owner_id: int,
    resource_company_id: int | None = None,
    error_message: str = "Sem permissão para acessar este recurso.",
) -> None:
    if is_admin(user):
        if resource_company_id is not None and user.company_id != resource_company_id:
            raise AuthorizationError(error_message)
        return
    if user.id != resource_owner_id:
        raise AuthorizationError(error_message)
