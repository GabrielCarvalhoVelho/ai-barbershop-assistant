import re

from app.core.exceptions import BusinessError
from app.core.logger import get_logger
from app.modules.ai.llm_service import generate_ai_response
from app.modules.ai.prompts import BusinessInfo, build_system_prompt

logger = get_logger(__name__)

BLOCKED_PATTERNS = [
    re.compile(r"(.)(\1{9,})", re.IGNORECASE),           # 10+ caracteres repetidos seguidos
    re.compile(r"(\b\w+\b)(\s+\1){4,}", re.IGNORECASE),  # mesma palavra 5+ vezes seguidas
]


def _sanitize_message(message: str) -> str:
    """Normaliza espaços internos da mensagem."""
    return re.sub(r"\s+", " ", message).strip()


def _validate_business_rules(message: str) -> None:
    """Validações de regra de negócio (conteúdo, não formato)."""
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(message):
            raise BusinessError(
                "Sua mensagem parece conter conteúdo repetitivo. "
                "Por favor, envie uma mensagem válida."
            )


async def generate_response(
    message: str,
    history: list,
    business_info: BusinessInfo,
) -> str:
    message = _sanitize_message(message)
    _validate_business_rules(message)

    logger.info("Mensagem recebida: message_length=%d", len(message))

    system_prompt = build_system_prompt(business_info)

    return await generate_ai_response(message, history, system_prompt)
