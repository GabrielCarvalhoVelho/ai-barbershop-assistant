import pytest

from app.core.auth import require_role
from app.core.exceptions import AuthorizationError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


def _make_user(role: UserRole) -> User:
    user = User(
        id=1,
        company_id=1,
        name="Test User",
        phone="+5511000000001",
        email="test@test.com",
        password_hash=hash_password("pass"),
        role=role,
    )
    user.is_active = True
    return user


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_matching_role_returns_user(self):
        user = _make_user(UserRole.ADMIN)
        dep = require_role(UserRole.ADMIN)
        result = await dep(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_wrong_role_raises(self):
        user = _make_user(UserRole.CUSTOMER)
        dep = require_role(UserRole.ADMIN)
        with pytest.raises(AuthorizationError):
            await dep(current_user=user)

    @pytest.mark.asyncio
    async def test_multiple_roles_one_matches(self):
        user = _make_user(UserRole.ADMIN)
        dep = require_role(UserRole.CUSTOMER, UserRole.ADMIN)
        result = await dep(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_multiple_roles_none_match(self):
        user = _make_user(UserRole.CUSTOMER)
        dep = require_role(UserRole.ADMIN)
        with pytest.raises(AuthorizationError):
            await dep(current_user=user)

    @pytest.mark.asyncio
    async def test_raises_403_status(self):
        user = _make_user(UserRole.CUSTOMER)
        dep = require_role(UserRole.ADMIN)
        with pytest.raises(AuthorizationError) as exc_info:
            await dep(current_user=user)
        assert exc_info.value.status_code == 403
