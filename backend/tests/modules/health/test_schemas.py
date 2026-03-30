from app.modules.health.schemas import HealthResponse


# ========================
# HealthResponse
# ========================

class TestHealthResponse:
    def test_default_status(self):
        res = HealthResponse()
        assert res.status == "ok"
