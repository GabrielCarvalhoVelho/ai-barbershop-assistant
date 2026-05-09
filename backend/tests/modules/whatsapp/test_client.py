from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import ServiceUnavailableError
from app.modules.whatsapp.client import WhatsAppClient


def _make_client():
    return WhatsAppClient(
        token="test-token",
        phone_number_id="123",
        api_version="v21.0",
    )


def _mock_response(status_code: int, json_data: dict):
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://graph.facebook.com"),
        json=json_data,
    )


class TestWhatsAppClient:
    @pytest.mark.asyncio
    async def test_send_text_returns_wamid(self):
        ok = _mock_response(200, {"messages": [{"id": "wamid.HXYZ123"}]})
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=ok)):
            wamid = await _make_client().send_text(to="+5511999", body="oi")
        assert wamid == "wamid.HXYZ123"

    @pytest.mark.asyncio
    async def test_send_text_4xx_raises_service_unavailable(self):
        bad = _mock_response(400, {"error": {"message": "x"}})
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=bad)):
            with pytest.raises(ServiceUnavailableError):
                await _make_client().send_text(to="+5511999", body="oi")

    @pytest.mark.asyncio
    async def test_send_text_request_error_raises_service_unavailable(self):
        with patch(
            "httpx.AsyncClient.post",
            new=AsyncMock(side_effect=httpx.ConnectError("refused")),
        ):
            with pytest.raises(ServiceUnavailableError):
                await _make_client().send_text(to="+5511999", body="oi")

    @pytest.mark.asyncio
    async def test_send_text_unexpected_response_raises(self):
        bad_shape = _mock_response(200, {"unexpected": "shape"})
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=bad_shape)):
            with pytest.raises(ServiceUnavailableError):
                await _make_client().send_text(to="+5511999", body="oi")

    def test_base_url_uses_phone_number_id_and_version(self):
        c = _make_client()
        assert c._base_url == "https://graph.facebook.com/v21.0/123/messages"
