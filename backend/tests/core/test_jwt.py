from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from app.core.config import settings
from app.core.exceptions import InvalidTokenError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

_TEST_SECRET = "test-secret-key-for-unit-tests"


# ========================
# hash_password / verify_password
# ========================

class TestPasswordHashing:
    def test_hash_returns_bcrypt_string(self):
        h = hash_password("senha123")
        assert h.startswith("$2b$")

    def test_hash_is_different_each_call(self):
        h1 = hash_password("senha123")
        h2 = hash_password("senha123")
        assert h1 != h2

    def test_verify_correct_password(self):
        h = hash_password("senha123")
        assert verify_password("senha123", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("senha123")
        assert verify_password("errada", h) is False

    def test_verify_different_hashes_of_same_password(self):
        h1 = hash_password("abc")
        h2 = hash_password("abc")
        assert verify_password("abc", h1) is True
        assert verify_password("abc", h2) is True


# ========================
# create_access_token
# ========================

class TestCreateAccessToken:
    def test_create_token_returns_string(self):
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            token = create_access_token({"sub": "user:1"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_contains_sub(self):
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            token = create_access_token({"sub": "user:42"})
            payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "user:42"

    def test_create_token_custom_expiry(self):
        delta = timedelta(minutes=5)
        before = datetime.now(timezone.utc)
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            token = create_access_token({"sub": "user:1"}, expires_delta=delta)
            payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > before + timedelta(minutes=4)
        assert exp < before + timedelta(minutes=6)

    def test_create_token_default_expiry(self):
        before = datetime.now(timezone.utc)
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            token = create_access_token({"sub": "user:1"})
            payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_minutes = settings.jwt_access_token_expire_minutes
        assert exp > before + timedelta(minutes=expected_minutes - 1)
        assert exp < before + timedelta(minutes=expected_minutes + 1)


# ========================
# decode_access_token
# ========================

class TestDecodeAccessToken:
    def test_decode_valid_token(self):
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            token = create_access_token({"sub": "user:7"})
            payload = decode_access_token(token)
        assert payload["sub"] == "user:7"

    def test_decode_expired_token(self):
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            token = create_access_token(
                {"sub": "user:1"},
                expires_delta=timedelta(seconds=-1),
            )
            with pytest.raises(InvalidTokenError):
                decode_access_token(token)

    def test_decode_wrong_signature(self):
        other_token = jwt.encode(
            {"sub": "user:1", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
            "wrong-key",
            algorithm="HS256",
        )
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            with pytest.raises(InvalidTokenError):
                decode_access_token(other_token)

    def test_decode_malformed_token(self):
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            with pytest.raises(InvalidTokenError):
                decode_access_token("not.a.valid.jwt.token")

    def test_decode_error_has_auth003_code(self):
        with patch.object(settings, "jwt_secret_key", _TEST_SECRET):
            with pytest.raises(InvalidTokenError) as exc_info:
                decode_access_token("garbage")
        err = exc_info.value
        assert err.code == "AUTH_003"
        assert err.status_code == 401
