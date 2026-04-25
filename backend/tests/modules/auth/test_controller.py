import pytest
from unittest.mock import AsyncMock, patch

from app.core.exceptions import AuthenticationError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.controller import AuthController
from app.modules.auth.schemas import LoginRequest


def _make_user() -> User:
    user = User(
        id=5,
        company_id=1,
        name="Ctrl User",
        phone="+5511000000005",
        email="ctrl@test.com",
        password_hash=hash_password("ctrl_pass"),
        role=UserRole.CUSTOMER,
    )
    user.is_active = True
    return user


class TestAuthController:
    @pytest.mark.asyncio
    async def test_login_returns_success_response(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_phone.return_value = user
        request = LoginRequest(phone="+5511000000005", password="ctrl_pass")

        response = await AuthController.login(request, repo)

        assert response.success is True
        assert "access_token" in response.data
        assert response.data["access_token"]
        assert "expires_in" in response.data

    @pytest.mark.asyncio
    async def test_login_bad_credentials_propagates(self):
        repo = AsyncMock()
        repo.get_by_phone.return_value = None
        request = LoginRequest(phone="+5599000000000", password="pass123")

        with pytest.raises(AuthenticationError):
            await AuthController.login(request, repo)

    @pytest.mark.asyncio
    async def test_me_returns_user_data(self):
        user = _make_user()
        response = await AuthController.me(user)

        assert response.success is True
        assert response.data["id"] == user.id
        assert response.data["email"] == user.email

    @pytest.mark.asyncio
    async def test_me_response_has_all_fields(self):
        user = _make_user()
        response = await AuthController.me(user)

        data = response.data
        assert "id" in data
        assert "name" in data
        assert "email" in data
        assert "phone" in data
        assert "role" in data
        assert "company_id" in data
