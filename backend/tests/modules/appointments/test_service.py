from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthorizationError, BusinessError, NotFoundError
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.modules.appointments.schemas import AppointmentCreate
from app.modules.appointments.service import (
    cancel_appointment,
    create_appointment,
    get_appointment,
)

_FUTURE = datetime.now(timezone.utc) + timedelta(days=1)


def _make_user(role: UserRole = UserRole.CUSTOMER, user_id: int = 1, company_id: int = 1) -> User:
    user = User(
        id=user_id,
        company_id=company_id,
        name="Teste",
        phone="+5511000000001",
        password_hash="placeholder",
        role=role,
    )
    user.is_active = True
    return user


def _make_appointment(
    appt_id: int = 1,
    user_id: int = 1,
    company_id: int = 1,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> Appointment:
    return Appointment(
        id=appt_id,
        user_id=user_id,
        company_id=company_id,
        service="Corte",
        scheduled_at=_FUTURE,
        duration_minutes=30,
        status=status,
        created_at=datetime.now(timezone.utc),
    )


def _make_body(**kwargs) -> AppointmentCreate:
    defaults = {"service": "Corte", "scheduled_at": _FUTURE, "duration_minutes": 30}
    defaults.update(kwargs)
    return AppointmentCreate(**defaults)


# ========================
# TestCreateAppointment
# ========================


class TestCreateAppointment:
    @pytest.mark.asyncio
    async def test_sem_conflito_cria_agendamento(self):
        user = _make_user()
        repo = AsyncMock()
        repo.has_conflict.return_value = False
        appt = _make_appointment()
        repo.create.return_value = appt

        result = await create_appointment(_make_body(), user, repo)

        assert result is appt
        repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_com_conflito_levanta_business_error(self):
        user = _make_user()
        repo = AsyncMock()
        repo.has_conflict.return_value = True

        with pytest.raises(BusinessError) as exc_info:
            await create_appointment(_make_body(), user, repo)

        assert "Horário indisponível" in exc_info.value.message
        repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_repassa_company_id_correto(self):
        user = _make_user(company_id=5)
        repo = AsyncMock()
        repo.has_conflict.return_value = False
        repo.create.return_value = _make_appointment()

        await create_appointment(_make_body(), user, repo)

        call_kwargs = repo.has_conflict.call_args.kwargs
        assert call_kwargs["company_id"] == 5


# ========================
# TestGetAppointment
# ========================


class TestGetAppointment:
    @pytest.mark.asyncio
    async def test_owner_busca_proprio(self):
        user = _make_user(user_id=1)
        appt = _make_appointment(user_id=1)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        result = await get_appointment(1, user, repo)
        assert result is appt

    @pytest.mark.asyncio
    async def test_admin_acessa_de_outro_user(self):
        admin = _make_user(role=UserRole.ADMIN, user_id=3)
        appt = _make_appointment(user_id=1)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        result = await get_appointment(1, admin, repo)
        assert result is appt

    @pytest.mark.asyncio
    async def test_customer_acessa_de_outro_levanta_authorization_error(self):
        user = _make_user(user_id=2)
        appt = _make_appointment(user_id=1)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        with pytest.raises(AuthorizationError) as exc_info:
            await get_appointment(1, user, repo)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_id_inexistente_levanta_not_found(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await get_appointment(999, user, repo)

        assert exc_info.value.status_code == 404


# ========================
# TestCancelAppointment
# ========================


class TestCancelAppointment:
    @pytest.mark.asyncio
    async def test_scheduled_pode_cancelar(self):
        user = _make_user()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED)
        cancelled = _make_appointment(status=AppointmentStatus.CANCELLED)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt
        repo.update_status.return_value = cancelled

        result = await cancel_appointment(1, user, repo)

        assert result.status == AppointmentStatus.CANCELLED
        repo.update_status.assert_awaited_once_with(1, AppointmentStatus.CANCELLED)

    @pytest.mark.asyncio
    async def test_confirmed_pode_cancelar(self):
        user = _make_user()
        appt = _make_appointment(status=AppointmentStatus.CONFIRMED)
        cancelled = _make_appointment(status=AppointmentStatus.CANCELLED)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt
        repo.update_status.return_value = cancelled

        result = await cancel_appointment(1, user, repo)
        assert result.status == AppointmentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_ja_cancelado_levanta_business_error(self):
        user = _make_user()
        appt = _make_appointment(status=AppointmentStatus.CANCELLED)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        with pytest.raises(BusinessError):
            await cancel_appointment(1, user, repo)

        repo.update_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_completed_levanta_business_error(self):
        user = _make_user()
        appt = _make_appointment(status=AppointmentStatus.COMPLETED)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        with pytest.raises(BusinessError):
            await cancel_appointment(1, user, repo)

    @pytest.mark.asyncio
    async def test_ownership_errado_levanta_authorization_error(self):
        user = _make_user(user_id=2)
        appt = _make_appointment(user_id=1)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        with pytest.raises(AuthorizationError):
            await cancel_appointment(1, user, repo)

    @pytest.mark.asyncio
    async def test_id_inexistente_levanta_not_found(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await cancel_appointment(999, user, repo)
