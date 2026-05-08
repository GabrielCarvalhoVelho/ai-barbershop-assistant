from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import get_current_user, require_role
from app.core.exceptions import AuthorizationError, InvalidTokenError
from app.core.security import create_access_token, hash_password
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


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_null_sub_raises_invalid_token(self):
        token = create_access_token({"data": "sem_sub"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_session = AsyncMock()
        with pytest.raises(InvalidTokenError) as exc_info:
            await get_current_user(credentials=credentials, session=mock_session)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "AUTH_003"

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_invalid_token(self):
        mock_session = AsyncMock()
        with pytest.raises(InvalidTokenError):
            await get_current_user(credentials=None, session=mock_session)

    @pytest.mark.asyncio
    async def test_user_deleted_after_token_issued(self):
        """Token válido mas user removido do DB → InvalidTokenError."""
        token = create_access_token({"sub": "999"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_session = AsyncMock()
        with patch("app.core.auth.UserRepository") as MockRepo:
            instance = AsyncMock()
            instance.get_by_id.return_value = None
            MockRepo.return_value = instance
            with pytest.raises(InvalidTokenError):
                await get_current_user(credentials=credentials, session=mock_session)

    def test_bearer_without_token_returns_401(self, client):
        """Header Authorization sem token após 'Bearer ' retorna 401."""
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})
        assert response.status_code == 401

    def test_non_bearer_scheme_returns_401(self, client):
        """Header Authorization com scheme diferente de Bearer retorna 401."""
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Token abc123"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_invalid_token(self):
        """JWT assinado com chave errada → InvalidTokenError."""
        from jose import jwt as _jwt
        token = _jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            "chave-errada-diferente-da-configurada",
            algorithm="HS256",
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_session = AsyncMock()
        with pytest.raises(InvalidTokenError) as exc_info:
            await get_current_user(credentials=credentials, session=mock_session)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "AUTH_003"

    @pytest.mark.asyncio
    async def test_expired_token_raises_invalid_token(self):
        """JWT com exp no passado → InvalidTokenError."""
        expired_token = create_access_token(
            {"sub": "1"},
            expires_delta=timedelta(seconds=-1),
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
        mock_session = AsyncMock()
        with pytest.raises(InvalidTokenError) as exc_info:
            await get_current_user(credentials=credentials, session=mock_session)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "AUTH_003"

    @pytest.mark.asyncio
    async def test_inactive_user_raises_invalid_token(self):
        """Token válido mas user.is_active=False → InvalidTokenError."""
        token = create_access_token({"sub": "1"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_session = AsyncMock()
        inactive_user = _make_user(UserRole.CUSTOMER)
        inactive_user.is_active = False
        with patch("app.core.auth.UserRepository") as MockRepo:
            instance = AsyncMock()
            instance.get_by_id.return_value = inactive_user
            MockRepo.return_value = instance
            with pytest.raises(InvalidTokenError) as exc_info:
                await get_current_user(credentials=credentials, session=mock_session)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "AUTH_003"
