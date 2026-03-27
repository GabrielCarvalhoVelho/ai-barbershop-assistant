from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(
        self, conversation_id: int, sender: str, content: str
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
        )
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def get_by_id(self, message_id: int) -> Message | None:
        return await self._session.get(Message, message_id)

    async def get_by_conversation(
        self, conversation_id: int, limit: int = 50
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
