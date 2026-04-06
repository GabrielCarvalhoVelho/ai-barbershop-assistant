from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app.modules.health.controller import HealthController
from app.schemas.base_schema import SuccessResponse


def _mock_session(raises=None):
    session = MagicMock()
    if raises:
        session.execute = AsyncMock(side_effect=raises)
    else:
        session.execute = AsyncMock(return_value=None)
    return session


# ========================
# DB disponível
# ========================

class TestHealthControllerDBOk:
    @pytest.mark.asyncio
    async def test_returns_success_response(self):
        response, db_ok = await HealthController.check(_mock_session())
        assert isinstance(response, SuccessResponse)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_data_status_ok(self):
        response, _ = await HealthController.check(_mock_session())
        assert response.data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_data_database_ok(self):
        response, _ = await HealthController.check(_mock_session())
        assert response.data["database"] == "ok"

    @pytest.mark.asyncio
    async def test_db_ok_is_true(self):
        _, db_ok = await HealthController.check(_mock_session())
        assert db_ok is True


# ========================
# DB indisponível
# ========================

class TestHealthControllerDBDown:
    @pytest.mark.asyncio
    async def test_returns_success_response_even_when_db_down(self):
        """O envelope é sempre SuccessResponse — o status HTTP é decidido na route."""
        session = _mock_session(
            raises=OperationalError("SELECT 1", {}, Exception("connection refused"))
        )
        response, _ = await HealthController.check(session)
        assert isinstance(response, SuccessResponse)

    @pytest.mark.asyncio
    async def test_data_status_degraded(self):
        session = _mock_session(
            raises=OperationalError("SELECT 1", {}, Exception("timeout"))
        )
        response, _ = await HealthController.check(session)
        assert response.data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_data_database_unavailable(self):
        session = _mock_session(
            raises=OperationalError("SELECT 1", {}, Exception("timeout"))
        )
        response, _ = await HealthController.check(session)
        assert response.data["database"] == "unavailable"

    @pytest.mark.asyncio
    async def test_db_ok_is_false(self):
        session = _mock_session(
            raises=OperationalError("SELECT 1", {}, Exception("pool exhausted"))
        )
        _, db_ok = await HealthController.check(session)
        assert db_ok is False

    @pytest.mark.asyncio
    async def test_any_exception_marks_db_unavailable(self):
        session = _mock_session(raises=Exception("unexpected"))
        response, db_ok = await HealthController.check(session)
        assert db_ok is False
        assert response.data["database"] == "unavailable"
