import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
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

    @db_operation("listar usuários da empresa")
    async def list_by_company(
        self,
        company_id: int,
        limit: int = 20,
        offset: int = 0,
        role: UserRole | None = None,
    ) -> tuple[list[User], int]:
        base = select(User).where(User.company_id == company_id)
        if role is not None:
            base = base.where(User.role == role)

        count_stmt = select(func.count()).select_from(base.subquery())
        list_stmt = (
            base.order_by(User.created_at.desc()).offset(offset).limit(limit)
        )

        total_result, list_result = await asyncio.gather(
            asyncio.wait_for(
                self._session.execute(count_stmt), timeout=DB_TIMEOUT_SECONDS
            ),
            asyncio.wait_for(
                self._session.execute(list_stmt), timeout=DB_TIMEOUT_SECONDS
            ),
        )
        total = total_result.scalar_one()
        users = list(list_result.scalars().all())
        return users, total

    @db_operation("atualizar role do usuário")
    async def update_role(self, user_id: int, role: UserRole) -> User | None:
        user = await asyncio.wait_for(
            self._session.get(User, user_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
        if user is None:
            return None
        user.role = role
        user.updated_at = datetime.now(timezone.utc)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        return user

    @db_operation("atualizar status ativo do usuário")
    async def update_active(self, user_id: int, is_active: bool) -> User | None:
        user = await asyncio.wait_for(
            self._session.get(User, user_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
        if user is None:
            return None
        user.is_active = is_active
        user.updated_at = datetime.now(timezone.utc)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        return user

    @db_operation("contar admins ativos da empresa")
    async def count_active_admins(self, company_id: int) -> int:
        stmt = select(func.count()).select_from(User).where(
            User.company_id == company_id,
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        return result.scalar_one()
