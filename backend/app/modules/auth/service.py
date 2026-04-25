from app.core.exceptions import AccountLockedError, AuthenticationError, RegistrationError
from app.core.lockout import get_lockout_remaining, is_locked, record_failure, reset_attempts
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository

_INVALID_CREDENTIALS = "Credenciais inválidas."


async def authenticate_user(phone: str, password: str, user_repo: UserRepository) -> User:
    if is_locked(phone):
        remaining = get_lockout_remaining(phone)
        raise AccountLockedError(message=f"Conta bloqueada. Tente novamente em {remaining} segundos.")

    user = await user_repo.get_by_phone(phone)
    if user is None or not user.is_active:
        record_failure(phone)
        raise AuthenticationError(message=_INVALID_CREDENTIALS)

    if not verify_password(password, user.password_hash):
        record_failure(phone)
        raise AuthenticationError(message=_INVALID_CREDENTIALS)

    reset_attempts(phone)
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
