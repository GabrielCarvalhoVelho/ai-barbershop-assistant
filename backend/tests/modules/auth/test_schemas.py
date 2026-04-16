import pytest
from pydantic import ValidationError

from app.models.enums import UserRole
from app.modules.auth.schemas import LoginRequest, TokenResponse, UserMeResponse


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(phone="+5511999000000", password="pass123")
        assert req.phone == "+5511999000000"
        assert req.password == "pass123"

    def test_missing_phone(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="pass123")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(phone="+5511999000000")

    def test_empty_password_fails(self):
        with pytest.raises(ValidationError):
            LoginRequest(phone="+5511999000000", password="")


class TestTokenResponse:
    def test_default_token_type(self):
        resp = TokenResponse(access_token="abc.def.ghi", expires_in=1800)
        assert resp.token_type == "bearer"

    def test_access_token_stored(self):
        resp = TokenResponse(access_token="my.jwt.token", expires_in=1800)
        assert resp.access_token == "my.jwt.token"

    def test_expires_in_stored(self):
        resp = TokenResponse(access_token="tok", expires_in=1800)
        assert resp.expires_in == 1800


class TestUserMeResponse:
    def test_from_orm(self):
        from app.models.user import User

        user = User(
            id=42,
            company_id=1,
            name="João",
            phone="+5511999000000",
            email="joao@test.com",
            password_hash="hash",
            role=UserRole.CUSTOMER,
        )
        resp = UserMeResponse.model_validate(user)
        assert resp.id == 42
        assert resp.name == "João"
        assert resp.email == "joao@test.com"
        assert resp.role == UserRole.CUSTOMER
        assert resp.company_id == 1

    def test_email_can_be_none(self):
        from app.models.user import User

        user = User(
            id=1,
            company_id=1,
            name="Sem Email",
            phone="+5511000000001",
            email=None,
            password_hash="hash",
            role=UserRole.CUSTOMER,
        )
        resp = UserMeResponse.model_validate(user)
        assert resp.email is None
