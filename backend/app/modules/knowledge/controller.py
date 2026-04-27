from app.core.exceptions import NotFoundError
from app.modules.knowledge.schemas import (
    CreateKnowledgeDocumentRequest,
    KnowledgeDocumentResponse,
    UpdateKnowledgeDocumentRequest,
)
from app.models.user import User
from app.repositories.knowledge_repository import KnowledgeDocumentRepository
from app.schemas.base_schema import SuccessResponse

_NOT_FOUND = "Documento não encontrado."


class KnowledgeController:
    @staticmethod
    async def list_documents(
        current_user: User,
        repo: KnowledgeDocumentRepository,
    ) -> SuccessResponse:
        docs = await repo.get_all_by_company(current_user.company_id)
        return SuccessResponse(
            data=[KnowledgeDocumentResponse.model_validate(d) for d in docs]
        )

    @staticmethod
    async def create_document(
        body: CreateKnowledgeDocumentRequest,
        current_user: User,
        repo: KnowledgeDocumentRepository,
    ) -> SuccessResponse:
        doc = await repo.create(
            company_id=current_user.company_id,
            title=body.title,
            content=body.content,
            category=body.category,
        )
        return SuccessResponse(data=KnowledgeDocumentResponse.model_validate(doc))

    @staticmethod
    async def update_document(
        doc_id: int,
        body: UpdateKnowledgeDocumentRequest,
        current_user: User,
        repo: KnowledgeDocumentRepository,
    ) -> SuccessResponse:
        doc = await repo.get_by_id(doc_id, current_user.company_id)
        if doc is None:
            raise NotFoundError(message=_NOT_FOUND)
        updated = await repo.update(
            doc_id, current_user.company_id, **body.model_dump(exclude_none=True)
        )
        return SuccessResponse(data=KnowledgeDocumentResponse.model_validate(updated))

    @staticmethod
    async def delete_document(
        doc_id: int,
        current_user: User,
        repo: KnowledgeDocumentRepository,
    ) -> SuccessResponse:
        doc = await repo.get_by_id(doc_id, current_user.company_id)
        if doc is None:
            raise NotFoundError(message=_NOT_FOUND)
        await repo.deactivate(doc_id, current_user.company_id)
        return SuccessResponse(data={"message": "Documento desativado."})
