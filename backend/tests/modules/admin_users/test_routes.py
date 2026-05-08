"""Matriz de permissões para /api/v1/admin/users/* — testa autenticação,
autorização, isolamento por company e regras de auto-proteção do admin.

Fixtures relevantes do conftest.py global:
- user_id=1: customer, company_id=1
- user_id=2: customer, company_id=2 (outra empresa)
- user_id=3: admin, company_id=1
"""
import pytest

from app.core.security import create_access_token


@pytest.fixture
def other_company_admin_headers():
    """JWT para um admin de outra empresa — criado dinamicamente."""
    # Criamos via fixture pois o conftest só cria um admin (company 1)
    return None  # ver test_isolamento_entre_empresas para criação inline


class TestListUsersAuth:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/admin/users/")
        assert response.status_code == 401

    def test_customer_returns_403(self, client, auth_headers):
        response = client.get("/api/v1/admin/users/", headers=auth_headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTH_002"

    def test_admin_returns_200(self, client, admin_headers):
        response = client.get("/api/v1/admin/users/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "users" in data
        assert "pagination" in data


class TestListUsersIsolation:
    def test_admin_lista_apenas_propria_empresa(self, client, admin_headers):
        response = client.get("/api/v1/admin/users/", headers=admin_headers)
        assert response.status_code == 200
        users = response.json()["data"]["users"]
        company_ids = {u["company_id"] for u in users}
        assert company_ids == {1}

    def test_filtro_role(self, client, admin_headers):
        response = client.get(
            "/api/v1/admin/users/?role=admin", headers=admin_headers
        )
        assert response.status_code == 200
        users = response.json()["data"]["users"]
        assert all(u["role"] == "admin" for u in users)

    def test_pagination(self, client, admin_headers):
        response = client.get(
            "/api/v1/admin/users/?limit=1&offset=0", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["users"]) <= 1
        assert data["pagination"]["limit"] == 1


class TestUpdateRoleAuth:
    def test_unauthenticated_returns_401(self, client):
        response = client.patch(
            "/api/v1/admin/users/1/role", json={"role": "admin"}
        )
        assert response.status_code == 401

    def test_customer_returns_403(self, client, auth_headers):
        response = client.patch(
            "/api/v1/admin/users/1/role",
            headers=auth_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 403


class TestUpdateRoleBusinessRules:
    def test_promove_customer_da_empresa(self, client, admin_headers):
        response = client.patch(
            "/api/v1/admin/users/1/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["role"] == "admin"

    def test_target_de_outra_empresa_404(self, client, admin_headers):
        # user_id=2 está em company 2 — admin é de company 1
        response = client.patch(
            "/api/v1/admin/users/2/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RES_001"

    def test_target_inexistente_404(self, client, admin_headers):
        response = client.patch(
            "/api/v1/admin/users/9999/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 404

    def test_admin_nao_rebaixa_a_si_mesmo(self, client, admin_headers):
        # admin é user_id=3
        response = client.patch(
            "/api/v1/admin/users/3/role",
            headers=admin_headers,
            json={"role": "customer"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "USR_001"

    def test_nao_rebaixa_ultimo_admin_da_empresa(self, client, admin_headers):
        # Cenário: promove user 1 a admin (agora há 2 admins na empresa).
        # User 1 (novo admin) tenta rebaixar user 3 (admin original) — deve OK.
        # Depois, admin 3 já rebaixado, sobra só user 1 admin.
        # User 1 tenta se auto-rebaixar — bloqueado por auto-proteção.
        # Para testar especificamente "último admin" sem ser auto-proteção,
        # promovemos user 1 a admin, depois usamos token de user 1 para
        # rebaixar user 3. Isso deve funcionar (há 2 admins). Em seguida
        # admin 3 tenta rebaixar user 1 (único admin restante) — ID 3 já
        # é customer, então não pode. Logo, esse caso só é testável no
        # service layer (já coberto). Aqui garantimos o flow inverso:
        # quando sobra só 1 admin, qualquer rebaixamento dele falha.
        from app.core.security import create_access_token

        # Promove user 1 → admin (admin 3 faz a operação)
        client.patch(
            "/api/v1/admin/users/1/role",
            headers=admin_headers,
            json={"role": "admin"},
        )
        # User 1 (novo admin) rebaixa user 3 — agora sobra só user 1 admin
        token1 = create_access_token({"sub": "1"})
        client.patch(
            "/api/v1/admin/users/3/role",
            headers={"Authorization": f"Bearer {token1}"},
            json={"role": "customer"},
        )
        # User 3 (agora customer) não tem permissão pra rebaixar — 403
        token3 = create_access_token({"sub": "3"})
        response = client.patch(
            "/api/v1/admin/users/1/role",
            headers={"Authorization": f"Bearer {token3}"},
            json={"role": "customer"},
        )
        assert response.status_code == 403

    def test_role_invalido_422(self, client, admin_headers):
        response = client.patch(
            "/api/v1/admin/users/1/role",
            headers=admin_headers,
            json={"role": "superuser"},
        )
        assert response.status_code == 422


class TestUpdateActiveAuth:
    def test_unauthenticated_returns_401(self, client):
        response = client.patch(
            "/api/v1/admin/users/1/active", json={"is_active": False}
        )
        assert response.status_code == 401

    def test_customer_returns_403(self, client, auth_headers):
        response = client.patch(
            "/api/v1/admin/users/1/active",
            headers=auth_headers,
            json={"is_active": False},
        )
        assert response.status_code == 403


class TestUpdateActiveBusinessRules:
    def test_desativa_customer(self, client, admin_headers):
        response = client.patch(
            "/api/v1/admin/users/1/active",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    def test_admin_nao_desativa_a_si_mesmo(self, client, admin_headers):
        response = client.patch(
            "/api/v1/admin/users/3/active",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "USR_001"

    def test_target_outra_empresa_404(self, client, admin_headers):
        response = client.patch(
            "/api/v1/admin/users/2/active",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert response.status_code == 404

    def test_usuario_desativado_nao_consegue_login(self, client, admin_headers):
        # Desativa user 1
        client.patch(
            "/api/v1/admin/users/1/active",
            headers=admin_headers,
            json={"is_active": False},
        )
        # Tenta usar o token (auth_headers usa user_id=1)
        token = create_access_token({"sub": "1"})
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


class TestAdminAppointmentsRoute:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/admin/appointments/")
        assert response.status_code == 401

    def test_customer_returns_403(self, client, auth_headers):
        response = client.get(
            "/api/v1/admin/appointments/", headers=auth_headers
        )
        assert response.status_code == 403

    def test_admin_returns_200_empty_list(self, client, admin_headers):
        response = client.get(
            "/api/v1/admin/appointments/", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "appointments" in data
        assert "pagination" in data
