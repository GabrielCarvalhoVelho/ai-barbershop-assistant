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
