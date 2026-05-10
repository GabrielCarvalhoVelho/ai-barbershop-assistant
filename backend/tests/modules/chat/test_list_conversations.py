# ========================
# GET /conversations - autenticação
# ========================


class TestListConversationsAuth:
    def test_no_token_returns_401(self, client):
        response = client.get("/api/v1/conversations")
        assert response.status_code == 401


# ========================
# GET /conversations — sucesso
# ========================


class TestListConversationsSuccess:
    def test_list_empty_conversations(self, client, auth_headers):
        """Novo user sem conversa retorna lista vazia."""
        response = client.get("/api/v1/conversations", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert len(body["data"]["conversations"]) == 0
        assert body["data"]["pagination"]["total"] == 0
        assert body["data"]["pagination"]["limit"] == 10
        assert body["data"]["pagination"]["offset"] == 0
        assert "timestamp" in body

    def test_list_conversations_with_data(self, client, auth_headers):
        """Cria 3 conversas e lista-as."""
        # Cria 3 conversas
        ids = []
        for _ in range(3):
            create = client.post("/api/v1/conversations", headers=auth_headers)
            ids.append(create.json()["data"]["id"])

        response = client.get("/api/v1/conversations", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]["conversations"]) == 3
        assert body["data"]["pagination"]["total"] == 3

        # Verifica que cada conversa tem os campos esperados
        for conv in body["data"]["conversations"]:
            assert "id" in conv
            assert "status" in conv
            assert conv["status"] == "active"
            assert "started_at" in conv
            assert "ended_at" in conv
            assert "message_count" in conv
            assert conv["message_count"] == 0
            assert "last_message_preview" in conv
            assert conv["last_message_preview"] is None

    def test_list_conversations_ordered_by_started_at_desc(self, client, auth_headers):
        """Conversas são listadas em ordem decrescente de started_at (mais recentes primeiro)."""
        # Cria 3 conversas
        id1 = client.post("/api/v1/conversations", headers=auth_headers).json()[
            "data"
        ]["id"]
        id2 = client.post("/api/v1/conversations", headers=auth_headers).json()[
            "data"
        ]["id"]
        id3 = client.post("/api/v1/conversations", headers=auth_headers).json()[
            "data"
        ]["id"]

        response = client.get("/api/v1/conversations", headers=auth_headers)
        body = response.json()
        returned_ids = [c["id"] for c in body["data"]["conversations"]]

        # Mais recentes primeiro
        assert returned_ids == [id3, id2, id1]

    def test_last_message_preview_with_messages(self, client, auth_headers):
        """Conversa com mensagens mostra preview da última mensagem."""
        create = client.post("/api/v1/conversations", headers=auth_headers)
        conv_id = create.json()["data"]["id"]

        # Envia mensagem
        client.post(
            "/api/v1/chat",
            json={"message": "Quero agendar um corte de cabelo", "conversation_id": conv_id},
            headers=auth_headers,
        )

        response = client.get("/api/v1/conversations", headers=auth_headers)
        body = response.json()
        assert len(body["data"]["conversations"]) == 1
        conv = body["data"]["conversations"][0]
        assert conv["message_count"] == 2  # user + bot
        assert conv["last_message_preview"] is not None
        assert isinstance(conv["last_message_preview"], str)


# ========================
# GET /conversations — paginação
# ========================


class TestListConversationsPagination:
    def test_pagination_limit_and_offset(self, client, auth_headers):
        """Testa limit e offset na paginação."""
        # Cria 9 conversas (respeita rate limit de 10/min)
        for _ in range(9):
            client.post("/api/v1/conversations", headers=auth_headers)

        # Primeira página: limit=5, offset=0
        response = client.get(
            "/api/v1/conversations?limit=5&offset=0", headers=auth_headers
        )
        body = response.json()
        assert len(body["data"]["conversations"]) == 5
        assert body["data"]["pagination"]["total"] == 9
        assert body["data"]["pagination"]["limit"] == 5
        assert body["data"]["pagination"]["offset"] == 0

        # Segunda página: limit=5, offset=5
        response = client.get(
            "/api/v1/conversations?limit=5&offset=5", headers=auth_headers
        )
        body = response.json()
        assert len(body["data"]["conversations"]) == 4
        assert body["data"]["pagination"]["total"] == 9
        assert body["data"]["pagination"]["limit"] == 5
        assert body["data"]["pagination"]["offset"] == 5

    def test_pagination_limit_max_50(self, client, auth_headers):
        """Limit máximo é 50."""
        # Tenta limit=100, API deve aceitar como inválido
        response = client.get(
            "/api/v1/conversations?limit=100", headers=auth_headers
        )
        assert response.status_code == 422

    def test_pagination_default_limit_10(self, client, auth_headers):
        """Limite padrão é 10 se não especificado."""
        # Cria 9 conversas (respeita rate limit de 10/min)
        for _ in range(9):
            client.post("/api/v1/conversations", headers=auth_headers)

        response = client.get("/api/v1/conversations", headers=auth_headers)
        body = response.json()
        assert body["data"]["pagination"]["limit"] == 10
        assert len(body["data"]["conversations"]) == 9


# ========================
# GET /conversations — isolamento de dados
# ========================


class TestListConversationsIsolation:
    def test_user1_does_not_see_user2_conversations(self, client, auth_headers, user2_headers):
        """User1 não vê conversas de User2."""
        # User1 cria 3 conversas
        for _ in range(3):
            client.post("/api/v1/conversations", headers=auth_headers)

        # User2 lista conversas — deve estar vazio
        response = client.get("/api/v1/conversations", headers=user2_headers)
        body = response.json()
        assert len(body["data"]["conversations"]) == 0
        assert body["data"]["pagination"]["total"] == 0

    def test_user1_sees_only_own_conversations(self, client, auth_headers, user2_headers):
        """Mesmo com múltiplos users, cada um vê apenas as próprias conversas."""
        # User1 cria 2 conversas
        for _ in range(2):
            client.post("/api/v1/conversations", headers=auth_headers)

        # User2 cria 3 conversas
        for _ in range(3):
            client.post("/api/v1/conversations", headers=user2_headers)

        # User1 lista — deve ver 2
        response = client.get("/api/v1/conversations", headers=auth_headers)
        body = response.json()
        assert body["data"]["pagination"]["total"] == 2

        # User2 lista — deve ver 3
        response = client.get("/api/v1/conversations", headers=user2_headers)
        body = response.json()
        assert body["data"]["pagination"]["total"] == 3


# ========================
# GET /conversations — validação
# ========================


class TestListConversationsValidation:
    def test_invalid_limit_negative(self, client, auth_headers):
        """Limit negativo retorna 422."""
        response = client.get("/api/v1/conversations?limit=-1", headers=auth_headers)
        assert response.status_code == 422

    def test_invalid_offset_negative(self, client, auth_headers):
        """Offset negativo retorna 422."""
        response = client.get("/api/v1/conversations?offset=-1", headers=auth_headers)
        assert response.status_code == 422

    def test_invalid_limit_zero(self, client, auth_headers):
        """Limit zero retorna 422."""
        response = client.get("/api/v1/conversations?limit=0", headers=auth_headers)
        assert response.status_code == 422
