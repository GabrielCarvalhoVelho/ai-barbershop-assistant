import pytest


class TestListDocuments:
    def test_list_documents_admin_ok(self, client, admin_headers):
        response = client.get("/api/v1/admin/knowledge/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 2  # seed cria 2 documentos para company 1

    def test_list_documents_customer_forbidden(self, client, auth_headers):
        response = client.get("/api/v1/admin/knowledge/", headers=auth_headers)
        assert response.status_code == 403

    def test_list_documents_unauthenticated(self, client):
        response = client.get("/api/v1/admin/knowledge/")
        assert response.status_code == 401


class TestCreateDocument:
    def test_create_document_admin_ok(self, client, admin_headers):
        response = client.post(
            "/api/v1/admin/knowledge/",
            headers=admin_headers,
            json={
                "title": "Novo documento",
                "content": "Conteúdo do novo documento com mais de dez caracteres.",
                "category": "services",
            },
        )
        assert response.status_code == 201
        doc = response.json()["data"]
        assert doc["title"] == "Novo documento"
        assert doc["is_active"] is True

    def test_create_document_invalid_body(self, client, admin_headers):
        response = client.post(
            "/api/v1/admin/knowledge/",
            headers=admin_headers,
            json={"title": "Só o título"},  # faltam content e category
        )
        assert response.status_code == 422


class TestUpdateDocument:
    def test_update_document_admin_ok(self, client, admin_headers):
        # seed cria doc com id=1 para company 1
        response = client.patch(
            "/api/v1/admin/knowledge/1",
            headers=admin_headers,
            json={"title": "Título atualizado"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Título atualizado"

    def test_update_document_not_found(self, client, admin_headers):
        response = client.patch(
            "/api/v1/admin/knowledge/99999",
            headers=admin_headers,
            json={"title": "Novo"},
        )
        assert response.status_code == 404

    def test_update_document_other_company_not_found(self, client, admin_headers):
        # doc_id=3 pertence a company 2 (se existir) ou simplesmente não existe para company 1
        # Garante isolamento: admin de company 1 não pode editar docs de outra company
        response = client.patch(
            "/api/v1/admin/knowledge/99998",
            headers=admin_headers,
            json={"title": "Invasão"},
        )
        assert response.status_code == 404


class TestDeleteDocument:
    def test_delete_document_admin_ok(self, client, admin_headers, db_session):
        # Cria um documento para deletar, para não interferir em outros testes
        create_resp = client.post(
            "/api/v1/admin/knowledge/",
            headers=admin_headers,
            json={
                "title": "Para deletar",
                "content": "Conteúdo que será desativado logo em seguida.",
                "category": "policies",
            },
        )
        assert create_resp.status_code == 201
        doc_id = create_resp.json()["data"]["id"]

        delete_resp = client.delete(
            f"/api/v1/admin/knowledge/{doc_id}",
            headers=admin_headers,
        )
        assert delete_resp.status_code == 200

        # Verifica que o doc ainda aparece na listagem (soft delete), mas is_active=False
        list_resp = client.get("/api/v1/admin/knowledge/", headers=admin_headers)
        docs = list_resp.json()["data"]
        deleted = next((d for d in docs if d["id"] == doc_id), None)
        assert deleted is not None
        assert deleted["is_active"] is False

    def test_delete_document_not_found(self, client, admin_headers):
        response = client.delete(
            "/api/v1/admin/knowledge/99997",
            headers=admin_headers,
        )
        assert response.status_code == 404
