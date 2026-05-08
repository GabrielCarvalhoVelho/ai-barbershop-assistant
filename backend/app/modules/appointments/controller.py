from app.models.user import User
from app.modules.appointments import service
from app.modules.appointments.schemas import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
)
from app.modules.chat.schemas import PaginationResponse
from app.repositories.appointment_repository import AppointmentRepository
from app.schemas.base_schema import SuccessResponse


class AppointmentController:
    @staticmethod
    async def create(
        body: AppointmentCreate,
        current_user: User,
        repo: AppointmentRepository,
    ) -> SuccessResponse:
        appt = await service.create_appointment(body, current_user, repo)
        return SuccessResponse(data=AppointmentResponse.model_validate(appt))

    @staticmethod
    async def get_by_id(
        appointment_id: int,
        current_user: User,
        repo: AppointmentRepository,
    ) -> SuccessResponse:
        appt = await service.get_appointment(appointment_id, current_user, repo)
        return SuccessResponse(data=AppointmentResponse.model_validate(appt))

    @staticmethod
    async def list_mine(
        current_user: User,
        repo: AppointmentRepository,
        limit: int = 20,
        offset: int = 0,
    ) -> SuccessResponse:
        appointments = await repo.get_by_user(current_user.id, limit=limit, offset=offset)
        all_appts = await repo.get_by_user(current_user.id, limit=10_000, offset=0)
        pagination = PaginationResponse(limit=limit, offset=offset, total=len(all_appts))
        data = AppointmentListResponse(
            appointments=[AppointmentResponse.model_validate(a) for a in appointments],
            pagination=pagination,
        )
        return SuccessResponse(data=data.model_dump())

    @staticmethod
    async def cancel(
        appointment_id: int,
        current_user: User,
        repo: AppointmentRepository,
    ) -> SuccessResponse:
        appt = await service.cancel_appointment(appointment_id, current_user, repo)
        return SuccessResponse(data=AppointmentResponse.model_validate(appt))
