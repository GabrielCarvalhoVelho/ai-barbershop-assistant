from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError, UserManagementError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.modules.admin_users import service


def _make_user(
    *, user_id: int, company_id: int = 1, role: UserRole = UserRole.CUSTOMER, is_active: bool = True
) -> User:
    user = User(
        id=user_id,
        company_id=company_id,
        name="Test",
        phone=f"+55119900{user_id:05d}",
        email=f"u{user_id}@test.com",
        password_hash=hash_password("pass"),
        role=role,
    )
    user.is_active = is_active
    return user


class TestListUsers:
    @pytest.mark.asyncio
    async def test_repassa_company_id_do_admin(self):
        admin = _make_user(user_id=1, company_id=42, role=UserRole.ADMIN)
        repo = AsyncMock()
        repo.list_by_company.return_value = ([], 0)

        await service.list_users(admin, repo, limit=10, offset=0, role=None)

        repo.list_by_company.assert_awaited_once_with(
            company_id=42, limit=10, offset=0, role=None
        )


class TestUpdateRole:
    @pytest.mark.asyncio
    async def test_promove_customer(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, role=UserRole.CUSTOMER)
        promoted = _make_user(user_id=2, role=UserRole.ADMIN)
        repo = AsyncMock()
        repo.get_by_id.return_value = target
        repo.update_role.return_value = promoted

        result = await service.update_role(admin, 2, UserRole.ADMIN, repo)

        assert result.role == UserRole.ADMIN
        repo.update_role.assert_awaited_once_with(2, UserRole.ADMIN)

    @pytest.mark.asyncio
    async def test_target_inexistente_levanta_not_found(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.update_role(admin, 99, UserRole.ADMIN, repo)

    @pytest.mark.asyncio
    async def test_target_de_outra_empresa_levanta_not_found(self):
        admin = _make_user(user_id=1, company_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, company_id=99, role=UserRole.CUSTOMER)
        repo = AsyncMock()
        repo.get_by_id.return_value = target

        with pytest.raises(NotFoundError):
            await service.update_role(admin, 2, UserRole.ADMIN, repo)

    @pytest.mark.asyncio
    async def test_admin_nao_pode_rebaixar_a_si_mesmo(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        repo = AsyncMock()
        repo.get_by_id.return_value = admin

        with pytest.raises(UserManagementError) as exc:
            await service.update_role(admin, 1, UserRole.CUSTOMER, repo)
        assert exc.value.code == "USR_001"

    @pytest.mark.asyncio
    async def test_nao_rebaixa_ultimo_admin(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, role=UserRole.ADMIN)  # outro admin
        repo = AsyncMock()
        repo.get_by_id.return_value = target
        repo.count_active_admins.return_value = 1  # só o target

        with pytest.raises(UserManagementError):
            await service.update_role(admin, 2, UserRole.CUSTOMER, repo)

    @pytest.mark.asyncio
    async def test_rebaixa_admin_quando_existem_outros(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, role=UserRole.ADMIN)
        rebaixado = _make_user(user_id=2, role=UserRole.CUSTOMER)
        repo = AsyncMock()
        repo.get_by_id.return_value = target
        repo.count_active_admins.return_value = 2
        repo.update_role.return_value = rebaixado

        result = await service.update_role(admin, 2, UserRole.CUSTOMER, repo)
        assert result.role == UserRole.CUSTOMER

    @pytest.mark.asyncio
    async def test_role_inalterado_nao_chama_update(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, role=UserRole.CUSTOMER)
        repo = AsyncMock()
        repo.get_by_id.return_value = target

        result = await service.update_role(admin, 2, UserRole.CUSTOMER, repo)

        assert result is target
        repo.update_role.assert_not_awaited()


class TestUpdateActive:
    @pytest.mark.asyncio
    async def test_desativa_customer(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, role=UserRole.CUSTOMER, is_active=True)
        desativado = _make_user(user_id=2, role=UserRole.CUSTOMER, is_active=False)
        repo = AsyncMock()
        repo.get_by_id.return_value = target
        repo.update_active.return_value = desativado

        result = await service.update_active(admin, 2, False, repo)
        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_admin_nao_pode_desativar_a_si_mesmo(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        repo = AsyncMock()
        repo.get_by_id.return_value = admin

        with pytest.raises(UserManagementError):
            await service.update_active(admin, 1, False, repo)

    @pytest.mark.asyncio
    async def test_nao_desativa_ultimo_admin(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, role=UserRole.ADMIN, is_active=True)
        repo = AsyncMock()
        repo.get_by_id.return_value = target
        repo.count_active_admins.return_value = 1

        with pytest.raises(UserManagementError):
            await service.update_active(admin, 2, False, repo)

    @pytest.mark.asyncio
    async def test_target_outra_empresa_levanta_not_found(self):
        admin = _make_user(user_id=1, company_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, company_id=99)
        repo = AsyncMock()
        repo.get_by_id.return_value = target

        with pytest.raises(NotFoundError):
            await service.update_active(admin, 2, False, repo)

    @pytest.mark.asyncio
    async def test_active_inalterado_nao_chama_update(self):
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        target = _make_user(user_id=2, is_active=True)
        repo = AsyncMock()
        repo.get_by_id.return_value = target

        result = await service.update_active(admin, 2, True, repo)
        assert result is target
        repo.update_active.assert_not_awaited()
