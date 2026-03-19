from app.core.logger import get_logger
from app.schemas.chat_schema import ChatResponse

logger = get_logger(__name__)


def generate_response(message: str) -> ChatResponse:
    logger.info(f"Mensagem recebida: {message}")

    if message == "erro":
        logger.error("Erro forçado no sistema")
        raise Exception("Erro de teste")

    return ChatResponse(response=f"Você disse: {message}")