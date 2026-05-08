from app.core.exceptions import AppointmentConflictError, AuthorizationError, BusinessError, NotFoundError
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.modules.appointments.schemas import AppointmentCreate
from app.repositories.appointment_repository import AppointmentRepository

_ACTIVE_CANCELLABLE = {AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED}


async def create_appointment(
    body: AppointmentCreate,
    current_user: User,
    repo: AppointmentRepository,
) -> Appointment:
    conflict = await repo.has_conflict(
        company_id=current_user.company_id,
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
    )
    if conflict:
        raise AppointmentConflictError("Horário indisponível. Escolha outro horário.")
    return await repo.create(
        user_id=current_user.id,
        company_id=current_user.company_id,
        service=body.service,
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
    )


async def get_appointment(
    appointment_id: int,
    current_user: User,
    repo: AppointmentRepository,
) -> Appointment:
    appt = await repo.get_by_id(appointment_id)
    if appt is None:
        raise NotFoundError("Agendamento não encontrado.")
    if appt.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise AuthorizationError("Sem permissão para acessar este agendamento.")
    return appt


async def cancel_appointment(
    appointment_id: int,
    current_user: User,
    repo: AppointmentRepository,
) -> Appointment:
    appt = await get_appointment(appointment_id, current_user, repo)
    if appt.status not in _ACTIVE_CANCELLABLE:
        raise BusinessError("Apenas agendamentos agendados ou confirmados podem ser cancelados.")
    return await repo.update_status(appointment_id, AppointmentStatus.CANCELLED)
