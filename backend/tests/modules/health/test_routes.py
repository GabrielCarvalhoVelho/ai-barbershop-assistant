from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import OperationalError

from app.db.database import get_session
from app.main import app


# ========================
# GET /health — DB disponível
# ========================

class TestHealthDBOk:
    def test_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_body_success_true(self, client):
        body = client.get("/api/v1/health").json()
        assert body["success"] is True

    def test_data_status_ok(self, client):
        body = client.get("/api/v1/health").json()
        assert body["data"]["status"] == "ok"

    def test_data_database_ok(self, client):
        body = client.get("/api/v1/health").json()
        assert body["data"]["database"] == "ok"

    def test_has_timestamp(self, client):
        body = client.get("/api/v1/health").json()
        assert "timestamp" in body


# ========================
# GET /health — DB indisponível
# ========================

class TestHealthDBDown:
    def test_returns_503(self, client):
        def _broken_session():
            session = MagicMock()
            session.execute = AsyncMock(
                side_effect=OperationalError("SELECT 1", {}, Exception("refused"))
            )

            async def _gen():
                yield session

            return _gen()

        original = app.dependency_overrides.get(get_session)
        app.dependency_overrides[get_session] = _broken_session
        try:
            response = client.get("/api/v1/health")
            assert response.status_code == 503
        finally:
            if original is not None:
                app.dependency_overrides[get_session] = original
            else:
                app.dependency_overrides.pop(get_session, None)

    def test_data_status_degraded(self, client):
        def _broken_session():
            session = MagicMock()
            session.execute = AsyncMock(
                side_effect=OperationalError("SELECT 1", {}, Exception("refused"))
            )

            async def _gen():
                yield session

            return _gen()

        original = app.dependency_overrides.get(get_session)
        app.dependency_overrides[get_session] = _broken_session
        try:
            body = client.get("/api/v1/health").json()
            assert body["data"]["status"] == "degraded"
            assert body["data"]["database"] == "unavailable"
        finally:
            if original is not None:
                app.dependency_overrides[get_session] = original
            else:
                app.dependency_overrides.pop(get_session, None)
