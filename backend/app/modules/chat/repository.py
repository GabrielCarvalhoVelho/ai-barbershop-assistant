import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, DatabaseError, ServiceUnavailableError
from app.core.logger import get_logger
from app.models.message import Message

logger = get_logger(__name__)

DB_TIMEOUT_SECONDS = 10


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
        self, conversation_id: int, limit: int = 50
    ) -> list[Message]:
        logger.info(
            "Buscando mensagens: conversation_id=%s limit=%s",
            conversation_id,
            limit,
        )
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
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
