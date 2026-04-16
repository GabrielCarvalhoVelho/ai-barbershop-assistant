import pytest
import pytest_asyncio

from app.models.company import Company
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
