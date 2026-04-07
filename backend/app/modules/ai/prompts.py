from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessInfo:
    """Dados do negócio usados para personalizar o prompt do assistente.

    DTO que desacopla o módulo de IA do model SQLAlchemy Company.
    """

    name: str
    phone: str | None = None
    address: str | None = None


# ========================
# Seções do prompt
# ========================

_PERSONA_TEMPLATE = (
    "Você é um assistente virtual de atendimento da {business_name}.\n"
    "\n"
    "Seu papel é ajudar clientes com informações sobre serviços, preços, "
    "horários e agendamentos.\n"
    "Seja cordial, objetivo e profissional. Use linguagem informal mas respeitosa."
)

_RULES = (
    "Regras:\n"
    "- Responda SEMPRE em português brasileiro.\n"
    "- Mantenha as respostas curtas e diretas (máximo 3 parágrafos).\n"
    "- Se o cliente perguntar algo não relacionado à barbearia, recuse "
    "educadamente e redirecione.\n"
    "- Nunca invente informações que não foram fornecidas. Se não souber, "
    "diga que vai verificar.\n"
    "- Quando o cliente quiser agendar, colete: serviço desejado, data e "
    "horário preferidos."
)

_BUSINESS_DETAILS_TEMPLATE = "Informações da barbearia:\n{details}"

_CONTEXT_TEMPLATE = (
    "Use as informações abaixo para responder ao cliente. "
    "Baseie-se apenas nelas — não invente dados.\n"
    "\n"
    "{context}"
)


# ========================
# Montagem do prompt
# ========================


def _build_business_details(info: BusinessInfo) -> str:
    """Monta a seção de detalhes do negócio a partir dos dados disponíveis."""
    lines = [f"- Nome: {info.name}"]
    if info.phone:
        lines.append(f"- Telefone: {info.phone}")
    if info.address:
        lines.append(f"- Endereço: {info.address}")
    return _BUSINESS_DETAILS_TEMPLATE.format(details="\n".join(lines))


def build_system_prompt(
    business_info: BusinessInfo,
    context: str = "",
) -> str:
    """Monta o system prompt completo combinando seções e dados do negócio.

    Args:
        business_info: Dados da empresa (nome, telefone, endereço).
        context: Informações de contexto externo (ex: dados do RAG).
                 Vazio por padrão — será preenchido quando o RAG for implementado.

    Returns:
        String do system prompt pronto para uso no SystemMessage do LangChain.
    """
    sections = [
        _PERSONA_TEMPLATE.format(business_name=business_info.name),
        _build_business_details(business_info),
        _RULES,
    ]

    if context.strip():
        sections.append(_CONTEXT_TEMPLATE.format(context=context))

    return "\n\n".join(sections)
