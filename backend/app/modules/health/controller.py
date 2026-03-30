from app.core.logger import get_logger
from app.modules.health.schemas import HealthResponse
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class HealthController:
    @staticmethod
    def check() -> SuccessResponse:
        logger.info("Health check executado")
        health = HealthResponse()
        return SuccessResponse(data=health.model_dump())
