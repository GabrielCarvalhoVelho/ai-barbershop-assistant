import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import DB_TIMEOUT_SECONDS, db_operation
from app.core.logger import get_logger
from app.models.enums import UserRole
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

    @db_operation("buscar usuário por email")
    async def get_by_email(self, email: str) -> User | None:
        result = await asyncio.wait_for(
            self._session.execute(select(User).where(User.email == email)),
            timeout=DB_TIMEOUT_SECONDS,
        )
        return result.scalars().first()

    @db_operation("buscar usuário por telefone")
    async def get_by_phone(self, phone: str) -> User | None:
        result = await asyncio.wait_for(
            self._session.execute(select(User).where(User.phone == phone)),
            timeout=DB_TIMEOUT_SECONDS,
        )
        return result.scalars().first()

    @db_operation("criar usuário")
    async def create(
        self,
        company_id: int,
        name: str,
        phone: str,
        password_hash: str,
        email: str | None = None,
    ) -> User:
        user = User(
            company_id=company_id,
            name=name,
            phone=phone,
            email=email,
            password_hash=password_hash,
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        self._session.add(user)
        await asyncio.wait_for(
            self._session.flush(),
            timeout=DB_TIMEOUT_SECONDS,
        )
        return user
