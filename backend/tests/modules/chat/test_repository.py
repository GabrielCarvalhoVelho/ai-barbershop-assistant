import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy import event, text

from app.core.exceptions import ConflictError
from app.db.database import Base
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.user import User
from app.modules.chat.repository import ConversationRepository, MessageRepository


def _enable_fk(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    event.listen(engine.sync_engine, "connect", _enable_fk)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def company(session):
    company = Company(name="Barbearia Teste")
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


@pytest_asyncio.fixture
async def user(session, company):
    user = User(company_id=company.id, name="João", phone="+5511999887766")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def conversation(session, user, company):
    conv = Conversation(user_id=user.id, company_id=company.id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


# ========================
# ConversationRepository
# ========================


class TestConversationRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_returns_conversation_with_id(self, session, user, company):
        repo = ConversationRepository(session)
        conv = await repo.create(user.id, company.id)

        assert conv.id is not None
        assert conv.user_id == user.id
        assert conv.company_id == company.id

    @pytest.mark.asyncio
    async def test_create_sets_status_active(self, session, user, company):
        repo = ConversationRepository(session)
        conv = await repo.create(user.id, company.id)

        assert conv.status == "active"

    @pytest.mark.asyncio
    async def test_create_sets_started_at(self, session, user, company):
        repo = ConversationRepository(session)
        conv = await repo.create(user.id, company.id)

        assert conv.started_at is not None

    @pytest.mark.asyncio
    async def test_create_ended_at_is_none(self, session, user, company):
        repo = ConversationRepository(session)
        conv = await repo.create(user.id, company.id)

        assert conv.ended_at is None

    @pytest.mark.asyncio
    async def test_create_with_invalid_user_raises_conflict(self, session, company):
        repo = ConversationRepository(session)
        with pytest.raises(ConflictError):
            await repo.create(user_id=999, company_id=company.id)

    @pytest.mark.asyncio
    async def test_create_with_invalid_company_raises_conflict(self, session, user):
        repo = ConversationRepository(session)
        with pytest.raises(ConflictError):
            await repo.create(user_id=user.id, company_id=999)


class TestConversationRepositoryGetById:
    @pytest.mark.asyncio
    async def test_get_by_id_returns_conversation(self, session, user, company):
        repo = ConversationRepository(session)
        created = await repo.create(user.id, company.id)
        found = await repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.user_id == user.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self, session):
        repo = ConversationRepository(session)
        found = await repo.get_by_id(999)

        assert found is None



class TestConversationRepositoryClose:
    @pytest.mark.asyncio
    async def test_close_sets_status_closed(self, session, user, company):
        repo = ConversationRepository(session)
        created = await repo.create(user.id, company.id)
        closed = await repo.close(created.id)

        assert closed is not None
        assert closed.status == "closed"

    @pytest.mark.asyncio
    async def test_close_sets_ended_at(self, session, user, company):
        repo = ConversationRepository(session)
        created = await repo.create(user.id, company.id)
        closed = await repo.close(created.id)

        assert closed.ended_at is not None

    @pytest.mark.asyncio
    async def test_close_returns_none_for_missing(self, session):
        repo = ConversationRepository(session)
        result = await repo.close(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_close_is_persisted(self, session, user, company):
        repo = ConversationRepository(session)
        created = await repo.create(user.id, company.id)
        await repo.close(created.id)
        found = await repo.get_by_id(created.id)

        assert found.status == "closed"
        assert found.ended_at is not None


# ========================
# MessageRepository
# ========================


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


class TestMessageRepositorySavePair:
    @pytest.mark.asyncio
    async def test_save_pair_returns_both_messages(self, session, conversation):
        repo = MessageRepository(session)
        user_msg, bot_msg = await repo.save_pair(
            conversation.id, "Oi", "Olá!"
        )

        assert user_msg.id is not None
        assert bot_msg.id is not None
        assert user_msg.sender == "user"
        assert bot_msg.sender == "bot"
        assert user_msg.content == "Oi"
        assert bot_msg.content == "Olá!"

    @pytest.mark.asyncio
    async def test_save_pair_persists_both(self, session, conversation):
        repo = MessageRepository(session)
        await repo.save_pair(conversation.id, "Oi", "Olá!")

        messages = await repo.get_by_conversation(conversation.id)
        assert len(messages) == 2
        assert messages[0].sender == "user"
        assert messages[1].sender == "bot"

    @pytest.mark.asyncio
    async def test_save_pair_same_conversation_id(self, session, conversation):
        repo = MessageRepository(session)
        user_msg, bot_msg = await repo.save_pair(
            conversation.id, "Oi", "Olá!"
        )

        assert user_msg.conversation_id == conversation.id
        assert bot_msg.conversation_id == conversation.id

    @pytest.mark.asyncio
    async def test_save_pair_invalid_conversation_raises_conflict(self, session):
        repo = MessageRepository(session)
        with pytest.raises(ConflictError):
            await repo.save_pair(999, "Oi", "Olá!")
