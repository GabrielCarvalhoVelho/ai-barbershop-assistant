import re
from datetime import datetime

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
    # TODO: user_id e company_id serão extraídos do token JWT
    # quando a task de autenticação + dashboard for implementada.
    # Por ora, são enviados explicitamente no body.
    user_id: int = Field(
        ...,
        gt=0,
        description="ID do usuário que está enviando a mensagem. (Temporário — será extraído do token JWT na task de autenticação.)",
        examples=[1],
    )
    company_id: int = Field(
        ...,
        gt=0,
        description="ID da barbearia à qual a mensagem se destina. (Temporário — será extraído do token JWT na task de autenticação.)",
        examples=[1],
    )
    conversation_id: int | None = Field(
        default=None,
        description="ID de uma conversa existente. Se omitido, uma nova conversa é criada.",
        examples=[1],
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


class CreateConversationRequest(BaseModel):
    user_id: int = Field(
        ...,
        gt=0,
        description="ID do usuário proprietário da conversa.",
        examples=[1],
    )
    company_id: int = Field(
        ...,
        gt=0,
        description="ID da barbearia à qual a conversa pertence.",
        examples=[1],
    )


class ChatResponse(BaseModel):
    response: str = Field(
        ...,
        examples=["Olá! Oferecemos corte, barba e sobrancelha. Deseja agendar?"],
    )


# ========================
# Message
# ========================


class MessageResponse(BaseModel):
    id: int = Field(..., examples=[1])
    sender: str = Field(..., examples=["user"])
    content: str = Field(..., examples=["Quero agendar um corte"])
    created_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])


# ========================
# Conversation
# ========================


class ConversationResponse(BaseModel):
    id: int = Field(..., examples=[1])
    status: str = Field(..., examples=["active"])
    started_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])
    ended_at: datetime | None = Field(None, examples=[None])
    message_count: int = Field(..., examples=[5])


class ConversationDetailResponse(BaseModel):
    id: int = Field(..., examples=[1])
    status: str = Field(..., examples=["active"])
    started_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])
    ended_at: datetime | None = Field(None, examples=[None])
    messages: list[MessageResponse] = Field(..., examples=[[]])
