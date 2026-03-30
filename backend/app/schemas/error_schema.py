from typing import Optional

from pydantic import Field

from app.schemas.base_schema import BaseResponse, ErrorDetail


class ErrorResponse(BaseResponse):
    success: bool = Field(
        default=False,
        examples=[False],
    )
    request_id: Optional[str] = Field(
        default=None,
        examples=["a1b2c3d4e5f6"],
    )
    error: ErrorDetail = Field(
        ...,
        examples=[
            {
                "code": "APP_000",
                "message": "Internal Server Error",
                "details": ["A mensagem não pode estar vazia."],
            }
        ],
    )
