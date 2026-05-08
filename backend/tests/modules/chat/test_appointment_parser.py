from datetime import datetime, timedelta, timezone

from app.modules.chat.appointment_parser import (
    AppointmentData,
    extract_appointment,
    strip_appointment_block,
)

_FUTURE = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
_PAST = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_block(service="Corte", scheduled_at=None, duration_minutes=30, extra="") -> str:
    scheduled_at = scheduled_at or _FUTURE
    lines = [
        "<APPOINTMENT>",
        f"service={service}",
        f"scheduled_at={scheduled_at}",
    ]
    if duration_minutes is not None:
        lines.append(f"duration_minutes={duration_minutes}")
    if extra:
        lines.append(extra)
    lines.append("</APPOINTMENT>")
    return "\n".join(lines)


# ========================
# TestExtractAppointment
# ========================


class TestExtractAppointment:
    def test_bloco_valido_retorna_appointment_data(self):
        result = extract_appointment(_make_block())
        assert isinstance(result, AppointmentData)
        assert result.service == "Corte"
        assert result.duration_minutes == 30
        assert result.scheduled_at.tzinfo is not None

    def test_sem_bloco_retorna_none(self):
        assert extract_appointment("Olá! Como posso ajudar?") is None

    def test_bloco_sem_service_retorna_none(self):
        block = "<APPOINTMENT>\nscheduled_at={}\nduration_minutes=30\n</APPOINTMENT>".format(_FUTURE)
        assert extract_appointment(block) is None

    def test_bloco_sem_scheduled_at_retorna_none(self):
        block = "<APPOINTMENT>\nservice=Corte\nduration_minutes=30\n</APPOINTMENT>"
        assert extract_appointment(block) is None

    def test_scheduled_at_no_passado_retorna_none(self):
        assert extract_appointment(_make_block(scheduled_at=_PAST)) is None

    def test_scheduled_at_malformado_retorna_none(self):
        assert extract_appointment(_make_block(scheduled_at="nao-e-data")) is None

    def test_duration_ausente_usa_default_30(self):
        block = "<APPOINTMENT>\nservice=Corte\nscheduled_at={}\n</APPOINTMENT>".format(_FUTURE)
        result = extract_appointment(block)
        assert result is not None
        assert result.duration_minutes == 30

    def test_duration_abaixo_do_minimo_clampeia_para_15(self):
        result = extract_appointment(_make_block(duration_minutes=5))
        assert result is not None
        assert result.duration_minutes == 15

    def test_duration_acima_do_maximo_clampeia_para_240(self):
        result = extract_appointment(_make_block(duration_minutes=999))
        assert result is not None
        assert result.duration_minutes == 240

    def test_bloco_embutido_em_texto_maior(self):
        text = "Ótimo! Vou agendar para você.\n" + _make_block() + "\nAté logo!"
        result = extract_appointment(text)
        assert result is not None
        assert result.service == "Corte"

    def test_duration_nao_numerico_usa_default_30(self):
        result = extract_appointment(_make_block(duration_minutes="invalido"))
        assert result is not None
        assert result.duration_minutes == 30

    def test_scheduled_at_z_suffix_aceito(self):
        block = _make_block(scheduled_at=_FUTURE)
        result = extract_appointment(block)
        assert result is not None
        assert result.scheduled_at.tzinfo is not None


# ========================
# TestStripAppointmentBlock
# ========================


class TestStripAppointmentBlock:
    def test_remove_bloco_retorna_texto_limpo(self):
        text = "Agendei para você.\n" + _make_block()
        result = strip_appointment_block(text)
        assert "<APPOINTMENT>" not in result
        assert "</APPOINTMENT>" not in result
        assert "Agendei para você." in result

    def test_sem_bloco_retorna_texto_original(self):
        text = "Olá! Posso ajudar com agendamentos."
        assert strip_appointment_block(text) == text

    def test_texto_so_com_bloco_retorna_vazio(self):
        result = strip_appointment_block(_make_block())
        assert result == ""
