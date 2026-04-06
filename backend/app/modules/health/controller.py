from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.modules.health.schemas import HealthResponse
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class HealthController:
    @staticmethod
    async def check(session: AsyncSession) -> tuple[SuccessResponse, bool]:
        """Verifica status da aplicação e do banco de dados.

        Returns:
            (SuccessResponse, db_ok) — db_ok indica se o banco está acessível.
        """
        try:
            await session.execute(text("SELECT 1"))
            db_status = "ok"
            db_ok = True
        except Exception as e:
            logger.error("Health check — banco indisponível: %s", e)
            db_status = "unavailable"
            db_ok = False

        overall = "ok" if db_ok else "degraded"
        logger.info("Health check executado: status=%s database=%s", overall, db_status)

        health = HealthResponse(status=overall, database=db_status)
        return SuccessResponse(data=health.model_dump()), db_ok
