from app.repositories.message_repository import MessageRepository
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import generate_response


class ChatController:
    @staticmethod
    async def send_message(
        request: ChatRequest,
        repository: MessageRepository | None = None,
    ) -> ChatResponse:
        response_text = generate_response(request.message)

        if repository:
            await repository.save(
                user_message=request.message,
                bot_response=response_text,
            )

        return ChatResponse(response=response_text)
