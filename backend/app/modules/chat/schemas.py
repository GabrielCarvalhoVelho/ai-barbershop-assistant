import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ConversationStatus, MessageSender

_ONLY_SPECIAL_CHARS = re.compile(r"[^\w\s]+")
_SINGLE_REPEATED_CHAR = re.compile(r"(.)\1+")


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        examples=["Quais serviços vocês oferecem?"],
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


class ChatResponse(BaseModel):
    response: str = Field(
        ...,
        examples=["Olá! Oferecemos corte, barba e sobrancelha. Deseja agendar?"],
    )
    conversation_id: int = Field(..., examples=[1])


# ========================
# Message
# ========================


class MessageResponse(BaseModel):
    id: int = Field(..., examples=[1])
    sender: MessageSender = Field(..., examples=["user"])
    content: str = Field(..., examples=["Quero agendar um corte"])
    created_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])


# ========================
# Conversation
# ========================


class ConversationSummaryResponse(BaseModel):
    """Resposta de criação e encerramento de conversa (sem message_count)."""

    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[1])
    company_id: int = Field(..., examples=[1])
    status: ConversationStatus = Field(..., examples=["active"])
    started_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])
    ended_at: datetime | None = Field(None, examples=[None])


class ConversationResponse(BaseModel):
    """Resposta de detalhes de conversa (com message_count)."""

    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[1])
    company_id: int = Field(..., examples=[1])
    status: ConversationStatus = Field(..., examples=["active"])
    started_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])
    ended_at: datetime | None = Field(None, examples=[None])
    message_count: int = Field(..., examples=[5])


class ConversationDetailResponse(BaseModel):
    id: int = Field(..., examples=[1])
    status: ConversationStatus = Field(..., examples=["active"])
    started_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])
    ended_at: datetime | None = Field(None, examples=[None])
    messages: list[MessageResponse] = Field(..., examples=[[]])


class PaginationResponse(BaseModel):
    limit: int = Field(..., examples=[50])
    offset: int = Field(..., examples=[0])
    total: int = Field(..., examples=[10])


class ConversationMessagesResponse(BaseModel):
    """Resposta paginada de mensagens de uma conversa."""

    conversation_id: int = Field(..., examples=[1])
    messages: list[MessageResponse] = Field(..., examples=[[]])
    pagination: PaginationResponse


# ========================
# Conversation List
# ========================


class ConversationListItemResponse(BaseModel):
    """Item individual na lista de conversas do usuário."""

    id: int = Field(..., examples=[1])
    status: ConversationStatus = Field(..., examples=["active"])
    started_at: datetime = Field(..., examples=["2026-03-30T14:00:00Z"])
    ended_at: datetime | None = Field(None, examples=[None])
    message_count: int = Field(..., examples=[5])
    last_message_preview: str | None = Field(
        None,
        description="Primeiros 100 caracteres da última mensagem",
        examples=["Olá! Oferecemos corte, barba e sobrancelha..."],
    )


class ConversationListPaginatedResponse(BaseModel):
    """Resposta paginada com lista de conversas do usuário."""

    conversations: list[ConversationListItemResponse] = Field(..., examples=[[]])
    pagination: PaginationResponse
