"""
Testes E2E: fluxo completo de chat com criação de agendamento automático.

Usa TestClient + SQLite in-memory real (conftest.py setup_db).
O mock do LLM é sobrescrito localmente para retornar blocos <APPOINTMENT>.
Os agendamentos criados são verificados via GET /api/v1/appointments/me.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

MOCK_TARGET = "app.modules.chat.service.generate_ai_response"


def _future_iso(days_ahead: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _appt_response(days_ahead: int, service: str = "Corte masculino") -> str:
    return (
        f"Perfeito! Agendei seu {service} para você.\n"
        "<APPOINTMENT>\n"
        f"service={service}\n"
        f"scheduled_at={_future_iso(days_ahead)}\n"
        "duration_minutes=30\n"
        "</APPOINTMENT>"
    )


def _chat(client, headers, message: str = "Quero agendar") -> dict:
    resp = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": message},
    )
    assert resp.status_code == 200
    return resp.json()["data"]


def _list_appointments(client, headers) -> list:
    resp = client.get("/api/v1/appointments/me", headers=headers)
    assert resp.status_code == 200
    return resp.json()["data"]["appointments"]


class TestChatAppointmentE2E:
    def test_chat_sem_bloco_nao_cria_agendamento(self, client, auth_headers):
        with patch(MOCK_TARGET, new=AsyncMock(return_value="Olá! Como posso ajudar?")):
            _chat(client, auth_headers)
        assert _list_appointments(client, auth_headers) == []

    def test_chat_com_bloco_valido_cria_agendamento(self, client, auth_headers):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=_appt_response(days_ahead=10))):
            _chat(client, auth_headers)
        appts = _list_appointments(client, auth_headers)
        assert len(appts) == 1
        assert appts[0]["service"] == "Corte masculino"
        assert appts[0]["status"] == "scheduled"

    def test_resposta_ao_cliente_nao_contem_bloco(self, client, auth_headers):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=_appt_response(days_ahead=11))):
            data = _chat(client, auth_headers)
        assert "<APPOINTMENT>" not in data["response"]
        assert "Perfeito! Agendei" in data["response"]

    def test_bloco_com_horario_no_passado_nao_cria_agendamento(self, client, auth_headers):
        passado = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        resposta = (
            "Agendado!\n"
            "<APPOINTMENT>\n"
            f"service=Barba\n"
            f"scheduled_at={passado}\n"
            "duration_minutes=30\n"
            "</APPOINTMENT>"
        )
        with patch(MOCK_TARGET, new=AsyncMock(return_value=resposta)):
            _chat(client, auth_headers)
        assert _list_appointments(client, auth_headers) == []

    def test_dois_chats_mesmo_horario_nao_duplica(self, client, auth_headers):
        horario = _future_iso(days_ahead=20)
        resposta = (
            "Agendado!\n"
            "<APPOINTMENT>\n"
            "service=Corte\n"
            f"scheduled_at={horario}\n"
            "duration_minutes=60\n"
            "</APPOINTMENT>"
        )
        with patch(MOCK_TARGET, new=AsyncMock(return_value=resposta)):
            _chat(client, auth_headers)
            _chat(client, auth_headers)

        appts = _list_appointments(client, auth_headers)
        # apenas 1 agendamento criado — o segundo teve conflito
        assert len(appts) == 1

    def test_agendamento_criado_via_chat_acessivel_por_id(self, client, auth_headers):
        with patch(MOCK_TARGET, new=AsyncMock(return_value=_appt_response(days_ahead=30))):
            _chat(client, auth_headers)
        appts = _list_appointments(client, auth_headers)
        assert len(appts) >= 1
        appt_id = appts[0]["id"]

        resp = client.get(f"/api/v1/appointments/{appt_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == appt_id
