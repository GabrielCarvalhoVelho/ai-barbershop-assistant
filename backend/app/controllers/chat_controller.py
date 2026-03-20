from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import generate_response


class ChatController:
    @staticmethod
    def send_message(request: ChatRequest) -> ChatResponse:
        response = generate_response(request.message)
        return ChatResponse(response=response)
