from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_role
from app.db.database import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.modules.knowledge.controller import KnowledgeController
from app.modules.knowledge.schemas import (
    CreateKnowledgeDocumentRequest,
    UpdateKnowledgeDocumentRequest,
)
from app.repositories.knowledge_repository import KnowledgeDocumentRepository
from app.schemas.base_schema import SuccessResponse
from app.schemas.error_schema import ErrorResponse

router = APIRouter(prefix="/api/v1/admin/knowledge", tags=["admin - knowledge"])

_SECURITY = {"security": [{"bearerAuth": []}]}
_401 = {"model": ErrorResponse, "description": "Token ausente ou inválido (AUTH_003)"}
_403 = {"model": ErrorResponse, "description": "Acesso negado — requer role ADMIN (AUTH_002)"}
_404 = {"model": ErrorResponse, "description": "Documento não encontrado (RES_001)"}


@router.get(
    "/",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={401: _401, 403: _403},
)
async def list_documents(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    repo = KnowledgeDocumentRepository(session)
    return await KnowledgeController.list_documents(current_user, repo)


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=201,
    openapi_extra=_SECURITY,
    responses={401: _401, 403: _403, 422: {"model": ErrorResponse}},
)
async def create_document(
    body: CreateKnowledgeDocumentRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    repo = KnowledgeDocumentRepository(session)
    return await KnowledgeController.create_document(body, current_user, repo)


@router.patch(
    "/{doc_id}",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={401: _401, 403: _403, 404: _404},
)
async def update_document(
    doc_id: int,
    body: UpdateKnowledgeDocumentRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    repo = KnowledgeDocumentRepository(session)
    return await KnowledgeController.update_document(doc_id, body, current_user, repo)


@router.delete(
    "/{doc_id}",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={401: _401, 403: _403, 404: _404},
)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    repo = KnowledgeDocumentRepository(session)
    return await KnowledgeController.delete_document(doc_id, current_user, repo)
