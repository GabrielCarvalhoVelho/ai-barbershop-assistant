from datetime import timedelta

from app.core.security import create_access_token
from tests.modules.auth.conftest import TEST_EMAIL, TEST_PASSWORD


class TestLoginRoute:
    def test_login_success(self, client, auth_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["access_token"]
        assert body["data"]["token_type"] == "bearer"

    def test_login_wrong_password_401(self, client, auth_user):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": "wrong_password"},
        )
        assert response.status_code == 401
        assert response.json()["success"] is False

    def test_login_user_not_found_401(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "pass"},
        )
        assert response.status_code == 401

    def test_login_missing_email_422(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "pass123"},
        )
        assert response.status_code == 422

    def test_login_missing_password_422(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL},
        )
        assert response.status_code == 422


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
