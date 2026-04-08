from types import SimpleNamespace

from app.models.enums import DocumentCategory
from app.modules.ai.context_service import CATEGORY_LABELS, format_knowledge_context


def _doc(
    title: str = "Corte masculino",
    content: str = "R$ 40,00",
    category: DocumentCategory = DocumentCategory.SERVICES,
):
    return SimpleNamespace(title=title, content=content, category=category)


# ========================
# Formatação de contexto
# ========================


class TestFormatKnowledgeContext:
    def test_empty_list_returns_empty_string(self):
        assert format_knowledge_context([]) == ""

    def test_single_document(self):
        result = format_knowledge_context([_doc()])
        assert "[Serviços]" in result
        assert "- Corte masculino: R$ 40,00" in result

    def test_multiple_docs_same_category(self):
        docs = [
            _doc(title="Corte", content="R$ 40"),
            _doc(title="Barba", content="R$ 30"),
        ]
        result = format_knowledge_context(docs)
        assert result.count("[Serviços]") == 1
        assert "- Corte: R$ 40" in result
        assert "- Barba: R$ 30" in result

    def test_groups_by_category(self):
        docs = [
            _doc(category=DocumentCategory.SERVICES),
            _doc(title="Horário", content="9h-19h", category=DocumentCategory.HOURS),
        ]
        result = format_knowledge_context(docs)
        assert "[Serviços]" in result
        assert "[Horário de Funcionamento]" in result

    def test_all_five_categories(self):
        docs = [
            _doc(category=DocumentCategory.SERVICES),
            _doc(category=DocumentCategory.HOURS),
            _doc(category=DocumentCategory.POLICIES),
            _doc(category=DocumentCategory.FAQ),
            _doc(category=DocumentCategory.GENERAL),
        ]
        result = format_knowledge_context(docs)
        for label in CATEGORY_LABELS.values():
            assert f"[{label}]" in result

    def test_category_labels_in_portuguese(self):
        assert CATEGORY_LABELS["services"] == "Serviços"
        assert CATEGORY_LABELS["hours"] == "Horário de Funcionamento"
        assert CATEGORY_LABELS["policies"] == "Políticas"
        assert CATEGORY_LABELS["faq"] == "Perguntas Frequentes"
        assert CATEGORY_LABELS["general"] == "Informações Gerais"

    def test_bullet_format(self):
        result = format_knowledge_context([_doc(title="Barba", content="R$ 30")])
        lines = result.strip().split("\n")
        assert lines[1] == "- Barba: R$ 30"

    def test_categories_separated_by_blank_line(self):
        docs = [
            _doc(category=DocumentCategory.SERVICES),
            _doc(title="Horário", content="9h-19h", category=DocumentCategory.HOURS),
        ]
        result = format_knowledge_context(docs)
        assert "\n\n" in result

    def test_preserves_document_order(self):
        docs = [
            _doc(title="Primeiro", content="1"),
            _doc(title="Segundo", content="2"),
        ]
        result = format_knowledge_context(docs)
        idx_first = result.index("Primeiro")
        idx_second = result.index("Segundo")
        assert idx_first < idx_second
