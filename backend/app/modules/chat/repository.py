import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, DatabaseError, ServiceUnavailableError
from app.core.logger import get_logger
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User

logger = get_logger(__name__)

DB_TIMEOUT_SECONDS = 10


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user_id: int, company_id: int) -> Conversation:
        logger.info(
            "Criando conversa: user_id=%s company_id=%s", user_id, company_id
        )
        conversation = Conversation(user_id=user_id, company_id=company_id)
        try:
            self._session.add(conversation)
            await asyncio.wait_for(
                self._session.commit(), timeout=DB_TIMEOUT_SECONDS
            )
            await asyncio.wait_for(
                self._session.refresh(conversation), timeout=DB_TIMEOUT_SECONDS
            )
        except IntegrityError as e:
            await self._session.rollback()
            logger.warning("IntegrityError ao criar conversa: %s", e.orig)
            raise ConflictError(
                message="Não foi possível criar a conversa. Verifique os dados enviados.",
            ) from e
        except (OperationalError, asyncio.TimeoutError) as e:
            await self._session.rollback()
            logger.error("Banco indisponível ao criar conversa: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error("Erro de banco ao criar conversa: %s", e)
            raise DatabaseError(
                message="Erro ao criar a conversa.",
            ) from e

        logger.info("Conversa criada: id=%s", conversation.id)
        return conversation

    async def get_by_id(self, conversation_id: int) -> Conversation | None:
        logger.info("Buscando conversa: id=%s", conversation_id)
        try:
            result = await asyncio.wait_for(
                self._session.get(Conversation, conversation_id),
                timeout=DB_TIMEOUT_SECONDS,
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao buscar conversa: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao buscar conversa: %s", e)
            raise DatabaseError(
                message="Erro ao buscar a conversa.",
            ) from e

        if result is None:
            logger.info("Conversa não encontrada: id=%s", conversation_id)
        return result

    async def get_active_by_user(
        self, user_id: int, company_id: int
    ) -> Conversation | None:
        logger.info(
            "Buscando conversa ativa: user_id=%s company_id=%s",
            user_id,
            company_id,
        )
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.company_id == company_id,
                Conversation.status == "active",
            )
            .order_by(Conversation.started_at.desc())
            .limit(1)
        )
        try:
            result = await asyncio.wait_for(
                self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao buscar conversa ativa: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao buscar conversa ativa: %s", e)
            raise DatabaseError(
                message="Erro ao buscar conversa ativa.",
            ) from e

        conversation = result.scalars().first()
        if conversation is None:
            logger.info(
                "Nenhuma conversa ativa: user_id=%s company_id=%s",
                user_id,
                company_id,
            )
        return conversation

    async def close(self, conversation_id: int) -> Conversation | None:
        logger.info("Encerrando conversa: id=%s", conversation_id)
        try:
            conversation = await asyncio.wait_for(
                self._session.get(Conversation, conversation_id),
                timeout=DB_TIMEOUT_SECONDS,
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao encerrar conversa: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao encerrar conversa: %s", e)
            raise DatabaseError(
                message="Erro ao encerrar a conversa.",
            ) from e

        if conversation is None:
            logger.info("Conversa não encontrada para encerrar: id=%s", conversation_id)
            return None

        conversation.status = "closed"
        conversation.ended_at = datetime.now(timezone.utc)
        try:
            await asyncio.wait_for(
                self._session.commit(), timeout=DB_TIMEOUT_SECONDS
            )
            await asyncio.wait_for(
                self._session.refresh(conversation), timeout=DB_TIMEOUT_SECONDS
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            await self._session.rollback()
            logger.error("Banco indisponível ao encerrar conversa: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error("Erro de banco ao encerrar conversa: %s", e)
            raise DatabaseError(
                message="Erro ao encerrar a conversa.",
            ) from e

        logger.info("Conversa encerrada: id=%s", conversation.id)
        return conversation


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(
        self, conversation_id: int, sender: str, content: str
    ) -> Message:
        logger.info(
            "Salvando mensagem: conversation_id=%s sender=%s",
            conversation_id,
            sender,
        )
        message = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
        )
        try:
            self._session.add(message)
            await asyncio.wait_for(
                self._session.commit(), timeout=DB_TIMEOUT_SECONDS
            )
            await asyncio.wait_for(
                self._session.refresh(message), timeout=DB_TIMEOUT_SECONDS
            )
        except IntegrityError as e:
            await self._session.rollback()
            logger.warning("IntegrityError ao salvar mensagem: %s", e.orig)
            raise ConflictError(
                message="Não foi possível salvar a mensagem. Verifique os dados enviados.",
            ) from e
        except (OperationalError, asyncio.TimeoutError) as e:
            await self._session.rollback()
            logger.error("Banco indisponível ao salvar mensagem: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            await self._session.rollback()
            logger.error("Erro de banco ao salvar mensagem: %s", e)
            raise DatabaseError(
                message="Erro ao salvar a mensagem.",
            ) from e

        logger.info("Mensagem salva: id=%s", message.id)
        return message

    async def get_by_id(self, message_id: int) -> Message | None:
        logger.info("Buscando mensagem: id=%s", message_id)
        try:
            result = await asyncio.wait_for(
                self._session.get(Message, message_id),
                timeout=DB_TIMEOUT_SECONDS,
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao buscar mensagem: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao buscar mensagem: %s", e)
            raise DatabaseError(
                message="Erro ao buscar a mensagem.",
            ) from e

        if result is None:
            logger.info("Mensagem não encontrada: id=%s", message_id)
        return result

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
        try:
            result = await asyncio.wait_for(
                self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao buscar mensagens: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao buscar mensagens: %s", e)
            raise DatabaseError(
                message="Erro ao buscar mensagens.",
            ) from e

        messages = list(result.scalars().all())
        logger.info(
            "Mensagens encontradas: conversation_id=%s count=%s",
            conversation_id,
            len(messages),
        )
        return messages

    async def count_by_conversation(self, conversation_id: int) -> int:
        logger.info("Contando mensagens: conversation_id=%s", conversation_id)
        stmt = select(func.count()).select_from(Message).where(
            Message.conversation_id == conversation_id
        )
        try:
            result = await asyncio.wait_for(
                self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao contar mensagens: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao contar mensagens: %s", e)
            raise DatabaseError(
                message="Erro ao contar mensagens.",
            ) from e

        count = result.scalar_one()
        logger.info(
            "Total de mensagens: conversation_id=%s count=%s",
            conversation_id,
            count,
        )
        return count


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        try:
            return await asyncio.wait_for(
                self._session.get(User, user_id),
                timeout=DB_TIMEOUT_SECONDS,
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao buscar usuário: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao buscar usuário: %s", e)
            raise DatabaseError(
                message="Erro ao buscar o usuário.",
            ) from e


class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, company_id: int) -> Company | None:
        try:
            return await asyncio.wait_for(
                self._session.get(Company, company_id),
                timeout=DB_TIMEOUT_SECONDS,
            )
        except (OperationalError, asyncio.TimeoutError) as e:
            logger.error("Banco indisponível ao buscar empresa: %s", e)
            raise ServiceUnavailableError(
                message="Serviço de banco de dados indisponível.",
            ) from e
        except SQLAlchemyError as e:
            logger.error("Erro de banco ao buscar empresa: %s", e)
            raise DatabaseError(
                message="Erro ao buscar a empresa.",
            ) from e
