from pydantic import BaseModel, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=1, examples=["+5511999000000"])
    password: str = Field(..., min_length=1, examples=["senha_dev_123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class UserMeResponse(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str
    role: UserRole
    company_id: int

    model_config = {"from_attributes": True}
