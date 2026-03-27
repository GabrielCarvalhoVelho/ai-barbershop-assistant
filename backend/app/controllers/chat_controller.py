from app.repositories.message_repository import MessageRepository
from app.schemas.base_schema import SuccessResponse
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import generate_response


class ChatController:
    @staticmethod
    async def send_message(
        request: ChatRequest,
        repository: MessageRepository | None = None,
        conversation_id: int | None = None,
    ) -> SuccessResponse:
        response_text = generate_response(request.message)

        if repository and conversation_id:
            await repository.save(
                conversation_id=conversation_id,
                sender="user",
                content=request.message,
            )
            await repository.save(
                conversation_id=conversation_id,
                sender="bot",
                content=response_text,
            )

        chat_response = ChatResponse(response=response_text)
        return SuccessResponse(data=chat_response.model_dump())
