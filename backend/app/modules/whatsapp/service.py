"""Orquestração do fluxo de mensagens recebidas pelo WhatsApp.

Para cada mensagem incoming:
1. Idempotência via whatsapp_message_id (Meta reenvia eventos em caso de erro)
2. Resolve User pelo phone (auto-cria se não existir)
3. Resolve Conversation ATIVA do user (auto-cria se não existir)
4. Reusa pipeline de IA do módulo chat (conhecimento, prompt, parsing de
   appointment) — apenas adapta entrada/saída pra WhatsApp.
5. Persiste par user/bot e dispara envio outbound.
"""

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logger import get_logger
from app.modules.ai.context_service import format_knowledge_context
from app.modules.ai.prompts import BusinessInfo
from app.modules.chat.appointment_parser import (
    extract_appointment,
    strip_appointment_block,
)
from app.modules.chat.repository import ConversationRepository, MessageRepository
from app.modules.chat.service import generate_response
from app.modules.whatsapp.client import WhatsAppClient
from app.modules.whatsapp.schemas import WhatsAppWebhookPayload
from app.repositories import CompanyRepository, KnowledgeDocumentRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


def _normalize_phone(wa_id: str) -> str:
    """Meta envia wa_id como '5511999999999'; padronizamos para '+5511999999999'."""
    wa_id = wa_id.strip()
    if wa_id.startswith("+"):
        return wa_id
    return f"+{wa_id}"


def _extract_first_text_message(payload: WhatsAppWebhookPayload):
    """Extrai (contact_name, message) da primeira mensagem de texto válida.

    Retorna (None, None) para payloads sem messages (ex: status updates,
    delivery receipts) — esses são ack-eados sem processamento.
    """
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            if not value.messages:
                continue
            for msg in value.messages:
                if msg.type != "text" or msg.text is None:
                    continue
                contact_name = None
                if value.contacts:
                    profile = value.contacts[0].profile
                    if profile:
                        contact_name = profile.name
                return contact_name, msg
    return None, None


async def handle_webhook_payload(
    payload: WhatsAppWebhookPayload,
    *,
    user_repo: UserRepository,
    conversation_repo: ConversationRepository,
    message_repo: MessageRepository,
    company_repo: CompanyRepository,
    knowledge_repo: KnowledgeDocumentRepository,
    appointment_repo: AppointmentRepository,
    whatsapp_client: WhatsAppClient,
) -> None:
    # Status updates (sent/delivered/read/failed) — só logar para diagnóstico.
    for entry in payload.entry:
        for change in entry.changes:
            if change.value.statuses:
                for status in change.value.statuses:
                    logger.info(
                        "Status WhatsApp: status=%s wamid=%s errors=%s",
                        status.get("status"),
                        status.get("id"),
                        status.get("errors"),
                    )

    contact_name, msg = _extract_first_text_message(payload)
    if msg is None:
        logger.info("Webhook sem mensagem de texto — ack apenas.")
        return

    # Idempotência: se já processamos esse wamid antes, ignora.
    existing = await message_repo.get_by_whatsapp_id(msg.id)
    if existing is not None:
        logger.info("Mensagem WhatsApp duplicada ignorada (idempotência).")
        return

    company_id = settings.whatsapp_default_company_id
    company = await company_repo.get_by_id(company_id)
    if company is None:
        # Configuração inválida — não temos pra qual empresa atender.
        raise NotFoundError(message=f"Empresa {company_id} não encontrada.")

    phone = _normalize_phone(msg.from_phone)
    user, created = await user_repo.get_or_create_by_phone(
        phone=phone,
        company_id=company_id,
        name=contact_name or "Cliente WhatsApp",
    )
    if created:
        logger.info("Usuário criado via WhatsApp: company_id=%s", company_id)

    conversation = await conversation_repo.get_active_by_user(
        user_id=user.id, company_id=company_id
    )
    if conversation is None:
        conversation = await conversation_repo.create(
            user_id=user.id, company_id=company_id
        )

    history = await message_repo.get_by_conversation(
        conversation_id=conversation.id,
        limit=settings.llm_max_history,
    )

    documents = await knowledge_repo.get_by_company(company_id)
    context = format_knowledge_context(documents)
    business_info = BusinessInfo(
        name=company.name, phone=company.phone, address=company.address
    )

    response_text = await generate_response(
        msg.text.body, history, business_info, context=context
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
                    user_id=user.id,
                    company_id=company_id,
                    service=appointment_data.service,
                    scheduled_at=appointment_data.scheduled_at,
                    duration_minutes=appointment_data.duration_minutes,
                )
                logger.info("Agendamento criado via WhatsApp.")
        except Exception:
            logger.exception("Falha ao criar agendamento via WhatsApp.")
        response_text = strip_appointment_block(response_text)

    # Salva user com wamid (idempotência) e bot sem wamid (resposta nossa).
    await message_repo.save(
        conversation_id=conversation.id,
        sender="user",
        content=msg.text.body,
        whatsapp_message_id=msg.id,
    )
    await message_repo.save(
        conversation_id=conversation.id,
        sender="bot",
        content=response_text,
    )

    await whatsapp_client.send_text(to=phone, body=response_text)
