from app.core.exceptions import AuthenticationError, RegistrationError
from app.core.security import hash_password, verify_password
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


async def register_user(
    phone: str,
    password: str,
    name: str,
    email: str | None,
    user_repo: UserRepository,
) -> User:
    if await user_repo.get_by_phone(phone):
        raise RegistrationError(message="Telefone já cadastrado.")

    if email is not None and await user_repo.get_by_email(email):
        raise RegistrationError(message="E-mail já cadastrado.")

    return await user_repo.create(
        company_id=1,
        name=name,
        phone=phone,
        password_hash=hash_password(password),
        email=email,
    )
