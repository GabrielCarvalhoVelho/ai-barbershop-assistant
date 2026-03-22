import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.database import Base
from app.repositories.message_repository import MessageRepository


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as s:
        yield s
    await engine.dispose()


class TestMessageRepository:
    @pytest.mark.asyncio
    async def test_save_returns_message_with_id(self, session):
        repo = MessageRepository(session)
        msg = await repo.save("Ola", "Voce disse: Ola")
        assert msg.id is not None
        assert msg.user_message == "Ola"
        assert msg.bot_response == "Voce disse: Ola"

    @pytest.mark.asyncio
    async def test_save_sets_created_at(self, session):
        repo = MessageRepository(session)
        msg = await repo.save("oi", "resposta")
        assert msg.created_at is not None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_saved_message(self, session):
        repo = MessageRepository(session)
        saved = await repo.save("teste", "resposta")
        found = await repo.get_by_id(saved.id)
        assert found is not None
        assert found.user_message == "teste"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self, session):
        repo = MessageRepository(session)
        found = await repo.get_by_id(999)
        assert found is None

    @pytest.mark.asyncio
    async def test_get_recent_returns_ordered_messages(self, session):
        repo = MessageRepository(session)
        await repo.save("msg1", "resp1")
        await repo.save("msg2", "resp2")
        await repo.save("msg3", "resp3")
        recent = await repo.get_recent(limit=2)
        assert len(recent) == 2
        assert recent[0].user_message == "msg3"
