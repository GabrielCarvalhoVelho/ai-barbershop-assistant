from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthorizationError
from app.core.logger import get_logger
from app.db.database import get_session
from app.modules.chat.repository import ConversationRepository, MessageRepository
from app.modules.whatsapp import service
from app.modules.whatsapp.client import WhatsAppClient, get_whatsapp_client
from app.modules.whatsapp.schemas import WhatsAppWebhookPayload
from app.modules.whatsapp.signature import verify_signature
from app.repositories import CompanyRepository, KnowledgeDocumentRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/webhooks/whatsapp", tags=["webhooks - whatsapp"])


@router.get("", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Verificação inicial do webhook pela Meta.

    Meta envia GET com hub.mode=subscribe, hub.verify_token e hub.challenge.
    Se o verify_token bater com o configurado, retornamos o challenge cru.
    """
    if hub_mode != "subscribe" or hub_verify_token != settings.whatsapp_verify_token:
        logger.warning("Webhook WhatsApp: verify_token inválido.")
        raise AuthorizationError(message="Verify token inválido.")
    return PlainTextResponse(content=hub_challenge, status_code=200)


@router.post("")
async def receive_event(
    request: Request,
    session: AsyncSession = Depends(get_session),
    whatsapp_client: WhatsAppClient = Depends(get_whatsapp_client),
):
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(raw_body, signature_header, settings.whatsapp_app_secret):
        logger.warning("Webhook WhatsApp: assinatura HMAC inválida.")
        raise AuthorizationError(message="Assinatura inválida.")

    payload = WhatsAppWebhookPayload.model_validate_json(raw_body)

    await service.handle_webhook_payload(
        payload,
        user_repo=UserRepository(session),
        conversation_repo=ConversationRepository(session),
        message_repo=MessageRepository(session),
        company_repo=CompanyRepository(session),
        knowledge_repo=KnowledgeDocumentRepository(session),
        appointment_repo=AppointmentRepository(session),
        whatsapp_client=whatsapp_client,
    )
    return Response(status_code=200)
