from app.core.exceptions import AuthenticationError
from app.core.security import verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository

_INVALID_CREDENTIALS = "Credenciais inválidas."


async def authenticate_user(phone: str, password: str, user_repo: UserRepository) -> User:
    user = await user_repo.get_by_phone(phone)
    if user is None or not user.is_active:
        raise AuthenticationError(message=_INVALID_CREDENTIALS)
    if not verify_password(password, user.password_hash):
        raise AuthenticationError(message=_INVALID_CREDENTIALS)
    return user
