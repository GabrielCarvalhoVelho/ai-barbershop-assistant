from datetime import timedelta

from app.core.security import create_access_token
from tests.modules.auth.conftest import TEST_EMAIL, TEST_PHONE, TEST_PASSWORD


class TestLoginRoute:
    def test_login_success(self, client, auth_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": TEST_PHONE, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["access_token"]
        assert body["data"]["token_type"] == "bearer"
        assert "expires_in" in body["data"]

    def test_login_wrong_password_401(self, client, auth_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": TEST_PHONE, "password": "wrong_password"},
        )
        assert response.status_code == 401
        assert response.json()["success"] is False

    def test_login_user_not_found_401(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "+5599000000000", "password": "pass123"},
        )
        assert response.status_code == 401

    def test_login_missing_phone_422(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "pass123"},
        )
        assert response.status_code == 422

    def test_login_missing_password_422(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": TEST_PHONE},
        )
        assert response.status_code == 422

    def test_login_inactive_user_401(self, client, inactive_auth_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "+5511666000099", "password": TEST_PASSWORD},
        )
        assert response.status_code == 401

    def test_login_phone_too_short_422(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "12345", "password": "pass123"},
        )
        assert response.status_code == 422

    def test_login_phone_too_long_422(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "+55119990000000000000000", "password": "pass123"},
        )
        assert response.status_code == 422

    def test_login_token_is_usable(self, client, auth_user):
        """Token retornado pelo login deve autenticar em /me."""
        login = client.post(
            "/api/v1/auth/login",
            json={"phone": TEST_PHONE, "password": TEST_PASSWORD},
        )
        assert login.status_code == 200
        token = login.json()["data"]["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["data"]["phone"] == TEST_PHONE

    def test_login_response_envelope(self, client, auth_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": TEST_PHONE, "password": TEST_PASSWORD},
        )
        body = response.json()
        assert body["success"] is True
        assert "timestamp" in body
        assert "data" in body
        assert body["data"]["token_type"] == "bearer"
        assert body["data"]["expires_in"] > 0

    def test_login_error_code_on_wrong_credentials(self, client, auth_user):
        """Resposta de erro deve conter o code AUTH_001."""
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": TEST_PHONE, "password": "wrong_password"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_001"

    def test_login_rate_limit_exceeded_429(self, client, auth_user):
        """6º request consecutivo deve retornar 429 com limite 5/minute."""
        payload = {"phone": TEST_PHONE, "password": "wrong_password"}
        for _ in range(5):
            client.post("/api/v1/auth/login", json=payload)
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 429


class TestMeRoute:
    def test_me_success(self, client, auth_user, auth_token):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == auth_user.id
        assert data["email"] == TEST_EMAIL

    def test_me_no_token_401(self, client, auth_user):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token_401(self, client, auth_user):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.real.token"},
        )
        assert response.status_code == 401

    def test_me_expired_token_401(self, client, auth_user):
        expired_token = create_access_token(
            {"sub": str(auth_user.id)},
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_me_response_envelope(self, client, auth_user, auth_token):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        body = response.json()
        assert body["success"] is True
        assert "timestamp" in body
        assert "data" in body

    def test_me_response_has_all_user_fields(self, client, auth_user, auth_token):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()["data"]
        assert "id" in data
        assert "name" in data
        assert "email" in data
        assert "phone" in data
        assert "role" in data
        assert "company_id" in data


class TestRegisterRoute:
    def test_register_success(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "phone": "+5511900000001",
                "password": "senha123",
                "name": "Maria Santos",
                "email": "maria@example.com",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["access_token"]
        assert body["data"]["token_type"] == "bearer"
        assert body["data"]["expires_in"] > 0

    def test_register_response_envelope(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "phone": "+5511900000002",
                "password": "senha123",
                "name": "Carlos",
            },
        )
        body = response.json()
        assert body["success"] is True
        assert "timestamp" in body
        assert "data" in body

    def test_register_token_is_usable(self, client):
        """Token retornado pelo register deve autenticar em /me."""
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "phone": "+5511900000003",
                "password": "senha123",
                "name": "Pedro",
            },
        )
        assert reg.status_code == 201
        token = reg.json()["data"]["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["data"]["phone"] == "+5511900000003"

    def test_register_phone_duplicate_400(self, client, auth_user):
        """Phone já cadastrado retorna 400 AUTH_004."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "phone": auth_user.phone,
                "password": "senha123",
                "name": "Outro",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "AUTH_004"

    def test_register_email_duplicate_400(self, client, auth_user):
        """Email já cadastrado retorna 400 AUTH_004."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "phone": "+5511900000004",
                "password": "senha123",
                "name": "Outro",
                "email": auth_user.email,
            },
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "AUTH_004"

    def test_register_missing_name_422(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={"phone": "+5511900000005", "password": "senha123"},
        )
        assert response.status_code == 422

    def test_register_missing_phone_422(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={"password": "senha123", "name": "João"},
        )
        assert response.status_code == 422

    def test_register_missing_password_422(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={"phone": "+5511900000006", "name": "João"},
        )
        assert response.status_code == 422

    def test_register_password_too_short_422(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={"phone": "+5511900000007", "password": "123", "name": "João"},
        )
        assert response.status_code == 422
