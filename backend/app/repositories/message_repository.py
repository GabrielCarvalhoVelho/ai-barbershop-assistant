from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, user_message: str, bot_response: str) -> Message:
        message = Message(user_message=user_message, bot_response=bot_response)
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def get_by_id(self, message_id: int) -> Message | None:
        return await self._session.get(Message, message_id)

    async def get_recent(self, limit: int = 10) -> list[Message]:
        stmt = (
            select(Message).order_by(Message.created_at.desc()).limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
