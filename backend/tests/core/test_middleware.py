import pytest


class TestSecurityHeadersMiddleware:
    def test_x_frame_options_deny(self, client):
        response = client.get("/api/v1/health")
        assert response.headers["x-frame-options"] == "DENY"

    def test_x_content_type_options_nosniff(self, client):
        response = client.get("/api/v1/health")
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_x_xss_protection(self, client):
        response = client.get("/api/v1/health")
        assert response.headers["x-xss-protection"] == "1; mode=block"

    def test_referrer_policy(self, client):
        response = client.get("/api/v1/health")
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_hsts_absent_in_debug_mode(self, client):
        """Em DEBUG=true (ambiente de testes) HSTS não deve aparecer."""
        response = client.get("/api/v1/health")
        assert "strict-transport-security" not in response.headers

    def test_security_headers_present_on_error_response(self, client):
        """Headers de segurança devem aparecer mesmo em respostas 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_security_headers_present_on_post(self, client):
        """Headers presentes em responses de POST também."""
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "+5599000000000", "password": "errada"},  # phone não existe no seed
        )
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"
