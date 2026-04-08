from itertools import groupby

from app.models.knowledge_document import KnowledgeDocument

CATEGORY_LABELS: dict[str, str] = {
    "services": "Serviços",
    "hours": "Horário de Funcionamento",
    "policies": "Políticas",
    "faq": "Perguntas Frequentes",
    "general": "Informações Gerais",
}


def format_knowledge_context(documents: list[KnowledgeDocument]) -> str:
    """Formata documentos da base de conhecimento em texto para o prompt.

    Agrupa por categoria com labels em PT-BR. Retorna string vazia se
    a lista estiver vazia.
    """
    if not documents:
        return ""

    sections: list[str] = []

    for category, docs in groupby(documents, key=lambda d: d.category.value):
        label = CATEGORY_LABELS.get(category, category)
        lines = [f"[{label}]"]
        for doc in docs:
            lines.append(f"- {doc.title}: {doc.content}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
