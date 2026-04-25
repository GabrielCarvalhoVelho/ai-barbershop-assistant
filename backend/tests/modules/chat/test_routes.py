VALID_BODY = {"message": "Quero agendar um corte"}


# ========================
# POST /chat - autenticação
# ========================


class TestChatAuth:
    def test_no_token_returns_401(self, client):
        response = client.post("/api/v1/chat", json=VALID_BODY)
        assert response.status_code == 401


# ========================
# POST /chat - sucesso (nova conversa)
# ========================


class TestChatSuccess:
    def test_valid_message(self, client, auth_headers):
        response = client.post("/api/v1/chat", json=VALID_BODY, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"]["response"], str)
        assert len(body["data"]["response"]) > 0
        assert body["data"]["conversation_id"] is not None
        assert "timestamp" in body

    def test_sanitizes_spaces(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "quero   agendar    corte"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json()["data"]["response"], str)

    def test_creates_new_conversation_each_call(self, client, auth_headers):
        body = {"message": "Oi"}
        r1 = client.post("/api/v1/chat", json=body, headers=auth_headers)
        r2 = client.post("/api/v1/chat", json=body, headers=auth_headers)
        assert r1.json()["data"]["conversation_id"] != r2.json()["data"]["conversation_id"]


# ========================
# POST /chat - conversa existente
# ========================


class TestChatExistingConversation:
    def test_reuses_conversation_id(self, client, auth_headers):
        r1 = client.post("/api/v1/chat", json={"message": "Oi"}, headers=auth_headers)
        conv_id = r1.json()["data"]["conversation_id"]

        r2 = client.post(
            "/api/v1/chat",
            json={"message": "Quero cortar", "conversation_id": conv_id},
            headers=auth_headers,
        )
        assert r2.status_code == 200
        assert r2.json()["data"]["conversation_id"] == conv_id

    def test_not_found_returns_404(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "conversation_id": 999},
            headers=auth_headers,
        )
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"

    def test_closed_conversation_returns_400(self, client, auth_headers):
        r1 = client.post("/api/v1/chat", json={"message": "Oi"}, headers=auth_headers)
        conv_id = r1.json()["data"]["conversation_id"]
        client.patch(f"/api/v1/conversations/{conv_id}/close", headers=auth_headers)

        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi de novo", "conversation_id": conv_id},
            headers=auth_headers,
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "encerrada" in body["error"]["message"]

    def test_messages_persisted_in_conversation(self, client, auth_headers):
        r1 = client.post("/api/v1/chat", json={"message": "Primeira"}, headers=auth_headers)
        conv_id = r1.json()["data"]["conversation_id"]

        client.post(
            "/api/v1/chat",
            json={"message": "Segunda", "conversation_id": conv_id},
            headers=auth_headers,
        )

        response = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        messages = response.json()["data"]["messages"]
        assert len(messages) == 4  # 2 user + 2 bot
        assert messages[0]["sender"] == "user"
        assert messages[0]["content"] == "Primeira"
        assert messages[2]["sender"] == "user"
        assert messages[2]["content"] == "Segunda"


# ========================
# POST /chat - ownership da conversa (IDOR protection)
# ========================


class TestChatConversationOwnership:
    """Testa que um usuário não pode usar a conversa de outro (IDOR protection).

    O conftest.py cria: company 1 + user 1, company 2 + user 2.
    """

    def test_wrong_user_returns_403(self, client, auth_headers, user2_headers):
        # User 1 cria conversa
        r1 = client.post("/api/v1/chat", json={"message": "Oi"}, headers=auth_headers)
        conv_id = r1.json()["data"]["conversation_id"]

        # User 2 tenta usar a conversa do user 1
        response = client.post(
            "/api/v1/chat",
            json={"message": "Invasão", "conversation_id": conv_id},
            headers=user2_headers,
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_002"
        assert "não pertence" in body["error"]["message"]

    def test_correct_ownership_succeeds(self, client, auth_headers):
        r1 = client.post("/api/v1/chat", json={"message": "Oi"}, headers=auth_headers)
        conv_id = r1.json()["data"]["conversation_id"]

        response = client.post(
            "/api/v1/chat",
            json={"message": "Continuando", "conversation_id": conv_id},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["conversation_id"] == conv_id


# ========================
# POST /chat - erro 422 (validação de schema)
# ========================


class TestChatValidation422:
    def test_empty_message(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VAL_001"
        assert body["error"]["message"] == "Erro de validação na mensagem."
        assert "details" in body["error"]
        assert "timestamp" in body

    def test_only_spaces(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "     "},
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "details" in response.json()["error"]

    def test_only_special_chars(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "!!!"},
            headers=auth_headers,
        )
        assert response.status_code == 422
        error = response.json()["error"]
        assert any("letra ou número" in d for d in error["details"])

    def test_single_repeated_char(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "aaaaaaa"},
            headers=auth_headers,
        )
        assert response.status_code == 422
        error = response.json()["error"]
        assert any("repetidos" in d for d in error["details"])

    def test_exceeds_max_length(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "a" * 501},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_missing_message_field(self, client, auth_headers):
        response = client.post("/api/v1/chat", json={}, headers=auth_headers)
        assert response.status_code == 422

    def test_no_details_null_in_response(self, client, auth_headers):
        """Garante que o campo details nunca aparece como null."""
        response = client.post(
            "/api/v1/chat",
            json={"message": ""},
            headers=auth_headers,
        )
        error = response.json()["error"]
        if "details" in error:
            assert error["details"] is not None


# ========================
# POST /chat - erro 400 (regra de negócio)
# ========================


class TestChatBusiness400:
    def test_repeated_chars_spam(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "olha isso aaaaaaaaaa que legal"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "repetitivo" in body["error"]["message"]
        assert "details" not in body["error"]
        assert "timestamp" in body

    def test_repeated_word_spam(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"message": "spam spam spam spam spam"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "repetitivo" in body["error"]["message"]
        assert "details" not in body["error"]


# ========================
# POST /chat - atomicidade transacional
# ========================


class TestChatTransactionAtomicity:
    def test_no_orphan_conversation_on_business_error(self, client, auth_headers):
        """Se o service rejeita a mensagem (spam), a conversa criada deve ser desfeita."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "spam spam spam spam spam"},
            headers=auth_headers,
        )
        assert response.status_code == 400

        r = client.get("/api/v1/conversations/1", headers=auth_headers)
        assert r.status_code == 404

    def test_successful_chat_persists_conversation_and_messages(self, client, auth_headers):
        """Garante que no caso de sucesso, conversa e mensagens são persistidas."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Quero agendar"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        conv_id = response.json()["data"]["conversation_id"]

        r = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
        assert r.status_code == 200

        r = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["data"]["pagination"]["total"] == 2


# ========================
# POST /chat - contexto RAG
# ========================


class TestChatRAGContext:
    def test_chat_with_knowledge_documents(self, client, auth_headers):
        """Company 1 tem documentos — chat funciona com RAG ativo."""
        response = client.post("/api/v1/chat", json=VALID_BODY, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"]["response"], str)

    def test_chat_without_knowledge_documents(self, client, user2_headers):
        """Company 2 não tem documentos — chat funciona sem RAG (graceful)."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Olá"},
            headers=user2_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"]["response"], str)
