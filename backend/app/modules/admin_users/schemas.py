from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import UserRole
from app.modules.chat.schemas import PaginationResponse


class UserListItemResponse(BaseModel):
    id: int
    company_id: int
    name: str
    phone: str
    email: str | None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserListItemResponse]
    pagination: PaginationResponse


class UpdateUserRoleRequest(BaseModel):
    role: UserRole = Field(..., examples=["admin"])


class UpdateUserActiveRequest(BaseModel):
    is_active: bool = Field(..., examples=[False])
