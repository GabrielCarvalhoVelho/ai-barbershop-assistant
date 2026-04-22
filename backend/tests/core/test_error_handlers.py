from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError


# ========================
# HTTPException handler (404, 405)
# ========================

class TestHTTPExceptionHandler:
    def test_not_found_returns_error_response(self, client):
        response = client.get("/rota/que/nao/existe")
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "HTTP_404"
        assert "timestamp" in body

    def test_method_not_allowed_returns_error_response(self, client):
        response = client.delete("/api/v1/health")
        assert response.status_code == 405
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "HTTP_405"

    def test_not_found_has_request_id(self, client):
        response = client.get("/nope")
        body = response.json()
        assert "request_id" in body


# ========================
# IntegrityError handler (409 Conflict)
# ========================

class TestIntegrityErrorHandler:
    def _make_integrity_error(self, message: str) -> IntegrityError:
        return IntegrityError(
            statement="INSERT INTO ...",
            params={},
            orig=Exception(message),
        )

    def test_fk_violation_returns_409(self, client, auth_headers):
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=self._make_integrity_error("FOREIGN KEY constraint failed"),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        assert response.status_code == 409
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "DB_002"
        assert "Conflito" in body["error"]["message"]
        assert "timestamp" in body

    def test_unique_violation_returns_409(self, client, auth_headers):
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=self._make_integrity_error(
                "UNIQUE constraint failed: users.email"
            ),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DB_002"

    def test_integrity_error_does_not_leak_sql(self, client, auth_headers):
        """Statement SQL interno NÃO deve vazar para o cliente."""
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=self._make_integrity_error("secret_table.secret_column"),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        body = response.json()
        assert "secret_table" not in str(body)


# ========================
# OperationalError handler (503 Service Unavailable)
# ========================

class TestOperationalErrorHandler:
    def _make_operational_error(self, message: str) -> OperationalError:
        return OperationalError(
            statement="SELECT ...",
            params={},
            orig=Exception(message),
        )

    def test_db_unavailable_returns_503(self, client, auth_headers):
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=self._make_operational_error(
                "could not connect to server: Connection refused"
            ),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        assert response.status_code == 503
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "DB_003"
        assert "indisponível" in body["error"]["message"]
        assert "timestamp" in body

    def test_db_timeout_returns_503(self, client, auth_headers):
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=self._make_operational_error("connection timed out"),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DB_003"

    def test_operational_error_does_not_leak_details(self, client, auth_headers):
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=self._make_operational_error(
                "host=secret-db.internal port=5432"
            ),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        body = response.json()
        assert "secret-db" not in str(body)


# ========================
# SQLAlchemyError handler (500 fallback DB)
# ========================

class TestSQLAlchemyErrorHandler:
    def test_generic_db_error_returns_500(self, client, auth_headers):
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=SQLAlchemyError("unexpected internal error"),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        assert response.status_code == 500
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "DB_001"
        assert "banco de dados" in body["error"]["message"]
        assert "timestamp" in body

    def test_generic_db_error_does_not_leak_details(self, client, auth_headers):
        """Mensagem interna do banco NÃO deve vazar para o cliente."""
        with patch(
            "app.modules.chat.routes.ChatController.send_message",
            new_callable=AsyncMock,
            side_effect=SQLAlchemyError("secret internal state xyz"),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        body = response.json()
        assert "secret" not in str(body)
        assert "xyz" not in str(body)


# ========================
# Middleware catch-all (500 genérico)
# ========================

class TestErrorHandlerMiddleware:
    def test_unexpected_error_returns_500(self, client, auth_headers):
        with patch(
            "app.modules.chat.controller.generate_response",
            side_effect=RuntimeError("bug inesperado"),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        assert response.status_code == 500
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "APP_000"
        assert body["error"]["message"] == "Internal Server Error"

    def test_unexpected_error_does_not_leak_details(self, client, auth_headers):
        """Mensagem interna NÃO deve vazar para o cliente."""
        with patch(
            "app.modules.chat.controller.generate_response",
            side_effect=RuntimeError("segredo interno do sistema"),
        ):
            response = client.post(
                "/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers
            )

        body = response.json()
        assert "segredo" not in str(body)

    def test_unexpected_error_logs_stack_trace(self, client, auth_headers, caplog):
        import logging

        with caplog.at_level(logging.ERROR), patch(
            "app.modules.chat.controller.generate_response",
            side_effect=RuntimeError("erro para logar"),
        ):
            client.post("/api/v1/chat", json={"message": "Quero agendar"}, headers=auth_headers)

        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_logs) >= 1
        assert "erro para logar" in error_logs[0].message


# ========================
# Formato padronizado em todos os erros
# ========================

class TestErrorResponseFormat:
    """Garante que TODOS os tipos de erro retornam o envelope ErrorResponse."""

    @pytest.mark.parametrize(
        "method, path, json_body, expected_fields",
        [
            ("POST", "/api/v1/chat", {"message": ""}, ["success", "error", "timestamp"]),
            ("GET", "/rota/inexistente", None, ["success", "error", "timestamp"]),
            (
                "POST",
                "/api/v1/chat",
                {"message": "spam spam spam spam spam"},
                ["success", "error", "timestamp"],
            ),
        ],
    )
    def test_all_errors_have_standard_envelope(
        self, client, auth_headers, method, path, json_body, expected_fields
    ):
        response = client.request(method, path, json=json_body, headers=auth_headers if method == "POST" else None)
        body = response.json()
        for field in expected_fields:
            assert field in body, f"Campo '{field}' ausente na resposta"
        assert body["success"] is False
        assert "code" in body["error"]
        assert "message" in body["error"]
