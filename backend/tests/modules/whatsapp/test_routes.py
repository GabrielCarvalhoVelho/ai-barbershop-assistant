import json
from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.main import app
from app.modules.whatsapp.client import WhatsAppClient, get_whatsapp_client
from app.modules.whatsapp.signature import compute_signature

VERIFY_TOKEN = "test-verify-token"
APP_SECRET = "test-app-secret"


@pytest.fixture(autouse=True)
def whatsapp_settings():
    """Configura credenciais de teste e restaura ao final."""
    original_verify = settings.whatsapp_verify_token
    original_secret = settings.whatsapp_app_secret
    original_company = settings.whatsapp_default_company_id
    settings.whatsapp_verify_token = VERIFY_TOKEN
    settings.whatsapp_app_secret = APP_SECRET
    settings.whatsapp_default_company_id = 1
    yield
    settings.whatsapp_verify_token = original_verify
    settings.whatsapp_app_secret = original_secret
    settings.whatsapp_default_company_id = original_company


@pytest.fixture
def fake_client():
    """Cliente WhatsApp mock com send_text que sempre retorna um wamid."""
    client = WhatsAppClient(token="x", phone_number_id="x", api_version="v21.0")
    client.send_text = AsyncMock(return_value="wamid.outbound")  # type: ignore[method-assign]
    app.dependency_overrides[get_whatsapp_client] = lambda: client
    yield client
    app.dependency_overrides.pop(get_whatsapp_client, None)


def _build_payload(*, from_phone: str, wamid: str, text: str, name: str = "Cliente") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {"wa_id": from_phone, "profile": {"name": name}}
                            ],
                            "messages": [
                                {
                                    "id": wamid,
                                    "from": from_phone,
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _post_signed(client, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(body, APP_SECRET)
    return client.post(
        "/api/v1/webhooks/whatsapp",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sig,
        },
    )


class TestVerifyWebhook:
    def test_valid_token_returns_challenge_plaintext(self, client):
        resp = client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VERIFY_TOKEN,
                "hub.challenge": "abc123",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "abc123"

    def test_wrong_token_returns_403(self, client):
        resp = client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong",
                "hub.challenge": "abc123",
            },
        )
        assert resp.status_code == 403

    def test_wrong_mode_returns_403(self, client):
        resp = client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": VERIFY_TOKEN,
                "hub.challenge": "abc123",
            },
        )
        assert resp.status_code == 403


class TestReceiveEvent:
    def test_missing_signature_returns_403(self, client, fake_client):
        body = json.dumps(
            _build_payload(from_phone="5511999", wamid="w1", text="oi")
        ).encode()
        resp = client.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403
        fake_client.send_text.assert_not_called()

    def test_invalid_signature_returns_403(self, client, fake_client):
        body = json.dumps(
            _build_payload(from_phone="5511999", wamid="w1", text="oi")
        ).encode()
        resp = client.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=deadbeef",
            },
        )
        assert resp.status_code == 403
        fake_client.send_text.assert_not_called()

    def test_valid_signature_processes_and_replies(self, client, fake_client):
        payload = _build_payload(
            from_phone="5511988887777", wamid="w-novo-1", text="quero corte"
        )
        resp = _post_signed(client, payload)
        assert resp.status_code == 200
        fake_client.send_text.assert_awaited_once()
        # Deve ter respondido para o número normalizado com '+'
        called_kwargs = fake_client.send_text.await_args.kwargs
        assert called_kwargs["to"] == "+5511988887777"
        assert isinstance(called_kwargs["body"], str)

    def test_duplicate_wamid_is_idempotent(self, client, fake_client):
        payload = _build_payload(
            from_phone="5511988887777", wamid="w-dup-1", text="oi"
        )
        first = _post_signed(client, payload)
        second = _post_signed(client, payload)
        assert first.status_code == 200
        assert second.status_code == 200
        # send_text foi chamado só na primeira passagem
        assert fake_client.send_text.await_count == 1

    def test_payload_without_messages_returns_200_no_send(self, client, fake_client):
        # Status update / delivery receipt — sem 'messages'
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "ENTRY_ID",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "statuses": [{"id": "wamid.x", "status": "delivered"}],
                            },
                        }
                    ],
                }
            ],
        }
        resp = _post_signed(client, payload)
        assert resp.status_code == 200
        fake_client.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_user_when_phone_unknown(self, client, fake_client, db_session):
        from sqlalchemy import select

        from app.models.user import User

        async def _count(phone):
            result = await db_session.execute(
                select(User).where(User.phone == phone)
            )
            return len(list(result.scalars().all()))

        assert await _count("+5511955554444") == 0
        payload = _build_payload(
            from_phone="5511955554444", wamid="w-newuser", text="oi"
        )
        _post_signed(client, payload)
        assert await _count("+5511955554444") == 1

    def test_reuses_user_when_phone_known(self, client, fake_client):
        # User user2 do conftest tem phone +5511988888888 — vai ser reutilizado.
        payload = _build_payload(
            from_phone="5511988888888", wamid="w-existing", text="oi"
        )
        resp = _post_signed(client, payload)
        assert resp.status_code == 200
        fake_client.send_text.assert_awaited_once()

    def test_non_text_message_is_ignored(self, client, fake_client):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "ENTRY_ID",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [
                                    {"wa_id": "5511999", "profile": {"name": "X"}}
                                ],
                                "messages": [
                                    {
                                        "id": "w-img",
                                        "from": "5511999",
                                        "timestamp": "1700000000",
                                        "type": "image",
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        resp = _post_signed(client, payload)
        assert resp.status_code == 200
        fake_client.send_text.assert_not_called()
