import secrets

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError, InvalidTokenError
from app.models.enums import UserRole
from app.core.security import decode_access_token
from app.db.database import get_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


async def require_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> str:
    if not settings.api_key:
        return "no-auth"

    if not api_key:
        raise AuthenticationError(
            message="API key ausente. Envie o header X-API-Key.",
        )

    if not secrets.compare_digest(api_key, settings.api_key):
        raise AuthorizationError(
            message="API key inválida.",
        )

    return api_key


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise InvalidTokenError(message="Token ausente.")
    payload = decode_access_token(credentials.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise InvalidTokenError(message="Token inválido.")
    user = await UserRepository(session).get_by_id(int(user_id_str))
    if user is None or not user.is_active:
        raise InvalidTokenError(message="Usuário não encontrado ou inativo.")
    return user


def require_role(*roles: UserRole):
    """Factory que retorna uma dependency FastAPI que exige o(s) role(s) informado(s).

    Uso:
        @router.get("/admin/...")
        async def rota(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise AuthorizationError(message="Permissão insuficiente.")
        return current_user
    return _check_role
