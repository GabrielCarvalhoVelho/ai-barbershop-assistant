import pytest
import pytest_asyncio

from app.models.company import Company
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository


@pytest_asyncio.fixture
async def repo_user(db_session):
    user = User(
        company_id=1,
        name="Repo Test",
        phone="+5511600000001",
        email="repo@test.com",
        password_hash="placeholder",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestUserRepositoryGetByEmail:
    @pytest.mark.asyncio
    async def test_get_by_email_found(self, db_session, repo_user):
        repo = UserRepository(db_session)
        result = await repo.get_by_email("repo@test.com")
        assert result is not None
        assert result.id == repo_user.id

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, db_session):
        repo = UserRepository(db_session)
        result = await repo.get_by_email("nobody@nowhere.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_still_works(self, db_session, repo_user):
        repo = UserRepository(db_session)
        result = await repo.get_by_id(repo_user.id)
        assert result is not None
        assert result.id == repo_user.id


class TestUserRepositoryGetByPhone:
    @pytest.mark.asyncio
    async def test_get_by_phone_found(self, db_session, repo_user):
        repo = UserRepository(db_session)
        result = await repo.get_by_phone(repo_user.phone)
        assert result is not None
        assert result.id == repo_user.id

    @pytest.mark.asyncio
    async def test_get_by_phone_not_found(self, db_session):
        repo = UserRepository(db_session)
        result = await repo.get_by_phone("+5500000000000")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_still_works(self, db_session, repo_user):
        repo = UserRepository(db_session)
        result = await repo.get_by_email("repo@test.com")
        assert result is not None
        assert result.id == repo_user.id


class TestUserRepositoryListByCompany:
    @pytest.mark.asyncio
    async def test_lists_only_company_users(self, db_session):
        repo = UserRepository(db_session)
        users, total = await repo.list_by_company(company_id=1)
        assert total == 2  # user_id=1 (customer) + user_id=3 (admin) — fixture
        company_ids = {u.company_id for u in users}
        assert company_ids == {1}

    @pytest.mark.asyncio
    async def test_filters_by_role(self, db_session):
        repo = UserRepository(db_session)
        admins, total = await repo.list_by_company(
            company_id=1, role=UserRole.ADMIN
        )
        assert total == 1
        assert all(u.role == UserRole.ADMIN for u in admins)

    @pytest.mark.asyncio
    async def test_pagination_limits_and_offset(self, db_session):
        repo = UserRepository(db_session)
        users, total = await repo.list_by_company(
            company_id=1, limit=1, offset=0
        )
        assert len(users) == 1
        assert total == 2

    @pytest.mark.asyncio
    async def test_other_company_isolated(self, db_session):
        repo = UserRepository(db_session)
        users, total = await repo.list_by_company(company_id=2)
        assert total == 1  # apenas user_id=2 (Outro Cliente) na fixture
        assert users[0].company_id == 2


class TestUserRepositoryUpdateRole:
    @pytest.mark.asyncio
    async def test_promote_customer_to_admin(self, db_session):
        repo = UserRepository(db_session)
        updated = await repo.update_role(1, UserRole.ADMIN)
        assert updated is not None
        assert updated.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_inexistent_returns_none(self, db_session):
        repo = UserRepository(db_session)
        result = await repo.update_role(9999, UserRole.ADMIN)
        assert result is None


class TestUserRepositoryUpdateActive:
    @pytest.mark.asyncio
    async def test_deactivate_user(self, db_session):
        repo = UserRepository(db_session)
        updated = await repo.update_active(1, False)
        assert updated is not None
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_reactivate_user(self, db_session):
        repo = UserRepository(db_session)
        await repo.update_active(1, False)
        updated = await repo.update_active(1, True)
        assert updated.is_active is True

    @pytest.mark.asyncio
    async def test_inexistent_returns_none(self, db_session):
        repo = UserRepository(db_session)
        result = await repo.update_active(9999, False)
        assert result is None


class TestUserRepositoryCountActiveAdmins:
    @pytest.mark.asyncio
    async def test_counts_only_active_admins_of_company(self, db_session):
        repo = UserRepository(db_session)
        count = await repo.count_active_admins(1)
        assert count == 1  # admin_user da fixture (user_id=3)

    @pytest.mark.asyncio
    async def test_other_company_zero(self, db_session):
        repo = UserRepository(db_session)
        count = await repo.count_active_admins(2)
        assert count == 0

    @pytest.mark.asyncio
    async def test_inactive_admin_not_counted(self, db_session):
        repo = UserRepository(db_session)
        await repo.update_active(3, False)
        count = await repo.count_active_admins(1)
        assert count == 0
