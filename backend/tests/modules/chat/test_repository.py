import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.database import Base
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.user import User
from app.modules.chat.repository import MessageRepository


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


@pytest_asyncio.fixture
async def conversation(session):
    company = Company(name="Barbearia Teste")
    session.add(company)
    await session.commit()
    await session.refresh(company)

    user = User(company_id=company.id, name="João", phone="+5511999887766")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    conv = Conversation(user_id=user.id, company_id=company.id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


class TestMessageRepository:
    @pytest.mark.asyncio
    async def test_save_returns_message_with_id(self, session, conversation):
        repo = MessageRepository(session)
        msg = await repo.save(conversation.id, "user", "Ola")

        assert msg.id is not None
        assert msg.conversation_id == conversation.id
        assert msg.sender == "user"
        assert msg.content == "Ola"

    @pytest.mark.asyncio
    async def test_save_sets_created_at(self, session, conversation):
        repo = MessageRepository(session)
        msg = await repo.save(conversation.id, "bot", "Resposta")

        assert msg.created_at is not None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_saved_message(self, session, conversation):
        repo = MessageRepository(session)
        saved = await repo.save(conversation.id, "user", "teste")
        found = await repo.get_by_id(saved.id)

        assert found is not None
        assert found.content == "teste"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self, session, conversation):
        repo = MessageRepository(session)
        found = await repo.get_by_id(999)

        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_conversation_returns_ordered_messages(
        self, session, conversation
    ):
        repo = MessageRepository(session)
        await repo.save(conversation.id, "user", "Oi")
        await repo.save(conversation.id, "bot", "Ola!")
        await repo.save(conversation.id, "user", "Quero cortar")

        messages = await repo.get_by_conversation(conversation.id)

        assert len(messages) == 3
        assert messages[0].content == "Oi"
        assert messages[1].content == "Ola!"
        assert messages[2].content == "Quero cortar"

    @pytest.mark.asyncio
    async def test_get_by_conversation_respects_limit(
        self, session, conversation
    ):
        repo = MessageRepository(session)
        await repo.save(conversation.id, "user", "msg1")
        await repo.save(conversation.id, "bot", "msg2")
        await repo.save(conversation.id, "user", "msg3")

        messages = await repo.get_by_conversation(conversation.id, limit=2)

        assert len(messages) == 2
