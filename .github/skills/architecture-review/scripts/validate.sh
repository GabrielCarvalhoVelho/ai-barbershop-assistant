#!/bin/bash
# Validador de contexto para architecture-review skill
# Confirma que decisões e biblias existem para consulta

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
GITHUB_DIR="${REPO_ROOT}/.github"
ERRORS=0

log_error() {
    echo "❌ $1" >&2
    ((ERRORS++))
}

log_ok() {
    echo "✅ $1"
}

echo "[architecture-review] Validação de contexto"

# Verificar que decisões existem
if [[ ! -f "${GITHUB_DIR}/decisions.md" ]]; then
    log_error "Arquivo decisions.md não encontrado"
else
    log_ok "decisions.md encontrado"
fi

# Verificar que project-bible existe
if [[ ! -f "${GITHUB_DIR}/project-bible.md" ]]; then
    log_error "Arquivo project-bible.md não encontrado"
else
    log_ok "project-bible.md encontrado"
fi

# Verificar que estrutura backend existe
if [[ ! -d "${REPO_ROOT}/backend/app/modules" ]]; then
    log_error "Estrutura backend (app/modules) não encontrada"
else
    log_ok "Estrutura backend encontrada"
fi

# Verificar que estrutura frontend existe
if [[ ! -d "${REPO_ROOT}/frontend/src" ]]; then
    log_error "Estrutura frontend (src) não encontrada"
else
    log_ok "Estrutura frontend encontrada"
fi

# Verificar que migrations existem
if [[ ! -d "${REPO_ROOT}/backend/migrations/versions" ]]; then
    log_error "Diretório de migrations não encontrado"
else
    log_ok "Diretório de migrations encontrado"
fi

# Resumo
echo ""
if [[ $ERRORS -eq 0 ]]; then
    echo "✅ Contexto de architecture-review disponível"
    echo "   Pronto para avaliar decisões arquiteturais."
    exit 0
else
    echo "❌ Problemas encontrados: $ERRORS"
    exit 1
fi
