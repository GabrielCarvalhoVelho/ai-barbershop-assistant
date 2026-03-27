import pytest

from app.controllers.chat_controller import ChatController
from app.controllers.health_controller import HealthController
from app.core.exceptions import BusinessError
from app.schemas.base_schema import SuccessResponse
from app.schemas.chat_schema import ChatRequest


# ========================
# ChatController
# ========================

class TestChatController:
    @pytest.mark.asyncio
    async def test_returns_success_response(self):
        request = ChatRequest(message="Quero agendar um corte")
        response = await ChatController.send_message(request)
        assert isinstance(response, SuccessResponse)
        assert response.success is True

    @pytest.mark.asyncio
    async def test_data_contains_response(self):
        request = ChatRequest(message="Olá")
        response = await ChatController.send_message(request)
        assert response.data["response"] == "Você disse: Olá"

    @pytest.mark.asyncio
    async def test_response_has_timestamp(self):
        request = ChatRequest(message="teste")
        response = await ChatController.send_message(request)
        assert response.timestamp is not None

    @pytest.mark.asyncio
    async def test_delegates_sanitization_to_service(self):
        request = ChatRequest(message="quero   agendar    corte")
        response = await ChatController.send_message(request)
        assert response.data["response"] == "Você disse: quero agendar corte"

    @pytest.mark.asyncio
    async def test_delegates_business_validation_to_service(self):
        request = ChatRequest(message="spam spam spam spam spam")
        with pytest.raises(BusinessError):
            await ChatController.send_message(request)


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
