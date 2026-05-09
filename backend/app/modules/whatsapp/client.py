"""Cliente HTTP para a Graph API do WhatsApp Cloud (envio de mensagens)."""

import httpx

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logger import get_logger

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 10.0


class WhatsAppClient:
    def __init__(
        self,
        token: str | None = None,
        phone_number_id: str | None = None,
        api_version: str | None = None,
    ):
        self._token = token or settings.whatsapp_token
        self._phone_number_id = phone_number_id or settings.whatsapp_phone_number_id
        self._api_version = api_version or settings.whatsapp_api_version

    @property
    def _base_url(self) -> str:
        return (
            f"https://graph.facebook.com/{self._api_version}"
            f"/{self._phone_number_id}/messages"
        )

    async def send_text(self, to: str, body: str) -> str:
        """Envia mensagem de texto e retorna o wamid retornado pela Meta."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    self._base_url, json=payload, headers=headers
                )
        except httpx.RequestError as exc:
            logger.error("Falha de rede ao enviar WhatsApp: %s", type(exc).__name__)
            raise ServiceUnavailableError(
                message="Não foi possível enviar mensagem pelo WhatsApp."
            )

        if response.status_code >= 400:
            # Body de ERRO da Meta é seguro logar (não contém PII da mensagem
            # original). Útil para diagnosticar 400 (recipient não aprovado etc).
            try:
                error_body = response.json()
            except Exception:
                error_body = {"raw": response.text[:500]}
            logger.error(
                "Meta retornou erro: status=%s phone_number_id=%s error=%s",
                response.status_code,
                self._phone_number_id,
                error_body,
            )
            raise ServiceUnavailableError(
                message="WhatsApp Cloud API retornou erro."
            )

        data = response.json()
        try:
            wamid = data["messages"][0]["id"]
        except (KeyError, IndexError):
            logger.error("Resposta inesperada da Meta ao enviar mensagem.")
            raise ServiceUnavailableError(
                message="Resposta inválida do WhatsApp Cloud API."
            )

        # Mascara o número (últimos 4 dígitos) só pra confirmar destino correto
        # em logs sem violar LGPD.
        masked_to = f"***{to[-4:]}" if len(to) >= 4 else "***"
        logger.info(
            "Mensagem WhatsApp enviada: wamid=%s to=%s contacts_returned=%s",
            wamid,
            masked_to,
            data.get("contacts", []),
        )
        return wamid


def get_whatsapp_client() -> WhatsAppClient:
    """Dependency para FastAPI. Permite override em testes."""
    return WhatsAppClient()
