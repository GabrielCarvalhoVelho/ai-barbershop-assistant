from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import BusinessError, NotFoundError
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.modules.appointments.controller import AppointmentController
from app.modules.appointments.schemas import AppointmentCreate
from app.schemas.base_schema import SuccessResponse

_FUTURE = datetime.now(timezone.utc) + timedelta(days=1)
_NOW = datetime.now(timezone.utc)


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
        created_at=_NOW,
    )


def _make_body() -> AppointmentCreate:
    return AppointmentCreate(service="Corte", scheduled_at=_FUTURE, duration_minutes=30)


# ========================
# TestAppointmentControllerCreate
# ========================


class TestAppointmentControllerCreate:
    @pytest.mark.asyncio
    async def test_sem_conflito_retorna_success_response(self):
        user = _make_user()
        appt = _make_appointment()
        repo = AsyncMock()
        repo.has_conflict.return_value = False
        repo.create.return_value = appt

        result = await AppointmentController.create(_make_body(), user, repo)

        assert isinstance(result, SuccessResponse)
        assert result.data.id == 1
        assert result.data.service == "Corte"

    @pytest.mark.asyncio
    async def test_com_conflito_propaga_business_error(self):
        user = _make_user()
        repo = AsyncMock()
        repo.has_conflict.return_value = True

        with pytest.raises(BusinessError):
            await AppointmentController.create(_make_body(), user, repo)


# ========================
# TestAppointmentControllerGetById
# ========================


class TestAppointmentControllerGetById:
    @pytest.mark.asyncio
    async def test_owner_retorna_success_response(self):
        user = _make_user(user_id=1)
        appt = _make_appointment(user_id=1)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        result = await AppointmentController.get_by_id(1, user, repo)

        assert isinstance(result, SuccessResponse)
        assert result.data.id == 1

    @pytest.mark.asyncio
    async def test_id_invalido_propaga_not_found(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await AppointmentController.get_by_id(999, user, repo)


# ========================
# TestAppointmentControllerListMine
# ========================


class TestAppointmentControllerListMine:
    @pytest.mark.asyncio
    async def test_lista_vazia(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_user.return_value = []

        result = await AppointmentController.list_mine(user, repo)

        assert isinstance(result, SuccessResponse)
        assert result.data["appointments"] == []
        assert result.data["pagination"]["total"] == 0

    @pytest.mark.asyncio
    async def test_lista_com_dois_agendamentos(self):
        user = _make_user()
        appts = [_make_appointment(appt_id=1), _make_appointment(appt_id=2)]
        repo = AsyncMock()
        repo.get_by_user.return_value = appts

        result = await AppointmentController.list_mine(user, repo)

        assert len(result.data["appointments"]) == 2
        assert result.data["pagination"]["total"] == 2

    @pytest.mark.asyncio
    async def test_paginacao_com_offset(self):
        user = _make_user()
        repo = AsyncMock()
        # offset=10 retorna página vazia, mas total = 2 (simulado pelo limit=10_000)
        repo.get_by_user.side_effect = [
            [],  # chamada paginada (limit=5, offset=10)
            [_make_appointment(1), _make_appointment(2)],  # chamada de total
        ]

        result = await AppointmentController.list_mine(user, repo, limit=5, offset=10)

        assert result.data["pagination"]["limit"] == 5
        assert result.data["pagination"]["offset"] == 10
        assert result.data["pagination"]["total"] == 2


# ========================
# TestAppointmentControllerCancel
# ========================


class TestAppointmentControllerCancel:
    @pytest.mark.asyncio
    async def test_scheduled_retorna_cancelled(self):
        user = _make_user()
        appt = _make_appointment(status=AppointmentStatus.SCHEDULED)
        cancelled = _make_appointment(status=AppointmentStatus.CANCELLED)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt
        repo.update_status.return_value = cancelled

        result = await AppointmentController.cancel(1, user, repo)

        assert isinstance(result, SuccessResponse)
        assert result.data.status == AppointmentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_ja_cancelado_propaga_business_error(self):
        user = _make_user()
        appt = _make_appointment(status=AppointmentStatus.CANCELLED)
        repo = AsyncMock()
        repo.get_by_id.return_value = appt

        with pytest.raises(BusinessError):
            await AppointmentController.cancel(1, user, repo)
