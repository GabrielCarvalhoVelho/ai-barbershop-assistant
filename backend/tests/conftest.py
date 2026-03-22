import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.rate_limiter import limiter
from app.db.database import Base, get_session
from app.main import app

test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
test_async_session = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_session():
    async with test_async_session() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture(autouse=True)
def setup_db():
    loop = asyncio.new_event_loop()

    async def _setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    loop.run_until_complete(_setup())
    yield
    loop.run_until_complete(_teardown())
    loop.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    loop = asyncio.new_event_loop()

    async def _create():
        session = test_async_session()
        return session

    session = loop.run_until_complete(_create())
    yield session
    loop.run_until_complete(session.close())
    loop.close()
