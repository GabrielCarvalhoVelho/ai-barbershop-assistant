import logging

from app.core.context import get_request_id, request_id_var
from app.core.middleware import REQUEST_ID_HEADER


# ========================
# Request ID — Middleware
# ========================

class TestRequestIDMiddleware:
    def test_response_has_request_id_header(self, client):
        response = client.get("/")
        assert REQUEST_ID_HEADER in response.headers
        assert len(response.headers[REQUEST_ID_HEADER]) > 0

    def test_generated_request_id_is_hex_uuid(self, client):
        response = client.get("/")
        rid = response.headers[REQUEST_ID_HEADER]
        assert rid.isalnum()
        assert len(rid) == 32

    def test_client_can_send_custom_request_id(self, client):
        custom_rid = "my-custom-request-id-123"
        response = client.get(
            "/", headers={REQUEST_ID_HEADER: custom_rid}
        )
        assert response.headers[REQUEST_ID_HEADER] == custom_rid

    def test_request_id_present_on_success(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Ola", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 200
        assert REQUEST_ID_HEADER in response.headers

    def test_request_id_present_on_error_422(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 422
        assert REQUEST_ID_HEADER in response.headers

    def test_request_id_present_on_error_400(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "spam spam spam spam spam", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 400
        assert REQUEST_ID_HEADER in response.headers


# ========================
# Request ID — Error Response Body
# ========================

class TestRequestIDInErrorBody:
    def test_error_422_body_has_request_id(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "", "user_id": 1, "company_id": 1},
        )
        body = response.json()
        assert "request_id" in body

    def test_error_400_body_has_request_id(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "spam spam spam spam spam", "user_id": 1, "company_id": 1},
        )
        body = response.json()
        assert "request_id" in body

    def test_error_request_id_matches_header(self, client):
        custom_rid = "trace-abc-123"
        response = client.post(
            "/api/v1/chat",
            json={"message": "", "user_id": 1, "company_id": 1},
            headers={REQUEST_ID_HEADER: custom_rid},
        )
        body = response.json()
        assert body["request_id"] == custom_rid
        assert response.headers[REQUEST_ID_HEADER] == custom_rid

    def test_success_response_has_no_request_id_in_body(self, client):
        """Sucesso não precisa de request_id no body — só no header."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Ola", "user_id": 1, "company_id": 1},
        )
        body = response.json()
        assert "request_id" not in body


# ========================
# Request ID — Context Var
# ========================

class TestRequestIDContext:
    def test_default_value_is_dash(self):
        assert get_request_id() == "-"

    def test_set_and_get(self):
        token = request_id_var.set("test-123")
        try:
            assert get_request_id() == "test-123"
        finally:
            request_id_var.reset(token)

    def test_reset_restores_default(self):
        token = request_id_var.set("temp")
        request_id_var.reset(token)
        assert get_request_id() == "-"


# ========================
# Logger — RequestIDFilter
# ========================

class TestRequestIDFilter:
    def test_log_record_has_request_id(self, caplog):
        token = request_id_var.set("rid-log-test")
        try:
            with caplog.at_level(logging.INFO):
                logger = logging.getLogger("test.filter")
                logger.info("mensagem de teste")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            assert hasattr(record, "request_id")
            assert record.request_id == "rid-log-test"
        finally:
            request_id_var.reset(token)

    def test_log_record_default_request_id(self, caplog):
        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test.filter.default")
            logger.info("sem contexto")

        record = caplog.records[-1]
        assert record.request_id == "-"
