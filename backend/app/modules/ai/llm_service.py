from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.core.logger import get_logger
from app.models.enums import MessageSender
from app.modules.ai.prompts import BARBERSHOP_SYSTEM_PROMPT

logger = get_logger(__name__)


def _build_history_messages(history: list) -> list:
    """Converte lista de Message do banco para formato LangChain."""
    messages = []
    for msg in history:
        if msg.sender == MessageSender.USER:
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    return messages


async def generate_ai_response(message: str, history: list) -> str:
    """
    Chama o LLM via Groq com o histórico da conversa e retorna a resposta gerada.

    Args:
        message: Mensagem atual do usuário (já sanitizada).
        history: Lista de objetos Message do banco (ordenados por created_at asc).
                 Apenas as últimas N mensagens, conforme LLM_MAX_HISTORY.

    Returns:
        Texto da resposta gerada pelo modelo.

    Raises:
        AIServiceError: Se a API do Groq estiver indisponível ou retornar erro.
    """
    logger.info(
        "Chamando LLM: model=%s history_length=%d",
        settings.llm_model,
        len(history),
    )

    llm = ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0.7,
        max_tokens=512,
        timeout=30,
    )

    messages = [SystemMessage(content=BARBERSHOP_SYSTEM_PROMPT)]
    messages.extend(_build_history_messages(history))
    messages.append(HumanMessage(content=message))

    try:
        response = await llm.ainvoke(messages)
        logger.info("LLM respondeu: response_length=%d", len(response.content))
        return response.content
    except Exception as exc:
        logger.error("Erro ao chamar LLM: %s", exc, exc_info=True)
        raise AIServiceError(
            "O serviço de inteligência artificial está temporariamente indisponível. "
            "Tente novamente em instantes."
        ) from exc
