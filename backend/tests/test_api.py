# ========================
# GET /
# ========================

class TestRoot:
    def test_returns_running_message(self, client):
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] == {"message": "API is running"}
        assert "timestamp" in body


# ========================
# GET /health
# ========================

class TestHealth:
    def test_returns_ok(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] == {"status": "ok"}
        assert "timestamp" in body


# ========================
# POST /chat - sucesso
# ========================

class TestChatSuccess:
    def test_valid_message(self, client):
        response = client.post("/api/v1/chat", json={"message": "Quero agendar um corte"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["response"] == "Você disse: Quero agendar um corte"
        assert "timestamp" in body

    def test_sanitizes_spaces(self, client):
        response = client.post("/api/v1/chat", json={"message": "quero   agendar    corte"})
        assert response.status_code == 200
        assert response.json()["data"]["response"] == "Você disse: quero agendar corte"


# ========================
# POST /chat - erro 422 (validação de schema)
# ========================

class TestChatValidation422:
    def test_empty_message(self, client):
        response = client.post("/api/v1/chat", json={"message": ""})
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VAL_001"
        assert body["error"]["message"] == "Erro de validação na mensagem."
        assert "details" in body["error"]
        assert "timestamp" in body

    def test_only_spaces(self, client):
        response = client.post("/api/v1/chat", json={"message": "     "})
        assert response.status_code == 422
        assert "details" in response.json()["error"]

    def test_only_special_chars(self, client):
        response = client.post("/api/v1/chat", json={"message": "!!!"})
        assert response.status_code == 422
        error = response.json()["error"]
        assert any("letra ou número" in d for d in error["details"])

    def test_single_repeated_char(self, client):
        response = client.post("/api/v1/chat", json={"message": "aaaaaaa"})
        assert response.status_code == 422
        error = response.json()["error"]
        assert any("repetidos" in d for d in error["details"])

    def test_exceeds_max_length(self, client):
        response = client.post("/api/v1/chat", json={"message": "a" * 501})
        assert response.status_code == 422

    def test_missing_message_field(self, client):
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422

    def test_no_details_null_in_response(self, client):
        """Garante que o campo details nunca aparece como null."""
        response = client.post("/api/v1/chat", json={"message": ""})
        error = response.json()["error"]
        if "details" in error:
            assert error["details"] is not None


# ========================
# POST /chat - erro 400 (regra de negócio)
# ========================

class TestChatBusiness400:
    def test_repeated_chars_spam(self, client):
        response = client.post(
            "/api/v1/chat", json={"message": "olha isso aaaaaaaaaa que legal"}
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "repetitivo" in body["error"]["message"]
        assert "details" not in body["error"]
        assert "timestamp" in body

    def test_repeated_word_spam(self, client):
        response = client.post(
            "/api/v1/chat", json={"message": "spam spam spam spam spam"}
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "repetitivo" in body["error"]["message"]
        assert "details" not in body["error"]
