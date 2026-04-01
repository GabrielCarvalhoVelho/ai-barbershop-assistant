from app.core.exceptions import AppError, BusinessError, NotFoundError
from app.core.logger import get_logger
from app.modules.chat.repository import (
    CompanyRepository,
    ConversationRepository,
    MessageRepository,
    UserRepository,
)
from app.modules.chat.schemas import ChatRequest, CreateConversationRequest
from app.modules.chat.service import generate_response
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class ChatController:
    @staticmethod
    async def send_message(
        request: ChatRequest,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        user_repo: UserRepository,
        company_repo: CompanyRepository,
    ) -> SuccessResponse:
        logger.info(
            "Chat iniciado: user_id=%s company_id=%s message_length=%s",
            request.user_id,
            request.company_id,
            len(request.message),
        )

        user = await user_repo.get_by_id(request.user_id)
        if user is None:
            raise NotFoundError(
                message=f"Usuário {request.user_id} não encontrado.",
            )

        company = await company_repo.get_by_id(request.company_id)
        if company is None:
            raise NotFoundError(
                message=f"Empresa {request.company_id} não encontrada.",
            )

        conversation_id = request.conversation_id

        if conversation_id:
            conversation = await conversation_repo.get_by_id(conversation_id)
            if conversation is None:
                raise NotFoundError(
                    message=f"Conversa {conversation_id} não encontrada.",
                )
            if conversation.status == "closed":
                raise BusinessError(
                    message=f"Conversa {conversation_id} está encerrada. Crie uma nova conversa para continuar.",
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


class ConversationController:
    @staticmethod
    async def create(
        request: CreateConversationRequest,
        conversation_repo: ConversationRepository,
        user_repo: UserRepository,
        company_repo: CompanyRepository,
    ) -> SuccessResponse:
        logger.info(
            "Criando conversa: user_id=%s company_id=%s",
            request.user_id,
            request.company_id,
        )

        user = await user_repo.get_by_id(request.user_id)
        if user is None:
            raise NotFoundError(
                message=f"Usuário {request.user_id} não encontrado.",
            )

        company = await company_repo.get_by_id(request.company_id)
        if company is None:
            raise NotFoundError(
                message=f"Empresa {request.company_id} não encontrada.",
            )

        conversation = await conversation_repo.create(
            user_id=request.user_id,
            company_id=request.company_id,
        )

        logger.info("Conversa criada: id=%s", conversation.id)

        return SuccessResponse(
            data={
                "id": conversation.id,
                "user_id": conversation.user_id,
                "company_id": conversation.company_id,
                "status": conversation.status,
                "started_at": conversation.started_at.isoformat(),
                "ended_at": None,
            }
        )

    @staticmethod
    async def get_by_id(
        conversation_id: int,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ) -> SuccessResponse:
        logger.info("Buscando conversa: id=%s", conversation_id)

        conversation = await conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(
                message=f"Conversa {conversation_id} não encontrada.",
            )

        message_count = await message_repo.count_by_conversation(conversation_id)

        logger.info(
            "Conversa encontrada: id=%s message_count=%s",
            conversation_id,
            message_count,
        )

        return SuccessResponse(
            data={
                "id": conversation.id,
                "user_id": conversation.user_id,
                "company_id": conversation.company_id,
                "status": conversation.status,
                "started_at": conversation.started_at.isoformat(),
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
                "message_count": message_count,
            }
        )

    @staticmethod
    async def get_messages(
        conversation_id: int,
        limit: int,
        offset: int,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ) -> SuccessResponse:
        logger.info(
            "Buscando mensagens: conversation_id=%s limit=%s offset=%s",
            conversation_id,
            limit,
            offset,
        )

        conversation = await conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(
                message=f"Conversa {conversation_id} não encontrada.",
            )

        messages = await message_repo.get_by_conversation(
            conversation_id, limit=limit, offset=offset
        )
        total = await message_repo.count_by_conversation(conversation_id)

        logger.info(
            "Mensagens retornadas: conversation_id=%s count=%s total=%s",
            conversation_id,
            len(messages),
            total,
        )

        return SuccessResponse(
            data={
                "conversation_id": conversation_id,
                "messages": [
                    {
                        "id": msg.id,
                        "sender": msg.sender,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                    }
                    for msg in messages
                ],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total,
                },
            }
        )

    @staticmethod
    async def close(
        conversation_id: int,
        conversation_repo: ConversationRepository,
    ) -> SuccessResponse:
        logger.info("Encerrando conversa: id=%s", conversation_id)

        conversation = await conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(
                message=f"Conversa {conversation_id} não encontrada.",
            )

        if conversation.status == "closed":
            raise BusinessError(
                message=f"Conversa {conversation_id} já está encerrada.",
            )

        conversation = await conversation_repo.close(conversation_id)

        logger.info(
            "Conversa encerrada: id=%s ended_at=%s",
            conversation.id,
            conversation.ended_at,
        )

        return SuccessResponse(
            data={
                "id": conversation.id,
                "user_id": conversation.user_id,
                "company_id": conversation.company_id,
                "status": conversation.status,
                "started_at": conversation.started_at.isoformat(),
                "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
            }
        )
