from app.core.exceptions import AppError, AuthorizationError, BusinessError, NotFoundError
from app.core.logger import get_logger
from app.core.permissions import ensure_owner_or_admin
from app.core.config import settings
from app.models.enums import ConversationStatus
from app.models.user import User
from app.modules.ai.context_service import format_knowledge_context
from app.modules.ai.prompts import BusinessInfo
from app.modules.chat.appointment_parser import extract_appointment, strip_appointment_block
from app.modules.chat.repository import ConversationRepository, MessageRepository
from app.repositories import CompanyRepository, KnowledgeDocumentRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.modules.chat.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationListItemResponse,
    ConversationListPaginatedResponse,
    ConversationMessagesResponse,
    ConversationResponse,
    ConversationSummaryResponse,
    MessageResponse,
    PaginationResponse,
)
from app.modules.chat.service import generate_response
from app.schemas.base_schema import SuccessResponse

logger = get_logger(__name__)


class ChatController:
    @staticmethod
    async def send_message(
        request: ChatRequest,
        current_user: User,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        company_repo: CompanyRepository,
        knowledge_repo: KnowledgeDocumentRepository,
        appointment_repo: AppointmentRepository,
    ) -> SuccessResponse:
        user_id = current_user.id
        company_id = current_user.company_id

        logger.info(
            "Chat iniciado: user_id=%s company_id=%s message_length=%s",
            user_id,
            company_id,
            len(request.message),
        )

        company = await company_repo.get_by_id(company_id)
        if company is None:
            raise NotFoundError(
                message=f"Empresa {company_id} não encontrada.",
            )

        conversation_id = request.conversation_id

        if conversation_id:
            conversation = await conversation_repo.get_by_id(conversation_id)
            if conversation is None:
                raise NotFoundError(
                    message=f"Conversa {conversation_id} não encontrada.",
                )
            if conversation.user_id != user_id or conversation.company_id != company_id:
                raise AuthorizationError(
                    message=f"Conversa {conversation_id} não pertence ao usuário ou empresa informados.",
                )
            if conversation.status == ConversationStatus.CLOSED:
                raise BusinessError(
                    message=f"Conversa {conversation_id} está encerrada. Crie uma nova conversa para continuar.",
                )
            logger.info("Conversa existente: id=%s", conversation_id)
        else:
            conversation = await conversation_repo.create(
                user_id=user_id,
                company_id=company_id,
            )
            conversation_id = conversation.id
            logger.info("Nova conversa criada: id=%s", conversation_id)

        history = await message_repo.get_by_conversation(
            conversation_id=conversation_id,
            limit=settings.llm_max_history,
        )

        business_info = BusinessInfo(
            name=company.name,
            phone=company.phone,
            address=company.address,
        )

        documents = await knowledge_repo.get_by_company(company_id)
        context = format_knowledge_context(documents)

        response_text = await generate_response(
            request.message, history, business_info, context=context
        )

        appointment_data = extract_appointment(response_text)
        if appointment_data is not None:
            try:
                has_conflict = await appointment_repo.has_conflict(
                    company_id=company_id,
                    scheduled_at=appointment_data.scheduled_at,
                    duration_minutes=appointment_data.duration_minutes,
                )
                if not has_conflict:
                    await appointment_repo.create(
                        user_id=user_id,
                        company_id=company_id,
                        service=appointment_data.service,
                        scheduled_at=appointment_data.scheduled_at,
                        duration_minutes=appointment_data.duration_minutes,
                    )
                    logger.info(
                        "Agendamento criado via chat: user_id=%s service=%s",
                        user_id,
                        appointment_data.service,
                    )
                else:
                    logger.warning(
                        "Conflito de horário via chat: user_id=%s scheduled_at=%s",
                        user_id,
                        appointment_data.scheduled_at,
                    )
            except Exception:
                logger.exception("Falha ao criar agendamento via chat: user_id=%s", user_id)
            response_text = strip_appointment_block(response_text)

        try:
            await message_repo.save_pair(
                conversation_id=conversation_id,
                user_content=request.message,
                bot_content=response_text,
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
            data=ChatResponse(
                response=response_text,
                conversation_id=conversation_id,
            ).model_dump()
        )


class ConversationController:
    @staticmethod
    async def create(
        current_user: User,
        conversation_repo: ConversationRepository,
        company_repo: CompanyRepository,
    ) -> SuccessResponse:
        user_id = current_user.id
        company_id = current_user.company_id

        logger.info(
            "Criando conversa: user_id=%s company_id=%s",
            user_id,
            company_id,
        )

        company = await company_repo.get_by_id(company_id)
        if company is None:
            raise NotFoundError(
                message=f"Empresa {company_id} não encontrada.",
            )

        conversation = await conversation_repo.create(
            user_id=user_id,
            company_id=company_id,
        )

        logger.info("Conversa criada: id=%s", conversation.id)

        return SuccessResponse(
            data=ConversationSummaryResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                company_id=conversation.company_id,
                status=conversation.status,
                started_at=conversation.started_at,
                ended_at=conversation.ended_at,
            ).model_dump()
        )

    @staticmethod
    async def get_by_id(
        conversation_id: int,
        current_user: User,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ) -> SuccessResponse:
        logger.info("Buscando conversa: id=%s", conversation_id)

        conversation = await conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(
                message=f"Conversa {conversation_id} não encontrada.",
            )

        ensure_owner_or_admin(
            current_user,
            resource_owner_id=conversation.user_id,
            resource_company_id=conversation.company_id,
            error_message=f"Conversa {conversation_id} não pertence ao usuário informado.",
        )

        message_count = await message_repo.count_by_conversation(conversation_id)

        logger.info(
            "Conversa encontrada: id=%s message_count=%s",
            conversation_id,
            message_count,
        )

        return SuccessResponse(
            data=ConversationResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                company_id=conversation.company_id,
                status=conversation.status,
                started_at=conversation.started_at,
                ended_at=conversation.ended_at,
                message_count=message_count,
            ).model_dump()
        )

    @staticmethod
    async def get_messages(
        conversation_id: int,
        current_user: User,
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

        ensure_owner_or_admin(
            current_user,
            resource_owner_id=conversation.user_id,
            resource_company_id=conversation.company_id,
            error_message=f"Conversa {conversation_id} não pertence ao usuário informado.",
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
            data=ConversationMessagesResponse(
                conversation_id=conversation_id,
                messages=[
                    MessageResponse(
                        id=msg.id,
                        sender=msg.sender,
                        content=msg.content,
                        created_at=msg.created_at,
                    )
                    for msg in messages
                ],
                pagination=PaginationResponse(
                    limit=limit,
                    offset=offset,
                    total=total,
                ),
            ).model_dump()
        )

    @staticmethod
    async def close(
        conversation_id: int,
        current_user: User,
        conversation_repo: ConversationRepository,
    ) -> SuccessResponse:
        logger.info("Encerrando conversa: id=%s", conversation_id)

        conversation = await conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(
                message=f"Conversa {conversation_id} não encontrada.",
            )

        ensure_owner_or_admin(
            current_user,
            resource_owner_id=conversation.user_id,
            resource_company_id=conversation.company_id,
            error_message=f"Conversa {conversation_id} não pertence ao usuário informado.",
        )

        if conversation.status == ConversationStatus.CLOSED:
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
            data=ConversationSummaryResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                company_id=conversation.company_id,
                status=conversation.status,
                started_at=conversation.started_at,
                ended_at=conversation.ended_at,
            ).model_dump()
        )

    @staticmethod
    async def list_user_conversations(
        user_id: int,
        company_id: int,
        limit: int,
        offset: int,
        conversation_repo: ConversationRepository,
    ) -> SuccessResponse:
        """Lista conversas do usuário, paginadas."""
        logger.info(
            "Listando conversas: user_id=%s company_id=%s limit=%s offset=%s",
            user_id,
            company_id,
            limit,
            offset,
        )

        conversations, total = await conversation_repo.list_by_user(
            user_id=user_id,
            company_id=company_id,
            limit=limit,
            offset=offset,
        )

        data = [
            {
                "id": c.id,
                "status": c.status,
                "started_at": c.started_at,
                "ended_at": c.ended_at,
                "message_count": len(c.messages),
                "last_message_preview": (
                    c.messages[-1].content[:100] + "..."
                    if c.messages
                    else None
                ),
            }
            for c in conversations
        ]

        logger.info(
            "Conversas listadas: user_id=%s company_id=%s returned=%s total=%s",
            user_id,
            company_id,
            len(data),
            total,
        )

        return SuccessResponse(
            data=ConversationListPaginatedResponse(
                conversations=[ConversationListItemResponse(**item) for item in data],
                pagination=PaginationResponse(
                    limit=limit,
                    offset=offset,
                    total=total,
                ),
            ).model_dump()
        )
