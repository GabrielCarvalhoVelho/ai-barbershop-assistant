VALID_BODY = {"user_id": 1, "company_id": 1}


# ========================
# POST /conversations — sucesso
# ========================


class TestCreateConversationSuccess:
    def test_creates_conversation(self, client):
        response = client.post("/api/v1/conversations", json=VALID_BODY)
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["id"] is not None
        assert body["data"]["user_id"] == 1
        assert body["data"]["company_id"] == 1
        assert body["data"]["status"] == "active"
        assert body["data"]["started_at"] is not None
        assert body["data"]["ended_at"] is None
        assert "timestamp" in body

    def test_each_call_creates_different_conversation(self, client):
        r1 = client.post("/api/v1/conversations", json=VALID_BODY)
        r2 = client.post("/api/v1/conversations", json=VALID_BODY)
        assert r1.json()["data"]["id"] != r2.json()["data"]["id"]


# ========================
# POST /conversations — user/company não encontrados
# ========================


class TestCreateConversationNotFound:
    def test_user_not_found_returns_404(self, client):
        response = client.post(
            "/api/v1/conversations",
            json={"user_id": 999, "company_id": 1},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]

    def test_company_not_found_returns_404(self, client):
        response = client.post(
            "/api/v1/conversations",
            json={"user_id": 1, "company_id": 888},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "888" in body["error"]["message"]


# ========================
# POST /conversations — validação de schema (422)
# ========================


class TestCreateConversationValidation:
    def test_missing_user_id_returns_422(self, client):
        response = client.post(
            "/api/v1/conversations",
            json={"company_id": 1},
        )
        assert response.status_code == 422

    def test_missing_company_id_returns_422(self, client):
        response = client.post(
            "/api/v1/conversations",
            json={"user_id": 1},
        )
        assert response.status_code == 422

    def test_zero_user_id_returns_422(self, client):
        response = client.post(
            "/api/v1/conversations",
            json={"user_id": 0, "company_id": 1},
        )
        assert response.status_code == 422

    def test_negative_company_id_returns_422(self, client):
        response = client.post(
            "/api/v1/conversations",
            json={"user_id": 1, "company_id": -1},
        )
        assert response.status_code == 422

    def test_invalid_type_user_id_returns_422(self, client):
        response = client.post(
            "/api/v1/conversations",
            json={"user_id": "abc", "company_id": 1},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client):
        response = client.post("/api/v1/conversations", json={})
        assert response.status_code == 422


# ========================
# GET /conversations/{id} — sucesso
# ========================


class TestGetConversationSuccess:
    def test_returns_conversation(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["id"] == conv_id
        assert body["data"]["user_id"] == 1
        assert body["data"]["company_id"] == 1
        assert body["data"]["status"] == "active"
        assert body["data"]["started_at"] is not None
        assert body["data"]["ended_at"] is None
        assert "timestamp" in body

    def test_message_count_zero_for_new_conversation(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}")
        assert response.json()["data"]["message_count"] == 0

    def test_message_count_after_chat(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        client.post(
            "/api/v1/chat",
            json={"message": "Oi", "user_id": 1, "company_id": 1, "conversation_id": conv_id},
        )

        response = client.get(f"/api/v1/conversations/{conv_id}")
        assert response.json()["data"]["message_count"] == 2  # user + bot


# ========================
# GET /conversations/{id} — não encontrada
# ========================


class TestGetConversationNotFound:
    def test_not_found_returns_404(self, client):
        response = client.get("/api/v1/conversations/999")
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]


# ========================
# GET /conversations/{id}/messages — sucesso
# ========================


def _create_conversation_with_messages(client, msg_count=2):
    """Helper: cria conversa e envia mensagens via /chat."""
    create = client.post("/api/v1/conversations", json=VALID_BODY)
    conv_id = create.json()["data"]["id"]
    for i in range(msg_count):
        client.post(
            "/api/v1/chat",
            json={
                "message": f"Mensagem {i + 1}",
                "user_id": 1,
                "company_id": 1,
                "conversation_id": conv_id,
            },
        )
    return conv_id


class TestGetConversationMessagesSuccess:
    def test_returns_messages(self, client):
        conv_id = _create_conversation_with_messages(client, msg_count=1)

        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["conversation_id"] == conv_id
        assert len(body["data"]["messages"]) == 2  # user + bot
        assert "timestamp" in body

    def test_message_fields(self, client):
        conv_id = _create_conversation_with_messages(client, msg_count=1)

        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        msg = response.json()["data"]["messages"][0]
        assert "id" in msg
        assert msg["sender"] == "user"
        assert msg["content"] == "Mensagem 1"
        assert "created_at" in msg

    def test_messages_ordered_by_created_at(self, client):
        conv_id = _create_conversation_with_messages(client, msg_count=2)

        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        messages = response.json()["data"]["messages"]
        # 4 mensagens: user1, bot1, user2, bot2
        assert len(messages) == 4
        assert messages[0]["sender"] == "user"
        assert messages[1]["sender"] == "bot"
        assert messages[2]["sender"] == "user"
        assert messages[3]["sender"] == "bot"

    def test_empty_conversation(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.status_code == 200
        assert response.json()["data"]["messages"] == []
        assert response.json()["data"]["pagination"]["total"] == 0

    def test_pagination_metadata(self, client):
        conv_id = _create_conversation_with_messages(client, msg_count=1)

        response = client.get(
            f"/api/v1/conversations/{conv_id}/messages?limit=10&offset=0"
        )
        pagination = response.json()["data"]["pagination"]
        assert pagination["limit"] == 10
        assert pagination["offset"] == 0
        assert pagination["total"] == 2

    def test_limit_restricts_results(self, client):
        conv_id = _create_conversation_with_messages(client, msg_count=3)
        # 6 mensagens no total (3 user + 3 bot)

        response = client.get(
            f"/api/v1/conversations/{conv_id}/messages?limit=2"
        )
        data = response.json()["data"]
        assert len(data["messages"]) == 2
        assert data["pagination"]["total"] == 6

    def test_offset_skips_results(self, client):
        conv_id = _create_conversation_with_messages(client, msg_count=2)
        # 4 mensagens: user1, bot1, user2, bot2

        response = client.get(
            f"/api/v1/conversations/{conv_id}/messages?limit=50&offset=2"
        )
        data = response.json()["data"]
        assert len(data["messages"]) == 2
        assert data["pagination"]["offset"] == 2

    def test_default_limit_is_50(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert response.json()["data"]["pagination"]["limit"] == 50


# ========================
# GET /conversations/{id}/messages — não encontrada
# ========================


class TestGetConversationMessagesNotFound:
    def test_not_found_returns_404(self, client):
        response = client.get("/api/v1/conversations/999/messages")
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]


# ========================
# GET /conversations/{id}/messages — validação de query params (422)
# ========================


class TestGetConversationMessagesValidation:
    def test_limit_zero_returns_422(self, client):
        response = client.get("/api/v1/conversations/1/messages?limit=0")
        assert response.status_code == 422

    def test_limit_exceeds_max_returns_422(self, client):
        response = client.get("/api/v1/conversations/1/messages?limit=101")
        assert response.status_code == 422

    def test_negative_offset_returns_422(self, client):
        response = client.get("/api/v1/conversations/1/messages?offset=-1")
        assert response.status_code == 422

    def test_invalid_limit_type_returns_422(self, client):
        response = client.get("/api/v1/conversations/1/messages?limit=abc")
        assert response.status_code == 422


# ========================
# PATCH /conversations/{id}/close — sucesso
# ========================


class TestCloseConversationSuccess:
    def test_closes_conversation(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        response = client.patch(f"/api/v1/conversations/{conv_id}/close")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["id"] == conv_id
        assert body["data"]["status"] == "closed"
        assert body["data"]["ended_at"] is not None
        assert "timestamp" in body

    def test_preserves_user_and_company(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        response = client.patch(f"/api/v1/conversations/{conv_id}/close")
        data = response.json()["data"]
        assert data["user_id"] == 1
        assert data["company_id"] == 1

    def test_get_after_close_shows_closed(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        client.patch(f"/api/v1/conversations/{conv_id}/close")

        response = client.get(f"/api/v1/conversations/{conv_id}")
        data = response.json()["data"]
        assert data["status"] == "closed"
        assert data["ended_at"] is not None


# ========================
# PATCH /conversations/{id}/close — erros
# ========================


class TestCloseConversationErrors:
    def test_not_found_returns_404(self, client):
        response = client.patch("/api/v1/conversations/999/close")
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]

    def test_already_closed_returns_400(self, client):
        create = client.post("/api/v1/conversations", json=VALID_BODY)
        conv_id = create.json()["data"]["id"]

        client.patch(f"/api/v1/conversations/{conv_id}/close")
        response = client.patch(f"/api/v1/conversations/{conv_id}/close")

        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "já está encerrada" in body["error"]["message"]
