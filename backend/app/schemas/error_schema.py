from pydantic import Field

from app.schemas.base_schema import BaseResponse, ErrorDetail


class ErrorResponse(BaseResponse):
    success: bool = Field(
        default=False,
        examples=[False],
    )
    error: ErrorDetail = Field(
        ...,
        examples=[
            {
                "message": "Internal Server Error",
                "details": ["A mensagem não pode estar vazia."],
            }
        ],
    )
