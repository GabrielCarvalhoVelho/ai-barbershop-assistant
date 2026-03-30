from app.modules.health.controller import HealthController
from app.schemas.base_schema import SuccessResponse


# ========================
# HealthController
# ========================

class TestHealthController:
    def test_returns_success_response(self):
        response = HealthController.check()
        assert isinstance(response, SuccessResponse)
        assert response.success is True

    def test_data_contains_status_ok(self):
        response = HealthController.check()
        assert response.data == {"status": "ok"}
