import pytest
import pytest_asyncio

from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.user import User

TEST_PHONE = "+5511777000099"
TEST_EMAIL = "auth_test@barbershop.dev"
TEST_PASSWORD = "test_pass_auth_123"


@pytest_asyncio.fixture
async def auth_user(db_session):
    user = User(
        company_id=1,
        name="Auth Test User",
        phone="+5511777000099",
        email=TEST_EMAIL,
        password_hash=hash_password(TEST_PASSWORD),
        role=UserRole.CUSTOMER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(auth_user):
    return create_access_token({"sub": str(auth_user.id)})
