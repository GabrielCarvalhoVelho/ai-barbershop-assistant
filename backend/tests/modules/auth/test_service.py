import logging

import pytest
from unittest.mock import AsyncMock, patch

import app.core.lockout as lockout_module
from app.core.exceptions import AccountLockedError, AuthenticationError
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


class TestAccountLockout:
    def setup_method(self):
        lockout_module._store.clear()

    @pytest.mark.asyncio
    async def test_lockout_after_max_attempts(self):
        """5 falhas consecutivas → 6ª levanta AccountLockedError (AUTH_005, 429)."""
        phone = "+5511lockout001"
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        for _ in range(5):
            with pytest.raises(AuthenticationError):
                await authenticate_user(phone, "errada", repo)

        with pytest.raises(AccountLockedError) as exc_info:
            await authenticate_user(phone, "errada", repo)
        assert exc_info.value.code == "AUTH_005"
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_success_resets_lockout_counter(self):
        """Login bem-sucedido zera o contador — 5 novas falhas necessárias para bloquear."""
        phone = "+5511lockout002"
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        for _ in range(3):
            with pytest.raises(AuthenticationError):
                await authenticate_user(phone, "errada", repo)

        repo.get_by_phone.return_value = user
        result = await authenticate_user(phone, "correct_pass", repo)
        assert result is user

        # Contador zerado — 3 novas falhas não bloqueiam
        repo.get_by_phone.return_value = None
        for _ in range(3):
            with pytest.raises(AuthenticationError):
                await authenticate_user(phone, "errada", repo)
        assert not lockout_module.is_locked(phone)

    @pytest.mark.asyncio
    async def test_lockout_message_contains_remaining_seconds(self):
        """Mensagem de bloqueio deve mencionar o tempo restante em segundos."""
        phone = "+5511lockout003"
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        for _ in range(5):
            with pytest.raises(AuthenticationError):
                await authenticate_user(phone, "errada", repo)

        with pytest.raises(AccountLockedError) as exc_info:
            await authenticate_user(phone, "errada", repo)
        assert "segundos" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_lockout_expires_after_ttl(self):
        """Após expirar o TTL, is_locked retorna False e novas tentativas são permitidas."""
        phone = "+5511lockout004"
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        with patch.object(lockout_module, "LOCKOUT_DURATION_SECONDS", 0):
            for _ in range(5):
                with pytest.raises(AuthenticationError):
                    await authenticate_user(phone, "errada", repo)

        assert not lockout_module.is_locked(phone)

    @pytest.mark.asyncio
    async def test_lockout_is_per_phone(self):
        """Bloqueio de um phone não afeta outro phone."""
        phone_a = "+5511lockout005A"
        phone_b = "+5511lockout005B"
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        for _ in range(5):
            with pytest.raises(AuthenticationError):
                await authenticate_user(phone_a, "errada", repo)

        # phone_b ainda não está bloqueado — deve levantar AuthenticationError (não lockout)
        with pytest.raises(AuthenticationError) as exc_info:
            await authenticate_user(phone_b, "errada", repo)
        assert exc_info.value.code == "AUTH_001"


class TestAuthServiceLogging:
    def setup_method(self):
        lockout_module._store.clear()

    @pytest.mark.asyncio
    async def test_login_failure_logged(self, caplog):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_phone.return_value = user

        with caplog.at_level(logging.WARNING, logger="app.modules.auth.service"):
            with pytest.raises(AuthenticationError):
                await authenticate_user("+5511000000001", "wrong_pass", repo)

        assert any("login_failed" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_login_success_logged(self, caplog):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_phone.return_value = user

        with caplog.at_level(logging.INFO, logger="app.modules.auth.service"):
            await authenticate_user("+5511000000001", "correct_pass", repo)

        assert any("login_success" in r.message for r in caplog.records)
        assert not any("+5511000000001" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_lockout_logged(self, caplog):
        phone = "+5511log001"
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        for _ in range(5):
            with pytest.raises(AuthenticationError):
                await authenticate_user(phone, "errada", repo)

        with caplog.at_level(logging.WARNING, logger="app.modules.auth.service"):
            with pytest.raises(AccountLockedError):
                await authenticate_user(phone, "errada", repo)

        assert any("login_blocked" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_phone_not_in_logs(self, caplog):
        phone = "+5511log002"
        repo = AsyncMock()
        repo.get_by_phone.return_value = None

        with caplog.at_level(logging.DEBUG, logger="app.modules.auth.service"):
            with pytest.raises(AuthenticationError):
                await authenticate_user(phone, "errada", repo)

        assert not any(phone in r.message for r in caplog.records)
