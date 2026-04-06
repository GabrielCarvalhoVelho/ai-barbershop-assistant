import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import DB_TIMEOUT_SECONDS, db_operation
from app.core.logger import get_logger
from app.models.user import User

logger = get_logger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @db_operation("buscar usuário")
    async def get_by_id(self, user_id: int) -> User | None:
        return await asyncio.wait_for(
            self._session.get(User, user_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
