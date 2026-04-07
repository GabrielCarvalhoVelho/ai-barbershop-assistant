from app.modules.ai.prompts import BusinessInfo, build_system_prompt


def _info_full():
    return BusinessInfo(
        name="Barbearia do João",
        phone="(11) 99999-0000",
        address="Rua das Flores, 123",
    )


def _info_name_only():
    return BusinessInfo(name="Barbearia Teste")


# ========================
# BusinessInfo
# ========================


class TestBusinessInfo:
    def test_creates_with_all_fields(self):
        info = _info_full()
        assert info.name == "Barbearia do João"
        assert info.phone == "(11) 99999-0000"
        assert info.address == "Rua das Flores, 123"

    def test_creates_with_name_only(self):
        info = _info_name_only()
        assert info.name == "Barbearia Teste"
        assert info.phone is None
        assert info.address is None

    def test_is_immutable(self):
        info = _info_full()
        try:
            info.name = "Outro nome"
            assert False, "Deveria ter levantado FrozenInstanceError"
        except AttributeError:
            pass


# ========================
# build_system_prompt — seções obrigatórias
# ========================


class TestBuildSystemPromptRequiredSections:
    def test_contains_business_name(self):
        prompt = build_system_prompt(_info_full())
        assert "Barbearia do João" in prompt

    def test_contains_persona(self):
        prompt = build_system_prompt(_info_name_only())
        assert "assistente virtual de atendimento" in prompt

    def test_contains_rules(self):
        prompt = build_system_prompt(_info_name_only())
        assert "português brasileiro" in prompt
        assert "máximo 3 parágrafos" in prompt

    def test_contains_business_details_section(self):
        prompt = build_system_prompt(_info_name_only())
        assert "Informações da barbearia:" in prompt
        assert "- Nome: Barbearia Teste" in prompt


# ========================
# build_system_prompt — dados opcionais
# ========================


class TestBuildSystemPromptOptionalData:
    def test_includes_phone_when_present(self):
        prompt = build_system_prompt(_info_full())
        assert "Telefone: (11) 99999-0000" in prompt

    def test_includes_address_when_present(self):
        prompt = build_system_prompt(_info_full())
        assert "Endereço: Rua das Flores, 123" in prompt

    def test_omits_phone_when_none(self):
        prompt = build_system_prompt(_info_name_only())
        assert "Telefone" not in prompt

    def test_omits_address_when_none(self):
        prompt = build_system_prompt(_info_name_only())
        assert "Endereço" not in prompt

    def test_partial_data_phone_only(self):
        info = BusinessInfo(name="Corte Certo", phone="(21) 3333-4444")
        prompt = build_system_prompt(info)
        assert "Telefone: (21) 3333-4444" in prompt
        assert "Endereço" not in prompt

    def test_partial_data_address_only(self):
        info = BusinessInfo(name="Corte Certo", address="Av. Brasil, 500")
        prompt = build_system_prompt(info)
        assert "Endereço: Av. Brasil, 500" in prompt
        assert "Telefone" not in prompt


# ========================
# build_system_prompt — contexto externo (RAG)
# ========================


class TestBuildSystemPromptContext:
    def test_no_context_by_default(self):
        prompt = build_system_prompt(_info_name_only())
        assert "Use as informações abaixo" not in prompt

    def test_empty_context_omitted(self):
        prompt = build_system_prompt(_info_name_only(), context="")
        assert "Use as informações abaixo" not in prompt

    def test_whitespace_only_context_omitted(self):
        prompt = build_system_prompt(_info_name_only(), context="   \n  ")
        assert "Use as informações abaixo" not in prompt

    def test_context_included_when_present(self):
        context = "Corte masculino: R$40\nBarba: R$25"
        prompt = build_system_prompt(_info_name_only(), context=context)
        assert "Use as informações abaixo" in prompt
        assert "Corte masculino: R$40" in prompt
        assert "Barba: R$25" in prompt

    def test_context_appears_after_rules(self):
        context = "Horário: 9h-18h"
        prompt = build_system_prompt(_info_name_only(), context=context)
        rules_pos = prompt.index("Regras:")
        context_pos = prompt.index("Horário: 9h-18h")
        assert context_pos > rules_pos


# ========================
# build_system_prompt — estrutura geral
# ========================


class TestBuildSystemPromptStructure:
    def test_sections_separated_by_blank_lines(self):
        prompt = build_system_prompt(_info_full())
        assert "\n\n" in prompt

    def test_returns_string(self):
        prompt = build_system_prompt(_info_name_only())
        assert isinstance(prompt, str)

    def test_not_empty(self):
        prompt = build_system_prompt(_info_name_only())
        assert len(prompt) > 0

    def test_full_prompt_combines_all_sections(self):
        context = "Serviços: corte, barba"
        prompt = build_system_prompt(_info_full(), context=context)
        assert "Barbearia do João" in prompt
        assert "Informações da barbearia:" in prompt
        assert "Regras:" in prompt
        assert "Serviços: corte, barba" in prompt
