from app.core.exceptions import AppError
from app.core.logger import get_logger
from app.modules.chat.repository import MessageRepository
from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.chat.service import generate_response
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class ChatController:
    @staticmethod
    async def send_message(
        request: ChatRequest,
        repository: MessageRepository | None = None,
        conversation_id: int | None = None,
    ) -> SuccessResponse:
        logger.info("Chat iniciado: message_length=%s", len(request.message))

        response_text = generate_response(request.message)

        if repository and conversation_id:
            try:
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
            except AppError:
                logger.error(
                    "Falha ao persistir mensagens: conversation_id=%s",
                    conversation_id,
                )
                raise

        logger.info("Chat concluído: response_length=%s", len(response_text))

        chat_response = ChatResponse(response=response_text)
        return SuccessResponse(data=chat_response.model_dump())
