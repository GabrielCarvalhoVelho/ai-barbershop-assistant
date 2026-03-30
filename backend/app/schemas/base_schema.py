from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    success: bool = Field(
        ...,
        examples=[True],
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        examples=["2026-03-26T15:30:00Z"],
    )


class SuccessResponse(BaseResponse):
    success: bool = Field(
        default=True,
        examples=[True],
    )
    data: Any = Field(
        ...,
        examples=[{"message": "API is running"}],
    )


class ErrorDetail(BaseModel):
    code: str = Field(
        ...,
        examples=["CHAT_001"],
    )
    message: str = Field(
        ...,
        examples=["Erro de validação na mensagem."],
    )
    field: Optional[str] = Field(
        default=None,
        examples=["message"],
    )
    details: Optional[list[str]] = Field(
        default=None,
        examples=[["A mensagem não pode estar vazia."]],
    )
