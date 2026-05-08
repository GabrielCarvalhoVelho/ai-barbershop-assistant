from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AppointmentStatus
from app.modules.chat.schemas import PaginationResponse


class AppointmentCreate(BaseModel):
    service: str = Field(
        ...,
        min_length=2,
        max_length=150,
        examples=["Corte masculino"],
    )
    scheduled_at: datetime = Field(
        ...,
        examples=["2026-06-01T14:00:00Z"],
    )
    duration_minutes: int = Field(
        default=30,
        ge=15,
        le=240,
        examples=[30],
    )

    @field_validator("scheduled_at")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("O horário do agendamento deve ser no futuro.")
        return v


class AppointmentResponse(BaseModel):
    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[1])
    company_id: int = Field(..., examples=[1])
    service: str = Field(..., examples=["Corte masculino"])
    scheduled_at: datetime = Field(..., examples=["2026-06-01T14:00:00Z"])
    duration_minutes: int = Field(..., examples=[30])
    status: AppointmentStatus = Field(..., examples=["scheduled"])
    created_at: datetime = Field(..., examples=["2026-05-07T10:00:00Z"])
    updated_at: datetime | None = Field(None, examples=[None])

    model_config = {"from_attributes": True}


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentResponse]
    pagination: PaginationResponse
