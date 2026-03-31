from app.core.exceptions import AppError, NotFoundError
from app.core.logger import get_logger
from app.modules.chat.repository import (
    CompanyRepository,
    ConversationRepository,
    MessageRepository,
    UserRepository,
)
from app.modules.chat.schemas import ChatRequest
from app.modules.chat.service import generate_response
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class ChatController:
    @staticmethod
    async def send_message(
        request: ChatRequest,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ) -> SuccessResponse:
        logger.info(
            "Chat iniciado: user_id=%s company_id=%s message_length=%s",
            request.user_id,
            request.company_id,
            len(request.message),
        )

        conversation_id = request.conversation_id

        if conversation_id:
            conversation = await conversation_repo.get_by_id(conversation_id)
            if conversation is None:
                raise NotFoundError(
                    message=f"Conversa {conversation_id} não encontrada.",
                )
            logger.info("Conversa existente: id=%s", conversation_id)
        else:
            conversation = await conversation_repo.create(
                user_id=request.user_id,
                company_id=request.company_id,
            )
            conversation_id = conversation.id
            logger.info("Nova conversa criada: id=%s", conversation_id)

        try:
            await message_repo.save(
                conversation_id=conversation_id,
                sender="user",
                content=request.message,
            )

            response_text = generate_response(request.message)

            await message_repo.save(
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

        logger.info(
            "Chat concluído: conversation_id=%s response_length=%s",
            conversation_id,
            len(response_text),
        )

        return SuccessResponse(
            data={
                "response": response_text,
                "conversation_id": conversation_id,
            }
        )
