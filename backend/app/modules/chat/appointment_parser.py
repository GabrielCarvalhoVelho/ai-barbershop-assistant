import re
from dataclasses import dataclass
from datetime import datetime, timezone

_BLOCK_RE = re.compile(r"<APPOINTMENT>(.*?)</APPOINTMENT>", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w+)=(.+)$", re.MULTILINE)


@dataclass
class AppointmentData:
    service: str
    scheduled_at: datetime
    duration_minutes: int


def extract_appointment(text: str) -> AppointmentData | None:
    """Extrai e valida dados do bloco <APPOINTMENT> na resposta do LLM.

    Retorna None se o bloco estiver ausente, malformado ou com dados inválidos
    (ex: scheduled_at no passado, campos obrigatórios ausentes).
    """
    match = _BLOCK_RE.search(text)
    if not match:
        return None

    fields = dict(_FIELD_RE.findall(match.group(1)))

    service = fields.get("service", "").strip()
    scheduled_at_raw = fields.get("scheduled_at", "").strip()
    duration_raw = fields.get("duration_minutes", "30").strip()

    if not service or not scheduled_at_raw:
        return None

    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_raw.replace("Z", "+00:00"))
    except ValueError:
        return None

    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

    if scheduled_at <= datetime.now(timezone.utc):
        return None

    try:
        duration_minutes = int(duration_raw)
    except ValueError:
        duration_minutes = 30

    duration_minutes = max(15, min(240, duration_minutes))

    return AppointmentData(
        service=service,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
    )


def strip_appointment_block(text: str) -> str:
    """Remove o bloco <APPOINTMENT>...</APPOINTMENT> antes de entregar a resposta ao cliente."""
    return _BLOCK_RE.sub("", text).strip()
