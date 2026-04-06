import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import DB_TIMEOUT_SECONDS, db_operation
from app.core.logger import get_logger
from app.models.company import Company

logger = get_logger(__name__)


class CompanyRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @db_operation("buscar empresa")
    async def get_by_id(self, company_id: int) -> Company | None:
        return await asyncio.wait_for(
            self._session.get(Company, company_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
