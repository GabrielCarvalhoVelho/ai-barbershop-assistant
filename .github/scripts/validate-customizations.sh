#!/bin/bash
# Validador centralizado para customizações do Copilot
# Verifica:
# - Nomes de agents/skills batem com pastas
# - Frontmatter YAML correto
# - Links relativos existem
# - Skills têm assets/references/scripts

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
GITHUB_DIR="${REPO_ROOT}/.github"
ERRORS=0
WARNINGS=0

# Cores
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

log_error() {
    echo -e "${RED}✗ ERROR${NC}: $1" >&2
    ((ERRORS++))
}

log_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1" >&2
    ((WARNINGS++))
}

log_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

# 1. Validar que instructions existem e têm frontmatter
validate_instructions() {
    echo "=== Validando Instructions ==="
    
    local required_instructions=(
        "base.instructions.md"
        "backend-python.instructions.md"
        "frontend-react.instructions.md"
        "testing.instructions.md"
        "security-lgpd.instructions.md"
        "migrations-alembic.instructions.md"
        "api-contract.instructions.md"
    )
    
    for instr in "${required_instructions[@]}"; do
        local file="${GITHUB_DIR}/instructions/${instr}"
        if [[ ! -f "$file" ]]; then
            log_error "Instruction ausente: $file"
        else
            # Validar frontmatter básico
            if ! head -1 "$file" | grep -q "^---"; then
                log_error "Instruction sem frontmatter: $file"
            else
                log_ok "Instruction encontrada: $instr"
            fi
        fi
    done
}

# 2. Validar que agents batem com pastas
validate_agents() {
    echo "=== Validando Agents ==="
    
    local required_agents=(
        "main-orchestrator"
        "backend-specialist"
        "frontend-specialist"
        "testing-specialist"
        "mobile-specialist"
        "review-specialist"
    )
    
    for agent in "${required_agents[@]}"; do
        local file="${GITHUB_DIR}/agents/${agent}.agent.md"
        if [[ ! -f "$file" ]]; then
            log_error "Agent ausente: $file"
        else
            # Validar frontmatter
            if ! head -1 "$file" | grep -q "^---"; then
                log_error "Agent sem frontmatter: $file"
            else
                # Extrair nome do frontmatter
                local agent_name=$(grep "^name:" "$file" | head -1 | sed 's/^name: *"//' | sed 's/"$//')
                if [[ "$agent_name" != "$agent" ]]; then
                    log_warn "Agent name mismatch em $file: esperado '$agent', encontrado '$agent_name'"
                else
                    log_ok "Agent validado: $agent"
                fi
            fi
        fi
    done
}

# 3. Validar que skills existem, têm estrutura correta e assets
validate_skills() {
    echo "=== Validando Skills ==="
    
    local skills_dir="${GITHUB_DIR}/skills"
    
    if [[ ! -d "$skills_dir" ]]; then
        log_error "Pasta de skills não existe: $skills_dir"
        return
    fi
    
    # Iterar sobre pastas de skills
    for skill_dir in "$skills_dir"/*; do
        if [[ ! -d "$skill_dir" ]]; then
            continue
        fi
        
        local skill_name=$(basename "$skill_dir")
        local skill_file="${skill_dir}/SKILL.md"
        
        # Verificar SKILL.md existe
        if [[ ! -f "$skill_file" ]]; then
            log_error "Skill sem SKILL.md: $skill_name"
        else
            # Validar frontmatter
            if ! head -1 "$skill_file" | grep -q "^---"; then
                log_error "Skill sem frontmatter: $skill_name/SKILL.md"
            else
                log_ok "Skill encontrada: $skill_name"
            fi
        fi
        
        # Verificar assets obrigatórios
        local required_assets=(
            "assets/checklist.md"
            "references/guide.md"
            "scripts/validate.sh"
        )
        
        for asset in "${required_assets[@]}"; do
            local asset_file="${skill_dir}/${asset}"
            if [[ ! -f "$asset_file" ]]; then
                log_error "Skill $skill_name missing: $asset"
            else
                log_ok "Skill $skill_name tem $asset"
            fi
        done
        
        # Validar que validate.sh é executável
        local validate_script="${skill_dir}/scripts/validate.sh"
        if [[ -f "$validate_script" ]]; then
            if [[ ! -x "$validate_script" ]]; then
                log_warn "Skill $skill_name validate.sh não é executável"
            fi
        fi
    done
}

# 4. Validar prompts têm frontmatter
validate_prompts() {
    echo "=== Validando Prompts ==="
    
    local prompts_dir="${GITHUB_DIR}/prompts"
    
    if [[ ! -d "$prompts_dir" ]]; then
        log_error "Pasta de prompts não existe: $prompts_dir"
        return
    fi
    
    for prompt_file in "$prompts_dir"/*.prompt.md; do
        if [[ ! -f "$prompt_file" ]]; then
            continue
        fi
        
        local prompt_name=$(basename "$prompt_file")
        
        # Validar frontmatter básico
        if ! head -1 "$prompt_file" | grep -q "^---"; then
            log_error "Prompt sem frontmatter: $prompt_name"
        else
            log_ok "Prompt validado: $prompt_name"
        fi
    done
}

# 5. Validar links em base.instructions.md
validate_links() {
    echo "=== Validando Links em base.instructions.md ==="
    
    local base_file="${GITHUB_DIR}/instructions/base.instructions.md"
    
    if [[ ! -f "$base_file" ]]; then
        log_error "Arquivo base não existe: $base_file"
        return
    fi
    
    # Extrair todos os paths relativos (./)
    while IFS= read -r line; do
        # Procura por linhas com paths tipo ./...
        if [[ $line =~ \./\.github/ ]]; then
            # Extrai o path (compatível com macOS BSD grep)
            local path=$(echo "$line" | grep -oE '\./\.github/[^ `]+' | head -1)
            if [[ -n "$path" ]]; then
                local full_path="${REPO_ROOT}/${path}"
                # Remove trailing * ou / se for glob
                full_path="${full_path%\*}"
                full_path="${full_path%/}"
                
                if [[ ! -e "$full_path" ]]; then
                    log_error "Link quebrado em base.instructions.md: $path"
                fi
            fi
        fi
    done < "$base_file"
    
    log_ok "Links validados"
}

# 6. Validar que project-bible.md e decisions.md existem
validate_core_docs() {
    echo "=== Validando Documentação Central ==="
    
    local docs=(
        "project-bible.md"
        "decisions.md"
    )
    
    for doc in "${docs[@]}"; do
        local file="${GITHUB_DIR}/${doc}"
        if [[ ! -f "$file" ]]; then
            log_error "Documentação central ausente: $file"
        else
            log_ok "Documentação encontrada: $doc"
        fi
    done
}

# Main
main() {
    echo "🔍 Validando customizações do Copilot em ${REPO_ROOT}"
    echo ""
    
    validate_instructions
    echo ""
    
    validate_agents
    echo ""
    
    validate_skills
    echo ""
    
    validate_prompts
    echo ""
    
    validate_links
    echo ""
    
    validate_core_docs
    echo ""
    
    # Resumo
    echo "================================================"
    if [[ $ERRORS -eq 0 ]]; then
        echo -e "${GREEN}✓ Todas as validações passaram!${NC}"
        echo "Warnings: $WARNINGS"
        exit 0
    else
        echo -e "${RED}✗ Validações falharam${NC}"
        echo "Errors: $ERRORS"
        echo "Warnings: $WARNINGS"
        exit 1
    fi
}

main "$@"
