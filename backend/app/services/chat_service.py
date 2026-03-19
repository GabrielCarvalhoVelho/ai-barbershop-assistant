from app.core.logger import get_logger

logger = get_logger(__name__)

def generate_response(message: str) -> str:
    logger.info(f"Mensagem recebida: {message}")

    if message == "erro":
        logger.error("Erro forçado no sistema")
        raise Exception("Erro de teste")

    return f"Você disse: {message}"