from datetime import datetime, timedelta, timezone

import pytest


def _future_iso(days_ahead: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()


def _create_appt(client, headers, days_ahead: int = 1, duration_minutes: int = 30) -> dict:
    resp = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={
            "service": "Corte",
            "scheduled_at": _future_iso(days_ahead),
            "duration_minutes": duration_minutes,
        },
    )
    assert resp.status_code == 201
    return resp.json()["data"]


# ========================
# TestCreateAppointment
# ========================


class TestCreateAppointment:
    def test_body_valido_retorna_201(self, client, auth_headers):
        resp = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={"service": "Corte", "scheduled_at": _future_iso(), "duration_minutes": 30},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["id"] is not None
        assert data["service"] == "Corte"
        assert data["status"] == "scheduled"

    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.post(
            "/api/v1/appointments/",
            json={"service": "Corte", "scheduled_at": _future_iso()},
        )
        assert resp.status_code == 401

    def test_service_vazio_retorna_422(self, client, auth_headers):
        resp = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={"service": "", "scheduled_at": _future_iso()},
        )
        assert resp.status_code == 422

    def test_scheduled_at_no_passado_retorna_422(self, client, auth_headers):
        passado = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        resp = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={"service": "Corte", "scheduled_at": passado},
        )
        assert resp.status_code == 422

    def test_conflito_de_horario_retorna_400(self, client, auth_headers):
        # Cria primeiro agendamento (30min a partir de amanhã)
        _create_appt(client, auth_headers, days_ahead=2, duration_minutes=60)

        # Tenta criar no mesmo horário
        resp = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "service": "Barba",
                "scheduled_at": _future_iso(days_ahead=2),
                "duration_minutes": 30,
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "APT_001"


# ========================
# TestGetAppointment
# ========================


class TestGetAppointment:
    def test_owner_busca_proprio_retorna_200(self, client, auth_headers):
        appt = _create_appt(client, auth_headers, days_ahead=3)
        resp = client.get(f"/api/v1/appointments/{appt['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == appt["id"]

    def test_outro_user_retorna_403(self, client, auth_headers):
        # auth_headers = user_id=1; user2_headers = user_id=2
        user2_token = __import__(
            "app.core.security", fromlist=["create_access_token"]
        ).create_access_token({"sub": "2"})
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        appt = _create_appt(client, auth_headers, days_ahead=4)
        resp = client.get(f"/api/v1/appointments/{appt['id']}", headers=user2_headers)
        assert resp.status_code == 403

    def test_inexistente_retorna_404(self, client, auth_headers):
        resp = client.get("/api/v1/appointments/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.get("/api/v1/appointments/1")
        assert resp.status_code == 401


# ========================
# TestListMyAppointments
# ========================


class TestListMyAppointments:
    def test_sem_agendamentos_retorna_lista_vazia(self, client, auth_headers):
        resp = client.get("/api/v1/appointments/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["appointments"] == []
        assert data["pagination"]["total"] == 0

    def test_com_agendamento_retorna_lista(self, client, auth_headers):
        _create_appt(client, auth_headers, days_ahead=5)
        resp = client.get("/api/v1/appointments/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["appointments"]) >= 1

    def test_limit_1_retorna_um_item(self, client, auth_headers):
        _create_appt(client, auth_headers, days_ahead=6)
        _create_appt(client, auth_headers, days_ahead=7)
        resp = client.get("/api/v1/appointments/me?limit=1", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]["appointments"]) == 1

    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.get("/api/v1/appointments/me")
        assert resp.status_code == 401


# ========================
# TestCancelAppointment
# ========================


class TestCancelAppointment:
    def test_owner_cancela_retorna_200(self, client, auth_headers):
        appt = _create_appt(client, auth_headers, days_ahead=8)
        resp = client.patch(
            f"/api/v1/appointments/{appt['id']}/cancel", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_outro_user_nao_pode_cancelar(self, client, auth_headers):
        user2_token = __import__(
            "app.core.security", fromlist=["create_access_token"]
        ).create_access_token({"sub": "2"})
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        appt = _create_appt(client, auth_headers, days_ahead=9)
        resp = client.patch(
            f"/api/v1/appointments/{appt['id']}/cancel", headers=user2_headers
        )
        assert resp.status_code == 403

    def test_inexistente_retorna_404(self, client, auth_headers):
        resp = client.patch("/api/v1/appointments/99999/cancel", headers=auth_headers)
        assert resp.status_code == 404

    def test_ja_cancelado_retorna_400(self, client, auth_headers):
        appt = _create_appt(client, auth_headers, days_ahead=10)
        client.patch(f"/api/v1/appointments/{appt['id']}/cancel", headers=auth_headers)
        resp = client.patch(
            f"/api/v1/appointments/{appt['id']}/cancel", headers=auth_headers
        )
        assert resp.status_code == 400

    def test_sem_autenticacao_retorna_401(self, client):
        resp = client.patch("/api/v1/appointments/1/cancel")
        assert resp.status_code == 401

    def test_admin_cancela_agendamento_de_outro_user(self, client, auth_headers, admin_headers):
        appt = _create_appt(client, auth_headers, days_ahead=11)
        resp = client.patch(
            f"/api/v1/appointments/{appt['id']}/cancel", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"
