from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.modules.appointments.controller import AppointmentController
from app.modules.appointments.schemas import AppointmentCreate
from app.repositories.appointment_repository import AppointmentRepository
from app.schemas.base_schema import SuccessResponse
from app.schemas.error_schema import ErrorResponse

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

_SECURITY = {"security": [{"bearerAuth": []}]}
_401 = {"model": ErrorResponse, "description": "Token ausente ou inválido (AUTH_003)"}
_403 = {"model": ErrorResponse, "description": "Acesso negado (AUTH_002)"}
_404 = {"model": ErrorResponse, "description": "Agendamento não encontrado (RES_001)"}
_400 = {"model": ErrorResponse, "description": "Regra de negócio violada (CHAT_001)"}


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=201,
    openapi_extra=_SECURITY,
    responses={400: _400, 401: _401, 422: {"model": ErrorResponse}},
)
async def create_appointment(
    body: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = AppointmentRepository(session)
    return await AppointmentController.create(body, current_user, repo)


# /me deve vir ANTES de /{appointment_id} — FastAPI resolve de cima para baixo
@router.get(
    "/me",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={401: _401},
)
async def list_my_appointments(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = AppointmentRepository(session)
    return await AppointmentController.list_mine(current_user, repo, limit=limit, offset=offset)


@router.get(
    "/{appointment_id}",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={401: _401, 403: _403, 404: _404},
)
async def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = AppointmentRepository(session)
    return await AppointmentController.get_by_id(appointment_id, current_user, repo)


@router.patch(
    "/{appointment_id}/cancel",
    response_model=SuccessResponse,
    openapi_extra=_SECURITY,
    responses={400: _400, 401: _401, 403: _403, 404: _404},
)
async def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    repo = AppointmentRepository(session)
    return await AppointmentController.cancel(appointment_id, current_user, repo)
