from app.schemas.base_schema import SuccessResponse
from app.schemas.health_schema import HealthResponse


class HealthController:
    @staticmethod
    def check() -> SuccessResponse:
        health = HealthResponse()
        return SuccessResponse(data=health.model_dump())
