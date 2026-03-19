from typing import Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str = Field(
        ...,
        examples=["Internal Server Error"],
    )
    details: Optional[list[str]] = Field(
        default=None,
        examples=[["A mensagem não pode estar vazia."]],
    )
