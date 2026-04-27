from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DocumentCategory


class KnowledgeDocumentResponse(BaseModel):
    id: int
    company_id: int
    title: str
    content: str
    category: DocumentCategory
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class CreateKnowledgeDocumentRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10)
    category: DocumentCategory


class UpdateKnowledgeDocumentRequest(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    content: str | None = Field(None, min_length=10)
    category: DocumentCategory | None = None
    is_active: bool | None = None
