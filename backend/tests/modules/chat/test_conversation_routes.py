# ========================
# POST /conversations - autenticação
# ========================


class TestConversationAuth:
    def test_no_token_returns_401(self, client):
        response = client.post("/api/v1/conversations")
        assert response.status_code == 401


# ========================
# POST /conversations — sucesso
# ========================


class TestCreateConversationSuccess:
    def test_creates_conversation(self, client, auth_headers):
        response = client.post("/api/v1/conversations", headers=auth_headers)
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

    def test_each_call_creates_different_conversation(self, client, auth_headers):
        r1 = client.post("/api/v1/conversations", headers=auth_headers)
        r2 = client.post("/api/v1/conversations", headers=auth_headers)
        assert r1.json()["data"]["id"] != r2.json()["data"]["id"]


# ========================
# GET /conversations/{id} — autenticação
# ========================


class TestGetConversationAuth:
    def test_no_token_returns_401(self, client):
        response = client.get("/api/v1/conversations/1")
        assert response.status_code == 401


# ========================
# GET /conversations/{id} — sucesso
# ========================


class TestGetConversationSuccess:
    def test_returns_conversation(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
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

    def test_message_count_zero_for_new_conversation(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
        assert response.json()["data"]["message_count"] == 0

    def test_message_count_after_chat(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        client.post(
            "/api/v1/chat",
            json={"message": "Oi", "conversation_id": conv_id},
            headers=auth_headers,
        )

        response = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
        assert response.json()["data"]["message_count"] == 2  # user + bot


# ========================
# GET /conversations/{id} — não encontrada
# ========================


class TestGetConversationNotFound:
    def test_not_found_returns_404(self, client, auth_headers):
        response = client.get("/api/v1/conversations/999", headers=auth_headers)
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]


# ========================
# GET /conversations/{id} — ownership (IDOR)
# ========================


class TestGetConversationOwnership:
    def test_other_user_returns_403(self, client, auth_headers, user2_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}", headers=user2_headers)
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_002"


# ========================
# GET /conversations/{id}/messages — autenticação
# ========================


class TestGetConversationMessagesAuth:
    def test_no_token_returns_401(self, client):
        response = client.get("/api/v1/conversations/1/messages")
        assert response.status_code == 401


# ========================
# GET /conversations/{id}/messages — sucesso
# ========================


def _create_conversation_with_messages(client, auth_headers, msg_count=2):
    """Helper: cria conversa e envia mensagens via /chat."""
    create = client.post("/api/v1/conversations", headers=auth_headers)
    conv_id = create.json()["data"]["id"]
    for i in range(msg_count):
        client.post(
            "/api/v1/chat",
            json={"message": f"Mensagem {i + 1}", "conversation_id": conv_id},
            headers=auth_headers,
        )
    return conv_id


class TestGetConversationMessagesSuccess:
    def test_returns_messages(self, client, auth_headers):
        conv_id = _create_conversation_with_messages(client, auth_headers, msg_count=1)

        response = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["conversation_id"] == conv_id
        assert len(body["data"]["messages"]) == 2  # user + bot
        assert "timestamp" in body

    def test_message_fields(self, client, auth_headers):
        conv_id = _create_conversation_with_messages(client, auth_headers, msg_count=1)

        response = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        msg = response.json()["data"]["messages"][0]
        assert "id" in msg
        assert msg["sender"] == "user"
        assert msg["content"] == "Mensagem 1"
        assert "created_at" in msg

    def test_messages_ordered_by_created_at(self, client, auth_headers):
        conv_id = _create_conversation_with_messages(client, auth_headers, msg_count=2)

        response = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        messages = response.json()["data"]["messages"]
        assert len(messages) == 4
        assert messages[0]["sender"] == "user"
        assert messages[1]["sender"] == "bot"
        assert messages[2]["sender"] == "user"
        assert messages[3]["sender"] == "bot"

    def test_empty_conversation(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["messages"] == []
        assert response.json()["data"]["pagination"]["total"] == 0

    def test_pagination_metadata(self, client, auth_headers):
        conv_id = _create_conversation_with_messages(client, auth_headers, msg_count=1)

        response = client.get(
            f"/api/v1/conversations/{conv_id}/messages?limit=10&offset=0",
            headers=auth_headers,
        )
        pagination = response.json()["data"]["pagination"]
        assert pagination["limit"] == 10
        assert pagination["offset"] == 0
        assert pagination["total"] == 2

    def test_limit_restricts_results(self, client, auth_headers):
        conv_id = _create_conversation_with_messages(client, auth_headers, msg_count=3)

        response = client.get(
            f"/api/v1/conversations/{conv_id}/messages?limit=2",
            headers=auth_headers,
        )
        data = response.json()["data"]
        assert len(data["messages"]) == 2
        assert data["pagination"]["total"] == 6

    def test_offset_skips_results(self, client, auth_headers):
        conv_id = _create_conversation_with_messages(client, auth_headers, msg_count=2)

        response = client.get(
            f"/api/v1/conversations/{conv_id}/messages?limit=50&offset=2",
            headers=auth_headers,
        )
        data = response.json()["data"]
        assert len(data["messages"]) == 2
        assert data["pagination"]["offset"] == 2

    def test_default_limit_is_50(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        assert response.json()["data"]["pagination"]["limit"] == 50


# ========================
# GET /conversations/{id}/messages — não encontrada
# ========================


class TestGetConversationMessagesNotFound:
    def test_not_found_returns_404(self, client, auth_headers):
        response = client.get("/api/v1/conversations/999/messages", headers=auth_headers)
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]


# ========================
# GET /conversations/{id}/messages — validação de query params (422)
# ========================


class TestGetConversationMessagesValidation:
    def test_limit_zero_returns_422(self, client, auth_headers):
        response = client.get("/api/v1/conversations/1/messages?limit=0", headers=auth_headers)
        assert response.status_code == 422

    def test_limit_exceeds_max_returns_422(self, client, auth_headers):
        response = client.get("/api/v1/conversations/1/messages?limit=101", headers=auth_headers)
        assert response.status_code == 422

    def test_negative_offset_returns_422(self, client, auth_headers):
        response = client.get("/api/v1/conversations/1/messages?offset=-1", headers=auth_headers)
        assert response.status_code == 422

    def test_invalid_limit_type_returns_422(self, client, auth_headers):
        response = client.get("/api/v1/conversations/1/messages?limit=abc", headers=auth_headers)
        assert response.status_code == 422


# ========================
# GET /conversations/{id}/messages — ownership (IDOR)
# ========================


class TestGetConversationMessagesOwnership:
    def test_other_user_returns_403(self, client, auth_headers, user2_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.get(
            f"/api/v1/conversations/{conv_id}/messages", headers=user2_headers
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_002"


# ========================
# PATCH /conversations/{id}/close — autenticação
# ========================


class TestCloseConversationAuth:
    def test_no_token_returns_401(self, client):
        response = client.patch("/api/v1/conversations/1/close")
        assert response.status_code == 401


# ========================
# PATCH /conversations/{id}/close — sucesso
# ========================


class TestCloseConversationSuccess:
    def test_closes_conversation(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.patch(f"/api/v1/conversations/{conv_id}/close", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["id"] == conv_id
        assert body["data"]["status"] == "closed"
        assert body["data"]["ended_at"] is not None
        assert "timestamp" in body

    def test_preserves_user_and_company(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.patch(f"/api/v1/conversations/{conv_id}/close", headers=auth_headers)
        data = response.json()["data"]
        assert data["user_id"] == 1
        assert data["company_id"] == 1

    def test_get_after_close_shows_closed(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        client.patch(f"/api/v1/conversations/{conv_id}/close", headers=auth_headers)

        response = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
        data = response.json()["data"]
        assert data["status"] == "closed"
        assert data["ended_at"] is not None


# ========================
# PATCH /conversations/{id}/close — erros
# ========================


class TestCloseConversationErrors:
    def test_not_found_returns_404(self, client, auth_headers):
        response = client.patch("/api/v1/conversations/999/close", headers=auth_headers)
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RES_001"
        assert "999" in body["error"]["message"]

    def test_already_closed_returns_400(self, client, auth_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        client.patch(f"/api/v1/conversations/{conv_id}/close", headers=auth_headers)
        response = client.patch(f"/api/v1/conversations/{conv_id}/close", headers=auth_headers)

        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CHAT_001"
        assert "já está encerrada" in body["error"]["message"]


# ========================
# PATCH /conversations/{id}/close — ownership (IDOR)
# ========================


class TestCloseConversationOwnership:
    def test_other_user_returns_403(self, client, auth_headers, user2_headers):
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        response = client.patch(
            f"/api/v1/conversations/{conv_id}/close", headers=user2_headers
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_002"
