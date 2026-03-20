import pytest

from app.controllers.chat_controller import ChatController
from app.controllers.health_controller import HealthController
from app.core.exceptions import BusinessError
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.schemas.health_schema import HealthResponse


# ========================
# ChatController
# ========================

class TestChatController:
    def test_returns_chat_response(self):
        request = ChatRequest(message="Quero agendar um corte")
        response = ChatController.send_message(request)
        assert isinstance(response, ChatResponse)

    def test_response_contains_message(self):
        request = ChatRequest(message="Olá")
        response = ChatController.send_message(request)
        assert response.response == "Você disse: Olá"

    def test_response_has_timestamp(self):
        request = ChatRequest(message="teste")
        response = ChatController.send_message(request)
        assert response.timestamp is not None

    def test_delegates_sanitization_to_service(self):
        request = ChatRequest(message="quero   agendar    corte")
        response = ChatController.send_message(request)
        assert response.response == "Você disse: quero agendar corte"

    def test_delegates_business_validation_to_service(self):
        request = ChatRequest(message="spam spam spam spam spam")
        with pytest.raises(BusinessError):
            ChatController.send_message(request)


# ========================
# HealthController
# ========================

class TestHealthController:
    def test_returns_health_response(self):
        response = HealthController.check()
        assert isinstance(response, HealthResponse)

    def test_status_is_ok(self):
        response = HealthController.check()
        assert response.status == "ok"
