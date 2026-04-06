VALID_BODY = {"message": "Quero agendar um corte", "user_id": 1, "company_id": 1}


# ========================
# POST /chat - sucesso (nova conversa)
# ========================


class TestChatSuccess:
    def test_valid_message(self, client):
        response = client.post("/api/v1/chat", json=VALID_BODY)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"]["response"], str)
        assert len(body["data"]["response"]) > 0
        assert body["data"]["conversation_id"] is not None
        assert "timestamp" in body

    def test_sanitizes_spaces(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "quero   agendar    corte", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 200
        assert isinstance(response.json()["data"]["response"], str)

    def test_creates_new_conversation_each_call(self, client):
        body = {"message": "Oi", "user_id": 1, "company_id": 1}
        r1 = client.post("/api/v1/chat", json=body)
        r2 = client.post("/api/v1/chat", json=body)
        assert r1.json()["data"]["conversation_id"] != r2.json()["data"]["conversation_id"]


# ========================
# POST /chat - conversa existente
# ========================


class TestChatExistingConversation:
    def test_reuses_conversation_id(self, client):
        body = {"message": "Oi", "user_id": 1, "company_id": 1}
        r1 = client.post("/api/v1/chat", json=body)
        conv_id = r1.json()["data"]["conversation_id"]

        r2 = client.post(
            "/api/v1/chat",
            json={"message": "Quero cortar", "user_id": 1, "company_id": 1, "conversation_id": conv_id},
        )
        assert r2.status_code == 200
        assert r2.json()["data"]["conversation_id"] == conv_id

    def test_not_found_returns_404(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": 1, "company_id": 1, "conversation_id": 999},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"

    def test_closed_conversation_returns_400(self, client):
        # Cria conversa e encerra
        r1 = client.post("/api/v1/chat", json={"message": "Oi", "user_id": 1, "company_id": 1})
        conv_id = r1.json()["data"]["conversation_id"]
        client.patch(f"/api/v1/conversations/{conv_id}/close")

        # Tenta enviar mensagem na conversa encerrada
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi de novo", "user_id": 1, "company_id": 1, "conversation_id": conv_id},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "encerrada" in body["error"]["message"]

    def test_messages_persisted_in_conversation(self, client):
        # Cria conversa via chat
        r1 = client.post("/api/v1/chat", json={"message": "Primeira", "user_id": 1, "company_id": 1})
        conv_id = r1.json()["data"]["conversation_id"]

        # Envia segunda mensagem na mesma conversa
        client.post(
            "/api/v1/chat",
            json={"message": "Segunda", "user_id": 1, "company_id": 1, "conversation_id": conv_id},
        )

        # Verifica via endpoint de mensagens
        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
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

    def test_wrong_user_returns_403(self, client):
        # User 1 cria conversa na company 1
        r1 = client.post("/api/v1/chat", json={"message": "Oi", "user_id": 1, "company_id": 1})
        conv_id = r1.json()["data"]["conversation_id"]

        # User 2 tenta usar a conversa do user 1
        response = client.post(
            "/api/v1/chat",
            json={"message": "Invasão", "user_id": 2, "company_id": 1, "conversation_id": conv_id},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_002"
        assert "não pertence" in body["error"]["message"]

    def test_wrong_company_returns_403(self, client):
        # User 1 cria conversa na company 1
        r1 = client.post("/api/v1/chat", json={"message": "Oi", "user_id": 1, "company_id": 1})
        conv_id = r1.json()["data"]["conversation_id"]

        # Mesmo user, mas tenta com company diferente
        response = client.post(
            "/api/v1/chat",
            json={"message": "Invasão", "user_id": 1, "company_id": 2, "conversation_id": conv_id},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_002"
        assert "não pertence" in body["error"]["message"]

    def test_correct_ownership_succeeds(self, client):
        # User 1 cria conversa
        r1 = client.post("/api/v1/chat", json={"message": "Oi", "user_id": 1, "company_id": 1})
        conv_id = r1.json()["data"]["conversation_id"]

        # Mesmo user e company reutiliza normalmente
        response = client.post(
            "/api/v1/chat",
            json={"message": "Continuando", "user_id": 1, "company_id": 1, "conversation_id": conv_id},
        )
        assert response.status_code == 200
        assert response.json()["data"]["conversation_id"] == conv_id


# ========================
# POST /chat - user/company não encontrados no banco
# ========================


class TestChatUserCompanyNotFound:
    def test_user_not_found_returns_404(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": 999, "company_id": 1},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]

    def test_company_not_found_returns_404(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": 1, "company_id": 888},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "888" in body["error"]["message"]


# ========================
# POST /chat - validação de user_id e company_id
# ========================


class TestChatUserCompanyValidation:
    def test_missing_user_id_returns_422(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "company_id": 1},
        )
        assert response.status_code == 422

    def test_missing_company_id_returns_422(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": 1},
        )
        assert response.status_code == 422

    def test_zero_user_id_returns_422(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": 0, "company_id": 1},
        )
        assert response.status_code == 422

    def test_negative_company_id_returns_422(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": 1, "company_id": -1},
        )
        assert response.status_code == 422

    def test_invalid_type_user_id_returns_422(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": "abc", "company_id": 1},
        )
        assert response.status_code == 422


# ========================
# POST /chat - erro 422 (validação de schema)
# ========================


class TestChatValidation422:
    def test_empty_message(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VAL_001"
        assert body["error"]["message"] == "Erro de validação na mensagem."
        assert "details" in body["error"]
        assert "timestamp" in body

    def test_only_spaces(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "     ", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 422
        assert "details" in response.json()["error"]

    def test_only_special_chars(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "!!!", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 422
        error = response.json()["error"]
        assert any("letra ou número" in d for d in error["details"])

    def test_single_repeated_char(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "aaaaaaa", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 422
        error = response.json()["error"]
        assert any("repetidos" in d for d in error["details"])

    def test_exceeds_max_length(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "a" * 501, "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 422

    def test_missing_message_field(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"user_id": 1, "company_id": 1},
        )
        assert response.status_code == 422

    def test_no_details_null_in_response(self, client):
        """Garante que o campo details nunca aparece como null."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "", "user_id": 1, "company_id": 1},
        )
        error = response.json()["error"]
        if "details" in error:
            assert error["details"] is not None


# ========================
# POST /chat - erro 400 (regra de negócio)
# ========================


class TestChatBusiness400:
    def test_repeated_chars_spam(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "olha isso aaaaaaaaaa que legal", "user_id": 1, "company_id": 1},
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
            "/api/v1/chat",
            json={"message": "spam spam spam spam spam", "user_id": 1, "company_id": 1},
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
    def test_no_orphan_conversation_on_business_error(self, client):
        """Se o service rejeita a mensagem (spam), a conversa criada deve ser desfeita.

        Fluxo: controller cria conversa → service.generate_response lança BusinessError
        → transação faz rollback → conversa não persiste.
        """
        # Envia spam — conversation é criada internamente, mas generate_response falha
        response = client.post(
            "/api/v1/chat",
            json={"message": "spam spam spam spam spam", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 400

        # Se a transação fosse commitada antes do erro, a conversa ficaria órfã.
        # Com Unit of Work, o rollback desfaz tudo. Verifica que nenhuma conversa existe.
        r = client.get("/api/v1/conversations/1")
        assert r.status_code == 404

    def test_successful_chat_persists_conversation_and_messages(self, client):
        """Garante que no caso de sucesso, conversa e mensagens são persistidas."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Quero agendar", "user_id": 1, "company_id": 1},
        )
        assert response.status_code == 200
        conv_id = response.json()["data"]["conversation_id"]

        # Conversa existe
        r = client.get(f"/api/v1/conversations/{conv_id}")
        assert r.status_code == 200

        # Mensagens existem
        r = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert r.status_code == 200
        assert r.json()["data"]["pagination"]["total"] == 2
