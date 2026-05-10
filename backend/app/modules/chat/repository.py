import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import DB_TIMEOUT_SECONDS, db_operation
from app.core.logger import get_logger
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, MessageSender
from app.models.message import Message

logger = get_logger(__name__)


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @db_operation("criar conversa")
    async def create(self, user_id: int, company_id: int) -> Conversation:
        logger.info("Criando conversa: user_id=%s company_id=%s", user_id, company_id)
        conversation = Conversation(user_id=user_id, company_id=company_id)
        self._session.add(conversation)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(conversation), timeout=DB_TIMEOUT_SECONDS)
        logger.info("Conversa criada: id=%s", conversation.id)
        return conversation

    @db_operation("buscar conversa")
    async def get_by_id(self, conversation_id: int) -> Conversation | None:
        logger.info("Buscando conversa: id=%s", conversation_id)
        result = await asyncio.wait_for(
            self._session.get(Conversation, conversation_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
        if result is None:
            logger.info("Conversa não encontrada: id=%s", conversation_id)
        return result

    @db_operation("buscar conversa ativa do usuário")
    async def get_active_by_user(
        self, user_id: int, company_id: int
    ) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.company_id == company_id,
                Conversation.status == ConversationStatus.ACTIVE,
            )
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        return result.scalars().first()

    @db_operation("encerrar conversa")
    async def close(self, conversation_id: int) -> Conversation | None:
        logger.info("Encerrando conversa: id=%s", conversation_id)
        conversation = await asyncio.wait_for(
            self._session.get(Conversation, conversation_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
        if conversation is None:
            logger.info("Conversa não encontrada para encerrar: id=%s", conversation_id)
            return None
        conversation.status = ConversationStatus.CLOSED
        conversation.ended_at = datetime.now(timezone.utc)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(conversation), timeout=DB_TIMEOUT_SECONDS)
        logger.info("Conversa encerrada: id=%s", conversation.id)
        return conversation

    @db_operation("listar conversas por usuário")
    async def list_by_user(
        self,
        user_id: int,
        company_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        """Lista conversas do usuário, paginadas por started_at DESC."""
        logger.info(
            "Listando conversas: user_id=%s company_id=%s limit=%s offset=%s",
            user_id,
            company_id,
            limit,
            offset,
        )
        stmt = (
            select(Conversation)
            .where(
                (Conversation.user_id == user_id)
                & (Conversation.company_id == company_id)
            )
            .order_by(Conversation.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        conversations = list(result.scalars().all())

        count_stmt = select(func.count(Conversation.id)).where(
            (Conversation.user_id == user_id)
            & (Conversation.company_id == company_id)
        )
        count_result = await asyncio.wait_for(
            self._session.execute(count_stmt), timeout=DB_TIMEOUT_SECONDS
        )
        total = count_result.scalar_one()

        logger.info(
            "Conversas listadas: user_id=%s company_id=%s count=%s total=%s",
            user_id,
            company_id,
            len(conversations),
            total,
        )
        return conversations, total


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @db_operation("salvar mensagem")
    async def save(
        self,
        conversation_id: int,
        sender: str,
        content: str,
        whatsapp_message_id: str | None = None,
    ) -> Message:
        logger.info(
            "Salvando mensagem: conversation_id=%s sender=%s", conversation_id, sender
        )
        message = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            whatsapp_message_id=whatsapp_message_id,
        )
        self._session.add(message)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(message), timeout=DB_TIMEOUT_SECONDS)
        logger.info("Mensagem salva: id=%s", message.id)
        return message

    @db_operation("buscar mensagem por whatsapp_message_id")
    async def get_by_whatsapp_id(self, whatsapp_message_id: str) -> Message | None:
        stmt = select(Message).where(
            Message.whatsapp_message_id == whatsapp_message_id
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        return result.scalars().first()

    @db_operation("salvar par de mensagens")
    async def save_pair(
        self,
        conversation_id: int,
        user_content: str,
        bot_content: str,
    ) -> tuple[Message, Message]:
        """Salva mensagem do user e do bot em uma única transação."""
        logger.info("Salvando par de mensagens: conversation_id=%s", conversation_id)
        user_msg = Message(
            conversation_id=conversation_id,
            sender=MessageSender.USER,
            content=user_content,
        )
        bot_msg = Message(
            conversation_id=conversation_id,
            sender=MessageSender.BOT,
            content=bot_content,
        )
        self._session.add(user_msg)
        self._session.add(bot_msg)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(user_msg), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(bot_msg), timeout=DB_TIMEOUT_SECONDS)
        logger.info(
            "Par de mensagens salvo: user_msg_id=%s bot_msg_id=%s",
            user_msg.id,
            bot_msg.id,
        )
        return user_msg, bot_msg

    @db_operation("buscar mensagem")
    async def get_by_id(self, message_id: int) -> Message | None:
        logger.info("Buscando mensagem: id=%s", message_id)
        result = await asyncio.wait_for(
            self._session.get(Message, message_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
        if result is None:
            logger.info("Mensagem não encontrada: id=%s", message_id)
        return result

    @db_operation("buscar mensagens")
    async def get_by_conversation(
        self, conversation_id: int, limit: int = 50, offset: int = 0
    ) -> list[Message]:
        logger.info(
            "Buscando mensagens: conversation_id=%s limit=%s offset=%s",
            conversation_id,
            limit,
            offset,
        )
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        messages = list(result.scalars().all())
        logger.info(
            "Mensagens encontradas: conversation_id=%s count=%s",
            conversation_id,
            len(messages),
        )
        return messages

    @db_operation("contar mensagens")
    async def count_by_conversation(self, conversation_id: int) -> int:
        logger.info("Contando mensagens: conversation_id=%s", conversation_id)
        stmt = select(func.count()).select_from(Message).where(
            Message.conversation_id == conversation_id
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        count = result.scalar_one()
        logger.info(
            "Total de mensagens: conversation_id=%s count=%s", conversation_id, count
        )
        return count
