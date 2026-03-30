import pytest

from app.core.exceptions import BusinessError
from app.modules.chat.controller import ChatController
from app.modules.chat.schemas import ChatRequest
from app.schemas.base_schema import SuccessResponse


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
