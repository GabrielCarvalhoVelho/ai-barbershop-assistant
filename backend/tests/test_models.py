import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy import inspect

from app.db.database import Base
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, DocumentCategory, MessageSender, UserRole
from app.models.knowledge_document import KnowledgeDocument
from app.models.message import Message
from app.models.user import User


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


class TestCompanyModel:
    @pytest.mark.asyncio
    async def test_create_company_with_required_fields(self, session):
        company = Company(name="Barbearia do Zé")
        session.add(company)
        await session.commit()
        await session.refresh(company)

        assert company.id is not None
        assert company.name == "Barbearia do Zé"

    @pytest.mark.asyncio
    async def test_create_company_with_all_fields(self, session):
        company = Company(
            name="Barbearia do Zé",
            address="Rua das Flores, 123",
            phone="+551133445566",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)

        assert company.address == "Rua das Flores, 123"
        assert company.phone == "+551133445566"

    @pytest.mark.asyncio
    async def test_optional_fields_default_to_none(self, session):
        company = Company(name="Barbearia Simples")
        session.add(company)
        await session.commit()
        await session.refresh(company)

        assert company.address is None
        assert company.phone is None
        assert company.updated_at is None

    @pytest.mark.asyncio
    async def test_created_at_is_auto_generated(self, session):
        company = Company(name="Barbearia Teste")
        session.add(company)
        await session.commit()
        await session.refresh(company)

        assert company.created_at is not None

    @pytest.mark.asyncio
    async def test_table_name_is_companies(self):
        assert Company.__tablename__ == "companies"


@pytest_asyncio.fixture
async def company(session):
    company = Company(name="Barbearia do Zé")
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


class TestUserModel:
    @pytest.mark.asyncio
    async def test_create_user_with_required_fields(self, session, company):
        user = User(
            company_id=company.id,
            name="João Silva",
            phone="+5511999887766",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.name == "João Silva"
        assert user.phone == "+5511999887766"
        assert user.company_id == company.id

    @pytest.mark.asyncio
    async def test_create_user_with_all_fields(self, session, company):
        user = User(
            company_id=company.id,
            name="João Silva",
            phone="+5511999887766",
            email="joao@email.com",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.email == "joao@email.com"

    @pytest.mark.asyncio
    async def test_email_defaults_to_none(self, session, company):
        user = User(
            company_id=company.id,
            name="Maria",
            phone="+5511999887755",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.email is None
        assert user.updated_at is None

    @pytest.mark.asyncio
    async def test_created_at_is_auto_generated(self, session, company):
        user = User(
            company_id=company.id,
            name="Carlos",
            phone="+5511999887744",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_phone_must_be_unique(self, session, company):
        user1 = User(
            company_id=company.id,
            name="João",
            phone="+5511999887766",
            password_hash="placeholder",
        )
        session.add(user1)
        await session.commit()

        user2 = User(
            company_id=company.id,
            name="Maria",
            phone="+5511999887766",
            password_hash="placeholder",
        )
        session.add(user2)
        with pytest.raises(Exception):
            await session.commit()

    @pytest.mark.asyncio
    async def test_email_must_be_unique(self, session, company):
        user1 = User(
            company_id=company.id,
            name="João",
            phone="+5511999887766",
            email="joao@email.com",
            password_hash="placeholder",
        )
        session.add(user1)
        await session.commit()

        user2 = User(
            company_id=company.id,
            name="Maria",
            phone="+5511999887755",
            email="joao@email.com",
            password_hash="placeholder",
        )
        session.add(user2)
        with pytest.raises(Exception):
            await session.commit()

    @pytest.mark.asyncio
    async def test_is_active_defaults_to_true(self, session, company):
        user = User(
            company_id=company.id,
            name="Ativo",
            phone="+5511999887733",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_can_set_is_active_false(self, session, company):
        user = User(
            company_id=company.id,
            name="Inativo",
            phone="+5511999887722",
            password_hash="placeholder",
            is_active=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_password_hash_is_required(self, session, company):
        user = User(
            company_id=company.id,
            name="Sem Senha",
            phone="+5511999887711",
        )
        session.add(user)
        with pytest.raises(Exception):
            await session.commit()

    @pytest.mark.asyncio
    async def test_password_hash_stored_correctly(self, session, company):
        hash_value = "$2b$12$KRhijZ4qabcdefghijklmnopqrstuvwxyz0123456789ABCD"
        user = User(
            company_id=company.id,
            name="Com Senha",
            phone="+5511999887700",
            password_hash=hash_value,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.password_hash == hash_value

    @pytest.mark.asyncio
    async def test_role_defaults_to_customer(self, session, company):
        user = User(
            company_id=company.id,
            name="Default Role",
            phone="+5511999887699",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.role == UserRole.CUSTOMER

    @pytest.mark.asyncio
    async def test_can_set_role_admin(self, session, company):
        user = User(
            company_id=company.id,
            name="Admin User",
            phone="+5511999887688",
            password_hash="placeholder",
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_role_is_enum_instance(self, session, company):
        user = User(
            company_id=company.id,
            name="Enum Check",
            phone="+5511999887677",
            password_hash="placeholder",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert isinstance(user.role, UserRole)

    @pytest.mark.asyncio
    async def test_company_id_has_index(self):
        indexes = inspect(User).mapper.columns["company_id"]
        assert indexes is not None

    @pytest.mark.asyncio
    async def test_table_name_is_users(self):
        assert User.__tablename__ == "users"


@pytest_asyncio.fixture
async def user(session, company):
    user = User(
        company_id=company.id,
        name="João Silva",
        phone="+5511999887766",
        password_hash="placeholder",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class TestConversationModel:
    @pytest.mark.asyncio
    async def test_create_conversation_with_required_fields(
        self, session, user, company
    ):
        conv = Conversation(user_id=user.id, company_id=company.id)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        assert conv.id is not None
        assert conv.user_id == user.id
        assert conv.company_id == company.id

    @pytest.mark.asyncio
    async def test_status_defaults_to_active(self, session, user, company):
        conv = Conversation(user_id=user.id, company_id=company.id)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        assert conv.status == "active"

    @pytest.mark.asyncio
    async def test_started_at_is_auto_generated(self, session, user, company):
        conv = Conversation(user_id=user.id, company_id=company.id)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        assert conv.started_at is not None

    @pytest.mark.asyncio
    async def test_ended_at_defaults_to_none(self, session, user, company):
        conv = Conversation(user_id=user.id, company_id=company.id)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        assert conv.ended_at is None

    @pytest.mark.asyncio
    async def test_can_set_status_to_closed(self, session, user, company):
        conv = Conversation(
            user_id=user.id,
            company_id=company.id,
            status=ConversationStatus.CLOSED,
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        assert conv.status == ConversationStatus.CLOSED

    def test_invalid_status_rejected_by_enum(self):
        """ConversationStatus não aceita valores fora de 'active'/'closed'."""
        with pytest.raises(ValueError):
            ConversationStatus("banana")

    def test_status_enum_has_expected_values(self):
        assert ConversationStatus.ACTIVE.value == "active"
        assert ConversationStatus.CLOSED.value == "closed"
        assert len(ConversationStatus) == 2

    @pytest.mark.asyncio
    async def test_user_can_have_multiple_conversations(
        self, session, user, company
    ):
        conv1 = Conversation(user_id=user.id, company_id=company.id)
        conv2 = Conversation(user_id=user.id, company_id=company.id)
        session.add_all([conv1, conv2])
        await session.commit()
        await session.refresh(conv1)
        await session.refresh(conv2)

        assert conv1.id != conv2.id
        assert conv1.user_id == conv2.user_id

    @pytest.mark.asyncio
    async def test_table_name_is_conversations(self):
        assert Conversation.__tablename__ == "conversations"


@pytest_asyncio.fixture
async def conversation(session, user, company):
    conv = Conversation(user_id=user.id, company_id=company.id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


class TestMessageModel:
    @pytest.mark.asyncio
    async def test_create_message_with_required_fields(
        self, session, conversation
    ):
        msg = Message(
            conversation_id=conversation.id,
            sender="user",
            content="Quero cortar cabelo",
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

        assert msg.id is not None
        assert msg.conversation_id == conversation.id
        assert msg.sender == "user"
        assert msg.content == "Quero cortar cabelo"

    @pytest.mark.asyncio
    async def test_created_at_is_auto_generated(self, session, conversation):
        msg = Message(
            conversation_id=conversation.id,
            sender="bot",
            content="Olá! Como posso ajudar?",
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

        assert msg.created_at is not None

    @pytest.mark.asyncio
    async def test_sender_can_be_user(self, session, conversation):
        msg = Message(
            conversation_id=conversation.id,
            sender="user",
            content="Oi",
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

        assert msg.sender == "user"

    @pytest.mark.asyncio
    async def test_sender_can_be_bot(self, session, conversation):
        msg = Message(
            conversation_id=conversation.id,
            sender=MessageSender.BOT,
            content="Resposta",
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

        assert msg.sender == MessageSender.BOT

    def test_invalid_sender_rejected_by_enum(self):
        """MessageSender não aceita valores fora de 'user'/'bot'."""
        with pytest.raises(ValueError):
            MessageSender("hacker")

    def test_sender_enum_has_expected_values(self):
        assert MessageSender.USER.value == "user"
        assert MessageSender.BOT.value == "bot"
        assert len(MessageSender) == 2

    @pytest.mark.asyncio
    async def test_conversation_can_have_multiple_messages(
        self, session, conversation
    ):
        msg1 = Message(
            conversation_id=conversation.id,
            sender="user",
            content="Oi",
        )
        msg2 = Message(
            conversation_id=conversation.id,
            sender="bot",
            content="Olá!",
        )
        session.add_all([msg1, msg2])
        await session.commit()
        await session.refresh(msg1)
        await session.refresh(msg2)

        assert msg1.id != msg2.id
        assert msg1.conversation_id == msg2.conversation_id

    @pytest.mark.asyncio
    async def test_content_accepts_long_text(self, session, conversation):
        long_text = "A" * 2000
        msg = Message(
            conversation_id=conversation.id,
            sender="bot",
            content=long_text,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)

        assert len(msg.content) == 2000

    @pytest.mark.asyncio
    async def test_table_name_is_messages(self):
        assert Message.__tablename__ == "messages"


class TestKnowledgeDocumentModel:
    @pytest.mark.asyncio
    async def test_create_with_required_fields(self, session, company):
        doc = KnowledgeDocument(
            company_id=company.id,
            title="Corte masculino",
            content="Corte masculino — R$ 40,00.",
            category=DocumentCategory.SERVICES,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.id is not None
        assert doc.company_id == company.id
        assert doc.title == "Corte masculino"
        assert doc.content == "Corte masculino — R$ 40,00."
        assert doc.category == DocumentCategory.SERVICES

    @pytest.mark.asyncio
    async def test_is_active_defaults_to_true(self, session, company):
        doc = KnowledgeDocument(
            company_id=company.id,
            title="Horário",
            content="9h-19h",
            category=DocumentCategory.HOURS,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.is_active is True

    @pytest.mark.asyncio
    async def test_can_set_is_active_false(self, session, company):
        doc = KnowledgeDocument(
            company_id=company.id,
            title="Promoção encerrada",
            content="Promoção de verão.",
            category=DocumentCategory.SERVICES,
            is_active=False,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.is_active is False

    @pytest.mark.asyncio
    async def test_created_at_is_auto_generated(self, session, company):
        doc = KnowledgeDocument(
            company_id=company.id,
            title="FAQ",
            content="Resposta",
            category=DocumentCategory.FAQ,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.created_at is not None

    @pytest.mark.asyncio
    async def test_updated_at_defaults_to_none(self, session, company):
        doc = KnowledgeDocument(
            company_id=company.id,
            title="Geral",
            content="Info",
            category=DocumentCategory.GENERAL,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.updated_at is None

    @pytest.mark.asyncio
    async def test_content_accepts_long_text(self, session, company):
        long_text = "A" * 3000
        doc = KnowledgeDocument(
            company_id=company.id,
            title="Longo",
            content=long_text,
            category=DocumentCategory.GENERAL,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert len(doc.content) == 3000

    @pytest.mark.asyncio
    async def test_all_categories_accepted(self, session, company):
        for cat in DocumentCategory:
            doc = KnowledgeDocument(
                company_id=company.id,
                title=f"Doc {cat.value}",
                content=f"Conteúdo {cat.value}",
                category=cat,
            )
            session.add(doc)
        await session.commit()

    def test_invalid_category_rejected_by_enum(self):
        with pytest.raises(ValueError):
            DocumentCategory("invalid")

    def test_category_enum_has_expected_values(self):
        assert DocumentCategory.SERVICES.value == "services"
        assert DocumentCategory.HOURS.value == "hours"
        assert DocumentCategory.POLICIES.value == "policies"
        assert DocumentCategory.FAQ.value == "faq"
        assert DocumentCategory.GENERAL.value == "general"
        assert len(DocumentCategory) == 5

    @pytest.mark.asyncio
    async def test_company_can_have_multiple_documents(self, session, company):
        doc1 = KnowledgeDocument(
            company_id=company.id,
            title="Doc 1",
            content="Conteúdo 1",
            category=DocumentCategory.SERVICES,
        )
        doc2 = KnowledgeDocument(
            company_id=company.id,
            title="Doc 2",
            content="Conteúdo 2",
            category=DocumentCategory.HOURS,
        )
        session.add_all([doc1, doc2])
        await session.commit()
        await session.refresh(doc1)
        await session.refresh(doc2)

        assert doc1.id != doc2.id
        assert doc1.company_id == doc2.company_id

    @pytest.mark.asyncio
    async def test_table_name_is_knowledge_documents(self):
        assert KnowledgeDocument.__tablename__ == "knowledge_documents"
