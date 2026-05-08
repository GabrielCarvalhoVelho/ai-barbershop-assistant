import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_utils import DB_TIMEOUT_SECONDS, db_operation
from app.core.logger import get_logger
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus

logger = get_logger(__name__)

_ACTIVE_STATUSES = [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]


class AppointmentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @db_operation("criar agendamento")
    async def create(
        self,
        user_id: int,
        company_id: int,
        service: str,
        scheduled_at: datetime,
        duration_minutes: int = 30,
    ) -> Appointment:
        logger.info(
            "Criando agendamento: user_id=%s company_id=%s service=%s scheduled_at=%s",
            user_id,
            company_id,
            service,
            scheduled_at.isoformat(),
        )
        appointment = Appointment(
            user_id=user_id,
            company_id=company_id,
            service=service,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.SCHEDULED,
        )
        self._session.add(appointment)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(appointment), timeout=DB_TIMEOUT_SECONDS)
        logger.info("Agendamento criado: id=%s", appointment.id)
        return appointment

    @db_operation("buscar agendamento")
    async def get_by_id(self, appointment_id: int) -> Appointment | None:
        logger.info("Buscando agendamento: id=%s", appointment_id)
        result = await asyncio.wait_for(
            self._session.get(Appointment, appointment_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
        if result is None:
            logger.info("Agendamento não encontrado: id=%s", appointment_id)
        return result

    @db_operation("listar agendamentos do usuário")
    async def get_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Appointment]:
        logger.info(
            "Buscando agendamentos: user_id=%s limit=%s offset=%s",
            user_id,
            limit,
            offset,
        )
        stmt = (
            select(Appointment)
            .where(Appointment.user_id == user_id)
            .order_by(Appointment.scheduled_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        appointments = list(result.scalars().all())
        logger.info(
            "Agendamentos encontrados: user_id=%s count=%s", user_id, len(appointments)
        )
        return appointments

    @db_operation("buscar agendamentos por período")
    async def get_by_company_and_date_range(
        self,
        company_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Appointment]:
        logger.info(
            "Buscando agendamentos: company_id=%s start=%s end=%s",
            company_id,
            start.isoformat(),
            end.isoformat(),
        )
        stmt = (
            select(Appointment)
            .where(
                Appointment.company_id == company_id,
                Appointment.scheduled_at >= start,
                Appointment.scheduled_at < end,
                Appointment.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(Appointment.scheduled_at.asc())
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        appointments = list(result.scalars().all())
        logger.info(
            "Agendamentos no período: company_id=%s count=%s", company_id, len(appointments)
        )
        return appointments

    @db_operation("verificar conflito de agendamento")
    async def has_conflict(
        self,
        company_id: int,
        scheduled_at: datetime,
        duration_minutes: int,
        exclude_appointment_id: int | None = None,
    ) -> bool:
        """Verifica se o slot solicitado colide com algum agendamento ativo.

        Dois intervalos [A_start, A_end) e [B_start, B_end) se sobrepõem quando
        A_start < B_end AND B_start < A_end.

        Busca candidatos via SQL (início < fim do novo slot) e faz a verificação
        precisa em Python — garante compatibilidade com SQLite (testes) e PostgreSQL.
        """
        end_time = scheduled_at + timedelta(minutes=duration_minutes)

        logger.info(
            "Verificando conflito: company_id=%s scheduled_at=%s end_time=%s",
            company_id,
            scheduled_at.isoformat(),
            end_time.isoformat(),
        )

        stmt = select(Appointment).where(
            Appointment.company_id == company_id,
            Appointment.status.in_(_ACTIVE_STATUSES),
            Appointment.scheduled_at < end_time,
        )
        result = await asyncio.wait_for(
            self._session.execute(stmt), timeout=DB_TIMEOUT_SECONDS
        )
        candidates = list(result.scalars().all())

        for appt in candidates:
            if exclude_appointment_id is not None and appt.id == exclude_appointment_id:
                continue
            # SQLite retorna datetimes sem tzinfo — normaliza para UTC antes de comparar
            appt_start = appt.scheduled_at
            if appt_start.tzinfo is None:
                appt_start = appt_start.replace(tzinfo=timezone.utc)
            appt_end = appt_start + timedelta(minutes=appt.duration_minutes)
            cmp_start = scheduled_at if scheduled_at.tzinfo is not None else scheduled_at.replace(tzinfo=timezone.utc)
            if cmp_start < appt_end:
                logger.info(
                    "Conflito detectado: appointment_id=%s scheduled_at=%s appt_end=%s",
                    appt.id,
                    appt.scheduled_at.isoformat(),
                    appt_end.isoformat(),
                )
                return True

        logger.info("Sem conflito: company_id=%s scheduled_at=%s", company_id, scheduled_at.isoformat())
        return False

    @db_operation("atualizar status do agendamento")
    async def update_status(
        self,
        appointment_id: int,
        status: AppointmentStatus,
    ) -> Appointment | None:
        logger.info(
            "Atualizando status: id=%s status=%s", appointment_id, status.value
        )
        appointment = await asyncio.wait_for(
            self._session.get(Appointment, appointment_id),
            timeout=DB_TIMEOUT_SECONDS,
        )
        if appointment is None:
            logger.info("Agendamento não encontrado para atualizar: id=%s", appointment_id)
            return None
        appointment.status = status
        appointment.updated_at = datetime.now(timezone.utc)
        await asyncio.wait_for(self._session.flush(), timeout=DB_TIMEOUT_SECONDS)
        await asyncio.wait_for(self._session.refresh(appointment), timeout=DB_TIMEOUT_SECONDS)
        logger.info("Status atualizado: id=%s status=%s", appointment.id, status.value)
        return appointment
