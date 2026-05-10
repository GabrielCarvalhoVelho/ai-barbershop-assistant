from __future__ import annotations

import time


class TestChatE2EFlow:
    def test_send_message_then_list_then_load_history(self, client, auth_headers):
        """Fluxo E2E de chat: enviar mensagem -> listar conversa -> abrir histórico."""
        send = client.post(
            "/api/v1/chat",
            json={"message": "Quero agendar para amanhã às 15h"},
            headers=auth_headers,
        )

        assert send.status_code == 200
        send_body = send.json()
        conversation_id = send_body["data"]["conversation_id"]
        assert conversation_id is not None

        listed = client.get(
            "/api/v1/conversations?limit=10&offset=0",
            headers=auth_headers,
        )
        assert listed.status_code == 200
        listed_body = listed.json()

        conversations = listed_body["data"]["conversations"]
        assert len(conversations) == 1
        assert conversations[0]["id"] == conversation_id
        assert conversations[0]["message_count"] >= 2

        history = client.get(
            f"/api/v1/conversations/{conversation_id}/messages?limit=50&offset=0",
            headers=auth_headers,
        )
        assert history.status_code == 200
        history_body = history.json()
        messages = history_body["data"]["messages"]

        assert len(messages) >= 2
        assert messages[0]["sender"] == "user"
        assert "Quero agendar" in messages[0]["content"]


class TestChatE2ESecurity:
    def test_user2_cannot_access_user1_conversation_history(
        self,
        client,
        auth_headers,
        user2_headers,
    ):
        """User2 não pode abrir histórico de conversa pertencente ao User1."""
        created = client.post(
            "/api/v1/chat",
            json={"message": "Mensagem privada do usuário 1"},
            headers=auth_headers,
        )
        assert created.status_code == 200
        conversation_id = created.json()["data"]["conversation_id"]

        forbidden = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=user2_headers,
        )

        assert forbidden.status_code == 403
        body = forbidden.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AUTH_002"


class TestChatE2EPerformance:
    def test_list_conversations_under_200ms_median(self, client, auth_headers):
        """Valida mediana de latência da listagem de conversas abaixo de 200ms."""
        for _ in range(9):
            created = client.post("/api/v1/conversations", headers=auth_headers)
            assert created.status_code == 201

        samples_ms: list[float] = []

        for _ in range(3):
            start = time.perf_counter()
            response = client.get(
                "/api/v1/conversations?limit=9&offset=0",
                headers=auth_headers,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            samples_ms.append(elapsed_ms)

            assert response.status_code == 200
            body = response.json()
            assert body["data"]["pagination"]["total"] == 9

        median_ms = sorted(samples_ms)[1]
        assert median_ms < 200, f"Latência mediana acima do alvo: {median_ms:.2f}ms"
