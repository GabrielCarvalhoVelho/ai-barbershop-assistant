from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.enums import AppointmentStatus
from app.modules.appointments.schemas import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
)
from app.modules.chat.schemas import PaginationResponse

_FUTURE = datetime.now(timezone.utc) + timedelta(days=1)
_PAST = datetime.now(timezone.utc) - timedelta(seconds=1)
_NOW = datetime.now(timezone.utc)


# ========================
# TestAppointmentCreate — válidos
# ========================


class TestAppointmentCreateValid:
    def test_campos_minimos(self):
        req = AppointmentCreate(service="Corte", scheduled_at=_FUTURE)
        assert req.service == "Corte"
        assert req.duration_minutes == 30

    def test_duration_minutes_customizado(self):
        req = AppointmentCreate(service="Barba", scheduled_at=_FUTURE, duration_minutes=60)
        assert req.duration_minutes == 60

    def test_duration_minimo_aceito(self):
        req = AppointmentCreate(service="Corte", scheduled_at=_FUTURE, duration_minutes=15)
        assert req.duration_minutes == 15

    def test_duration_maximo_aceito(self):
        req = AppointmentCreate(service="Corte", scheduled_at=_FUTURE, duration_minutes=240)
        assert req.duration_minutes == 240

    def test_scheduled_at_sem_tzinfo_normalizado_para_utc(self):
        futuro_naive = (_FUTURE).replace(tzinfo=None)
        req = AppointmentCreate(service="Corte", scheduled_at=futuro_naive)
        assert req.scheduled_at.tzinfo is not None

    def test_service_com_2_chars(self):
        req = AppointmentCreate(service="AB", scheduled_at=_FUTURE)
        assert req.service == "AB"

    def test_service_com_150_chars(self):
        req = AppointmentCreate(service="A" * 150, scheduled_at=_FUTURE)
        assert len(req.service) == 150


# ========================
# TestAppointmentCreate — inválidos
# ========================


class TestAppointmentCreateInvalid:
    def test_service_vazio(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(service="", scheduled_at=_FUTURE)

    def test_service_com_1_char(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(service="A", scheduled_at=_FUTURE)

    def test_service_com_151_chars(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(service="A" * 151, scheduled_at=_FUTURE)

    def test_scheduled_at_no_passado(self):
        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(service="Corte", scheduled_at=_PAST)
        assert "deve ser no futuro" in str(exc_info.value)

    def test_scheduled_at_agora(self):
        with pytest.raises(ValidationError) as exc_info:
            AppointmentCreate(service="Corte", scheduled_at=_NOW)
        assert "deve ser no futuro" in str(exc_info.value)

    def test_duration_abaixo_do_minimo(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(service="Corte", scheduled_at=_FUTURE, duration_minutes=14)

    def test_duration_acima_do_maximo(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(service="Corte", scheduled_at=_FUTURE, duration_minutes=241)

    def test_duration_zero(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(service="Corte", scheduled_at=_FUTURE, duration_minutes=0)

    def test_scheduled_at_ausente(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(service="Corte")

    def test_service_ausente(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(scheduled_at=_FUTURE)


# ========================
# TestAppointmentResponse
# ========================


class TestAppointmentResponseValid:
    def test_todos_os_campos(self):
        resp = AppointmentResponse(
            id=1,
            user_id=1,
            company_id=1,
            service="Corte",
            scheduled_at=_FUTURE,
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            created_at=_NOW,
        )
        assert resp.id == 1
        assert resp.status == AppointmentStatus.SCHEDULED
        assert resp.updated_at is None

    def test_updated_at_padrao_none(self):
        resp = AppointmentResponse(
            id=1,
            user_id=1,
            company_id=1,
            service="Barba",
            scheduled_at=_FUTURE,
            duration_minutes=30,
            status=AppointmentStatus.CONFIRMED,
            created_at=_NOW,
        )
        assert resp.updated_at is None

    def test_status_serializado_como_string(self):
        resp = AppointmentResponse(
            id=1,
            user_id=1,
            company_id=1,
            service="Corte",
            scheduled_at=_FUTURE,
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            created_at=_NOW,
        )
        data = resp.model_dump()
        assert data["status"] == "scheduled"

    def test_todos_status_validos(self):
        for status in AppointmentStatus:
            resp = AppointmentResponse(
                id=1,
                user_id=1,
                company_id=1,
                service="Corte",
                scheduled_at=_FUTURE,
                duration_minutes=30,
                status=status,
                created_at=_NOW,
            )
            assert resp.status == status

    def test_from_attributes_com_objeto_orm(self):
        from app.models.appointment import Appointment

        appt = Appointment(
            id=5,
            user_id=2,
            company_id=3,
            service="Sobrancelha",
            scheduled_at=_FUTURE,
            duration_minutes=20,
            status=AppointmentStatus.SCHEDULED,
            created_at=_NOW,
        )
        resp = AppointmentResponse.model_validate(appt)
        assert resp.id == 5
        assert resp.service == "Sobrancelha"
        assert resp.duration_minutes == 20


class TestAppointmentResponseInvalid:
    def test_id_ausente(self):
        with pytest.raises(ValidationError):
            AppointmentResponse(
                user_id=1,
                company_id=1,
                service="Corte",
                scheduled_at=_FUTURE,
                duration_minutes=30,
                status=AppointmentStatus.SCHEDULED,
                created_at=_NOW,
            )

    def test_service_ausente(self):
        with pytest.raises(ValidationError):
            AppointmentResponse(
                id=1,
                user_id=1,
                company_id=1,
                scheduled_at=_FUTURE,
                duration_minutes=30,
                status=AppointmentStatus.SCHEDULED,
                created_at=_NOW,
            )


# ========================
# TestAppointmentListResponse
# ========================


class TestAppointmentListResponseValid:
    def test_lista_vazia_com_paginacao(self):
        pagination = PaginationResponse(limit=20, offset=0, total=0)
        resp = AppointmentListResponse(appointments=[], pagination=pagination)
        assert resp.appointments == []
        assert resp.pagination.total == 0

    def test_lista_com_um_agendamento(self):
        appt = AppointmentResponse(
            id=1,
            user_id=1,
            company_id=1,
            service="Corte",
            scheduled_at=_FUTURE,
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            created_at=_NOW,
        )
        pagination = PaginationResponse(limit=20, offset=0, total=1)
        resp = AppointmentListResponse(appointments=[appt], pagination=pagination)
        assert len(resp.appointments) == 1
        assert resp.appointments[0].service == "Corte"

    def test_paginacao_com_offset(self):
        pagination = PaginationResponse(limit=5, offset=10, total=25)
        resp = AppointmentListResponse(appointments=[], pagination=pagination)
        assert resp.pagination.limit == 5
        assert resp.pagination.offset == 10
        assert resp.pagination.total == 25


class TestAppointmentListResponseInvalid:
    def test_pagination_ausente(self):
        with pytest.raises(ValidationError):
            AppointmentListResponse(appointments=[])
