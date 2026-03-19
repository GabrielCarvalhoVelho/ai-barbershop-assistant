from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str = Field(
        ...,
        examples=["Internal Server Error"],
    )
