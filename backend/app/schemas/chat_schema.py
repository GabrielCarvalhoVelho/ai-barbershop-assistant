import re
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

_ONLY_SPECIAL_CHARS = re.compile(r"[^\w\s]+")
_SINGLE_REPEATED_CHAR = re.compile(r"(.)\1+")


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        examples=["Quais serviços vocês oferecem?"],
    )

    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, v: str) -> str:
        v = v.strip()

        if not v:
            raise ValueError("A mensagem não pode estar vazia.")

        if _ONLY_SPECIAL_CHARS.fullmatch(v):
            raise ValueError(
                "A mensagem deve conter pelo menos uma letra ou número."
            )

        if _SINGLE_REPEATED_CHAR.fullmatch(v):
            raise ValueError(
                "A mensagem não pode conter apenas caracteres repetidos."
            )

        return v


class ChatResponse(BaseModel):
    response: str = Field(
        ...,
        examples=["Olá! Oferecemos corte, barba e sobrancelha. Deseja agendar?"],
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )