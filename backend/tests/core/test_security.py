import os
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


# ========================
# Rate Limiting
# ========================

class TestRateLimiting:
    def test_within_limit_succeeds(self, client, auth_headers):
        response = client.post("/api/v1/chat", json={"message": "Ola"}, headers=auth_headers)
        assert response.status_code == 200

    def test_exceeds_rate_limit(self, client, auth_headers):
        for _ in range(10):
            client.post("/api/v1/chat", json={"message": "Ola"}, headers=auth_headers)

        response = client.post("/api/v1/chat", json={"message": "Ola"}, headers=auth_headers)
        assert response.status_code == 429
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RATE_001"
        assert "Limite de requisições excedido" in body["error"]["message"]
        assert "timestamp" in body

    def test_health_not_rate_limited(self, client):
        for _ in range(15):
            response = client.get("/api/v1/health")
        assert response.status_code == 200


# ========================
# Autenticação por API Key
# ========================

class TestAuthNoKeyConfigured:
    """Quando API_KEY não está configurada, rotas JWT são acessíveis com token válido."""

    def test_chat_without_api_key_works_with_jwt(self, client, auth_headers):
        response = client.post("/api/v1/chat", json={"message": "Ola"}, headers=auth_headers)
        assert response.status_code == 200

    def test_health_never_requires_key(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_root_never_requires_key(self, client):
        response = client.get("/")
        assert response.status_code == 200


class TestAuthWithKeyConfigured:
    """Conversas usam JWT — API key não substitui Bearer token."""

    def test_conversations_without_jwt_returns_401(self):
        with patch.object(settings, "api_key", "test-secret-key"):
            client = TestClient(app)
            response = client.get("/api/v1/conversations/999")
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_003"

    def test_conversations_with_api_key_but_no_jwt_returns_401(self):
        with patch.object(settings, "api_key", "test-secret-key"):
            client = TestClient(app)
            response = client.get(
                "/api/v1/conversations/999",
                headers={"X-API-Key": "test-secret-key"},
            )
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_003"

    def test_health_still_open(self):
        with patch.object(settings, "api_key", "test-secret-key"):
            client = TestClient(app)
            response = client.get("/api/v1/health")
        assert response.status_code == 200


# ========================
# Validações de produção (Settings)
# ========================

class TestCorsConfig:
    def test_wildcard_cors_blocked_in_production(self):
        """CORS=['*'] + DEBUG=false deve falhar."""
        with patch.dict(
            "os.environ",
            {"CORS_ORIGINS": '["*"]', "DEBUG": "false", "API_KEY": "some-key"},
            clear=False,
        ):
            from app.core.config import Settings

            try:
                Settings()
                assert False, "Deveria ter levantado ValueError"
            except ValueError as e:
                assert "não é permitido" in str(e)

    def test_wildcard_cors_allowed_in_debug(self):
        """CORS=['*'] + DEBUG=true é permitido."""
        with patch.dict(
            "os.environ",
            {"CORS_ORIGINS": '["*"]', "DEBUG": "true"},
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.cors_origins == ["*"]


class TestApiKeyConfig:
    def test_empty_api_key_blocked_in_production(self):
        """API_KEY='' + DEBUG=false deve falhar."""
        with patch.dict(
            "os.environ",
            {"API_KEY": "", "DEBUG": "false"},
            clear=False,
        ):
            from app.core.config import Settings

            try:
                Settings()
                assert False, "Deveria ter levantado ValueError"
            except ValueError as e:
                assert "API_KEY é obrigatória" in str(e)

    def test_missing_api_key_blocked_in_production(self):
        """Sem API_KEY + DEBUG=false deve falhar."""
        env = os.environ.copy()
        env.pop("API_KEY", None)
        env["DEBUG"] = "false"
        with patch.dict("os.environ", env, clear=True):
            from app.core.config import Settings

            try:
                Settings()
                assert False, "Deveria ter levantado ValueError"
            except ValueError as e:
                assert "API_KEY é obrigatória" in str(e)

    def test_api_key_allowed_empty_in_debug(self):
        """API_KEY='' + DEBUG=true é permitido (dev mode)."""
        with patch.dict(
            "os.environ",
            {"API_KEY": "", "DEBUG": "true"},
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.api_key == ""

    def test_api_key_set_in_production_succeeds(self):
        """API_KEY definida + DEBUG=false deve funcionar."""
        with patch.dict(
            "os.environ",
            {"API_KEY": "my-prod-secret", "GROQ_API_KEY": "gsk_test", "JWT_SECRET_KEY": "jwtsecret", "DEBUG": "false"},
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.api_key == "my-prod-secret"


class TestGroqApiKeyConfig:
    def test_empty_groq_key_blocked_in_production(self):
        """GROQ_API_KEY='' + DEBUG=false deve falhar."""
        with patch.dict(
            "os.environ",
            {"GROQ_API_KEY": "", "API_KEY": "some-key", "DEBUG": "false"},
            clear=False,
        ):
            from app.core.config import Settings

            try:
                Settings()
                assert False, "Deveria ter levantado ValueError"
            except ValueError as e:
                assert "GROQ_API_KEY é obrigatória" in str(e)

    def test_missing_groq_key_blocked_in_production(self):
        """GROQ_API_KEY não definida + DEBUG=false deve falhar."""
        with patch.dict(
            "os.environ",
            {"GROQ_API_KEY": "", "API_KEY": "some-key", "DEBUG": "false"},
            clear=False,
        ):
            from app.core.config import Settings

            try:
                Settings()
                assert False, "Deveria ter levantado ValueError"
            except ValueError as e:
                assert "GROQ_API_KEY é obrigatória" in str(e)

    def test_groq_key_allowed_empty_in_debug(self):
        """GROQ_API_KEY='' + DEBUG=true é permitido (dev mode)."""
        with patch.dict(
            "os.environ",
            {"GROQ_API_KEY": "", "DEBUG": "true"},
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.groq_api_key == ""

    def test_groq_key_set_in_production_succeeds(self):
        """GROQ_API_KEY definida + DEBUG=false deve funcionar."""
        with patch.dict(
            "os.environ",
            {"GROQ_API_KEY": "gsk_test123", "API_KEY": "prod-key", "JWT_SECRET_KEY": "jwtsecret", "DEBUG": "false"},
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.groq_api_key == "gsk_test123"


class TestJwtSecretKeyConfig:
    def test_empty_jwt_secret_key_blocked_in_production(self):
        """JWT_SECRET_KEY='' + DEBUG=false deve falhar."""
        with patch.dict(
            "os.environ",
            {"JWT_SECRET_KEY": "", "API_KEY": "some-key", "GROQ_API_KEY": "gsk_test", "DEBUG": "false"},
            clear=False,
        ):
            from app.core.config import Settings

            try:
                Settings()
                assert False, "Deveria ter levantado ValueError"
            except ValueError as e:
                assert "JWT_SECRET_KEY é obrigatória" in str(e)

    def test_jwt_secret_key_allowed_empty_in_debug(self):
        """JWT_SECRET_KEY='' + DEBUG=true é permitido (dev mode)."""
        with patch.dict(
            "os.environ",
            {"JWT_SECRET_KEY": "", "DEBUG": "true"},
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.jwt_secret_key == ""

    def test_jwt_secret_key_set_in_production_succeeds(self):
        """JWT_SECRET_KEY definida + DEBUG=false deve funcionar."""
        with patch.dict(
            "os.environ",
            {"JWT_SECRET_KEY": "supersecret", "API_KEY": "prod-key", "GROQ_API_KEY": "gsk_test", "DEBUG": "false"},
            clear=False,
        ):
            from app.core.config import Settings

            s = Settings()
            assert s.jwt_secret_key == "supersecret"
