import os

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-tests")

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base
from app.models.appointment import Appointment
from app.models.company import Company
from app.models.enums import AppointmentStatus
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository

engine = create_async_engine("sqlite+aiosqlite://", echo=False)


def _enable_fk(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


event.listen(engine.sync_engine, "connect", _enable_fk)

factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_NOW = datetime(2026, 6, 1, 14, 0, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session():
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def company(session):
    c = Company(name="Barbearia Teste")
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


@pytest_asyncio.fixture
async def user(session, company):
    u = User(
        company_id=company.id,
        name="Cliente Teste",
        phone="+5511999000001",
        password_hash="placeholder",
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest_asyncio.fixture
async def repo(session):
    return AppointmentRepository(session)


async def _create_appointment(
    session,
    user_id: int,
    company_id: int,
    scheduled_at: datetime,
    duration_minutes: int = 30,
    service: str = "Corte",
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> Appointment:
    appt = Appointment(
        user_id=user_id,
        company_id=company_id,
        service=service,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        status=status,
    )
    session.add(appt)
    await session.commit()
    await session.refresh(appt)
    return appt


# ========================
# TestCreate
# ========================


class TestCreate:
    @pytest.mark.asyncio
    async def test_cria_e_retorna_com_id(self, repo, user, company):
        appt = await repo.create(
            user_id=user.id,
            company_id=company.id,
            service="Corte",
            scheduled_at=_NOW,
        )
        assert appt.id is not None

    @pytest.mark.asyncio
    async def test_campos_corretos(self, repo, user, company):
        appt = await repo.create(
            user_id=user.id,
            company_id=company.id,
            service="Barba",
            scheduled_at=_NOW,
            duration_minutes=45,
        )
        assert appt.user_id == user.id
        assert appt.company_id == company.id
        assert appt.service == "Barba"
        # SQLite descarta tzinfo — compara sem timezone
        scheduled = appt.scheduled_at.replace(tzinfo=None) if appt.scheduled_at.tzinfo else appt.scheduled_at
        assert scheduled == _NOW.replace(tzinfo=None)
        assert appt.duration_minutes == 45

    @pytest.mark.asyncio
    async def test_status_padrao_scheduled(self, repo, user, company):
        appt = await repo.create(
            user_id=user.id,
            company_id=company.id,
            service="Corte",
            scheduled_at=_NOW,
        )
        assert appt.status == AppointmentStatus.SCHEDULED

    @pytest.mark.asyncio
    async def test_duration_padrao_30(self, repo, user, company):
        appt = await repo.create(
            user_id=user.id,
            company_id=company.id,
            service="Corte",
            scheduled_at=_NOW,
        )
        assert appt.duration_minutes == 30

    @pytest.mark.asyncio
    async def test_created_at_preenchido(self, repo, user, company):
        appt = await repo.create(
            user_id=user.id,
            company_id=company.id,
            service="Corte",
            scheduled_at=_NOW,
        )
        assert appt.created_at is not None


# ========================
# TestGetById
# ========================


class TestGetById:
    @pytest.mark.asyncio
    async def test_encontrado(self, session, repo, user, company):
        existing = await _create_appointment(session, user.id, company.id, _NOW)
        result = await repo.get_by_id(existing.id)
        assert result is not None
        assert result.id == existing.id

    @pytest.mark.asyncio
    async def test_nao_encontrado_retorna_none(self, repo):
        result = await repo.get_by_id(99999)
        assert result is None


# ========================
# TestGetByUser
# ========================


class TestGetByUser:
    @pytest.mark.asyncio
    async def test_retorna_agendamentos_do_usuario(self, session, repo, user, company):
        await _create_appointment(session, user.id, company.id, _NOW)
        await _create_appointment(session, user.id, company.id, _NOW + timedelta(hours=1))
        result = await repo.get_by_user(user.id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_vazio_para_usuario_sem_agendamentos(self, repo, user):
        result = await repo.get_by_user(user.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_ordenado_por_scheduled_at_desc(self, session, repo, user, company):
        t1 = _NOW
        t2 = _NOW + timedelta(hours=2)
        t3 = _NOW + timedelta(hours=4)
        await _create_appointment(session, user.id, company.id, t1)
        await _create_appointment(session, user.id, company.id, t3)
        await _create_appointment(session, user.id, company.id, t2)

        result = await repo.get_by_user(user.id)
        times = [a.scheduled_at for a in result]
        assert times == sorted(times, reverse=True)

    @pytest.mark.asyncio
    async def test_paginacao_limit(self, session, repo, user, company):
        for i in range(5):
            await _create_appointment(session, user.id, company.id, _NOW + timedelta(hours=i))
        result = await repo.get_by_user(user.id, limit=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_paginacao_offset(self, session, repo, user, company):
        for i in range(5):
            await _create_appointment(session, user.id, company.id, _NOW + timedelta(hours=i))
        result_page1 = await repo.get_by_user(user.id, limit=3, offset=0)
        result_page2 = await repo.get_by_user(user.id, limit=3, offset=3)
        assert len(result_page2) == 2
        ids_p1 = {a.id for a in result_page1}
        ids_p2 = {a.id for a in result_page2}
        assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.asyncio
    async def test_isolado_por_usuario(self, session, repo, user, company):
        other_user = User(
            company_id=company.id,
            name="Outro",
            phone="+5511888000001",
            password_hash="placeholder",
        )
        session.add(other_user)
        await session.commit()
        await session.refresh(other_user)

        await _create_appointment(session, user.id, company.id, _NOW)
        await _create_appointment(session, other_user.id, company.id, _NOW + timedelta(hours=2))

        result = await repo.get_by_user(user.id)
        assert len(result) == 1
        assert result[0].user_id == user.id


# ========================
# TestGetByCompanyAndDateRange
# ========================


class TestGetByCompanyAndDateRange:
    @pytest.mark.asyncio
    async def test_retorna_agendamentos_no_intervalo(self, session, repo, user, company):
        await _create_appointment(session, user.id, company.id, _NOW)
        result = await repo.get_by_company_and_date_range(
            company.id,
            start=_NOW - timedelta(hours=1),
            end=_NOW + timedelta(hours=1),
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_exclui_fora_do_range(self, session, repo, user, company):
        await _create_appointment(session, user.id, company.id, _NOW + timedelta(hours=5))
        result = await repo.get_by_company_and_date_range(
            company.id,
            start=_NOW,
            end=_NOW + timedelta(hours=2),
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_exclui_cancelled(self, session, repo, user, company):
        await _create_appointment(
            session, user.id, company.id, _NOW, status=AppointmentStatus.CANCELLED
        )
        result = await repo.get_by_company_and_date_range(
            company.id, start=_NOW - timedelta(hours=1), end=_NOW + timedelta(hours=1)
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_exclui_completed(self, session, repo, user, company):
        await _create_appointment(
            session, user.id, company.id, _NOW, status=AppointmentStatus.COMPLETED
        )
        result = await repo.get_by_company_and_date_range(
            company.id, start=_NOW - timedelta(hours=1), end=_NOW + timedelta(hours=1)
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_inclui_confirmed(self, session, repo, user, company):
        await _create_appointment(
            session, user.id, company.id, _NOW, status=AppointmentStatus.CONFIRMED
        )
        result = await repo.get_by_company_and_date_range(
            company.id, start=_NOW - timedelta(hours=1), end=_NOW + timedelta(hours=1)
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_ordenado_por_scheduled_at_asc(self, session, repo, user, company):
        t2 = _NOW + timedelta(hours=1)
        t1 = _NOW
        await _create_appointment(session, user.id, company.id, t2)
        await _create_appointment(session, user.id, company.id, t1)

        result = await repo.get_by_company_and_date_range(
            company.id, start=_NOW - timedelta(minutes=1), end=_NOW + timedelta(hours=2)
        )
        times = [a.scheduled_at for a in result]
        assert times == sorted(times)

    @pytest.mark.asyncio
    async def test_vazio_para_company_sem_agendamentos(self, repo, company):
        result = await repo.get_by_company_and_date_range(
            company.id, start=_NOW, end=_NOW + timedelta(hours=8)
        )
        assert result == []


# ========================
# TestHasConflict
# ========================


class TestHasConflict:
    @pytest.mark.asyncio
    async def test_sem_agendamentos_retorna_false(self, repo, company):
        result = await repo.has_conflict(company.id, _NOW, 30)
        assert result is False

    @pytest.mark.asyncio
    async def test_slot_diferente_retorna_false(self, session, repo, user, company):
        # Existente: 14h00–14h30. Novo: 15h00–15h30. Sem sobreposição.
        await _create_appointment(session, user.id, company.id, _NOW, duration_minutes=30)
        result = await repo.has_conflict(company.id, _NOW + timedelta(hours=1), 30)
        assert result is False

    @pytest.mark.asyncio
    async def test_sobreposicao_exata_retorna_true(self, session, repo, user, company):
        # Existente: 14h00–14h30. Novo: 14h00–14h30. Conflito total.
        await _create_appointment(session, user.id, company.id, _NOW, duration_minutes=30)
        result = await repo.has_conflict(company.id, _NOW, 30)
        assert result is True

    @pytest.mark.asyncio
    async def test_inicio_dentro_do_slot_existente_retorna_true(self, session, repo, user, company):
        # Existente: 14h00–14h30. Novo: 14h15–14h45. Conflito parcial.
        await _create_appointment(session, user.id, company.id, _NOW, duration_minutes=30)
        result = await repo.has_conflict(company.id, _NOW + timedelta(minutes=15), 30)
        assert result is True

    @pytest.mark.asyncio
    async def test_novo_engloba_existente_retorna_true(self, session, repo, user, company):
        # Existente: 14h10–14h40. Novo: 14h00–15h00. Conflito — novo engloba o existente.
        await _create_appointment(
            session, user.id, company.id, _NOW + timedelta(minutes=10), duration_minutes=30
        )
        result = await repo.has_conflict(company.id, _NOW, 60)
        assert result is True

    @pytest.mark.asyncio
    async def test_slots_adjacentes_sem_conflito(self, session, repo, user, company):
        # Existente: 14h00–14h30. Novo começa às 14h30. Não há sobreposição (intervalo semi-aberto).
        await _create_appointment(session, user.id, company.id, _NOW, duration_minutes=30)
        result = await repo.has_conflict(company.id, _NOW + timedelta(minutes=30), 30)
        assert result is False

    @pytest.mark.asyncio
    async def test_cancelled_nao_bloqueia(self, session, repo, user, company):
        await _create_appointment(
            session, user.id, company.id, _NOW, status=AppointmentStatus.CANCELLED
        )
        result = await repo.has_conflict(company.id, _NOW, 30)
        assert result is False

    @pytest.mark.asyncio
    async def test_completed_nao_bloqueia(self, session, repo, user, company):
        await _create_appointment(
            session, user.id, company.id, _NOW, status=AppointmentStatus.COMPLETED
        )
        result = await repo.has_conflict(company.id, _NOW, 30)
        assert result is False

    @pytest.mark.asyncio
    async def test_exclude_appointment_id_ignora_o_proprio(self, session, repo, user, company):
        existing = await _create_appointment(session, user.id, company.id, _NOW, duration_minutes=30)
        result = await repo.has_conflict(
            company.id, _NOW, 30, exclude_appointment_id=existing.id
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_exclude_nao_ignora_outros_conflitos(self, session, repo, user, company):
        existing = await _create_appointment(session, user.id, company.id, _NOW, duration_minutes=30)
        other = await _create_appointment(
            session, user.id, company.id, _NOW + timedelta(minutes=15), duration_minutes=30
        )
        # Excluindo 'existing', mas 'other' ainda conflita com _NOW
        result = await repo.has_conflict(
            company.id, _NOW, 30, exclude_appointment_id=existing.id
        )
        assert result is True


# ========================
# TestUpdateStatus
# ========================


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_atualiza_status(self, session, repo, user, company):
        appt = await _create_appointment(session, user.id, company.id, _NOW)
        result = await repo.update_status(appt.id, AppointmentStatus.CONFIRMED)
        assert result is not None
        assert result.status == AppointmentStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_seta_updated_at(self, session, repo, user, company):
        appt = await _create_appointment(session, user.id, company.id, _NOW)
        assert appt.updated_at is None
        result = await repo.update_status(appt.id, AppointmentStatus.CANCELLED)
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_nao_encontrado_retorna_none(self, repo):
        result = await repo.update_status(99999, AppointmentStatus.CANCELLED)
        assert result is None

    @pytest.mark.asyncio
    async def test_cancela_agendamento(self, session, repo, user, company):
        appt = await _create_appointment(session, user.id, company.id, _NOW)
        result = await repo.update_status(appt.id, AppointmentStatus.CANCELLED)
        assert result.status == AppointmentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_completa_agendamento(self, session, repo, user, company):
        appt = await _create_appointment(
            session, user.id, company.id, _NOW, status=AppointmentStatus.CONFIRMED
        )
        result = await repo.update_status(appt.id, AppointmentStatus.COMPLETED)
        assert result.status == AppointmentStatus.COMPLETED
