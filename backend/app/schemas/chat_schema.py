from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        strip_whitespace=True,
        examples=["Quais serviços vocês oferecem?"],
    )


class ChatResponse(BaseModel):
    response: str = Field(
        ...,
        examples=["Olá! Oferecemos corte, barba e sobrancelha. Deseja agendar?"],
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
    )