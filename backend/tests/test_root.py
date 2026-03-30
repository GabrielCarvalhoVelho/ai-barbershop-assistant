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
