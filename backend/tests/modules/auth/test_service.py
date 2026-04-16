import pytest
from unittest.mock import AsyncMock

from app.core.exceptions import AuthenticationError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.service import authenticate_user, _INVALID_CREDENTIALS


def _make_user(is_active: bool = True) -> User:
    user = User(
        id=1,
        company_id=1,
        name="Teste",
        phone="+5511000000001",
        email="user@test.com",
        password_hash=hash_password("correct_pass"),
        role=UserRole.CUSTOMER,
    )
    user.is_active = is_active
    return user


class TestAuthenticateUser:
    @pytest.mark.asyncio
    async def test_success_returns_user(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_phone.return_value = user

        result = await authenticate_user("+5511000000001", "correct_pass", repo)
        assert result is user

    @pytest.mark.asyncio
    async def test_wrong_password_raises(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_phone.return_value = user

        with pytest.raises(AuthenticationError):
            await authenticate_user("+5511000000001", "wrong_pass", repo)

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self):
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        with pytest.raises(AuthenticationError):
            await authenticate_user("+5599000000000", "pass", repo)

    @pytest.mark.asyncio
    async def test_inactive_user_raises(self):
        user = _make_user(is_active=False)
        repo = AsyncMock()
        repo.get_by_phone.return_value = user

        with pytest.raises(AuthenticationError):
            await authenticate_user("+5511000000001", "correct_pass", repo)

    @pytest.mark.asyncio
    async def test_same_error_message_prevents_enumeration(self):
        """Usuário não encontrado e senha errada retornam a mesma mensagem."""
        repo_not_found = AsyncMock()
        repo_not_found.get_by_phone.return_value = None

        repo_wrong_pass = AsyncMock()
        repo_wrong_pass.get_by_phone.return_value = _make_user()

        with pytest.raises(AuthenticationError) as exc_not_found:
            await authenticate_user("+5599000000000", "pass", repo_not_found)

        with pytest.raises(AuthenticationError) as exc_wrong_pass:
            await authenticate_user("+5511000000001", "wrong", repo_wrong_pass)

        assert exc_not_found.value.message == exc_wrong_pass.value.message == _INVALID_CREDENTIALS
