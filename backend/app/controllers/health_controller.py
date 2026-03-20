from app.schemas.health_schema import HealthResponse


class HealthController:
    @staticmethod
    def check() -> HealthResponse:
        return HealthResponse()
