#!/usr/bin/env bash
set -euo pipefail

echo "[mobile-planning] Validacao de contexto"
if [[ -d "backend" ]]; then
  echo "- APIs backend disponiveis para integracao mobile"
fi
if [[ -d "frontend" ]]; then
  echo "- referencia web existente para mapear fluxos"
fi
echo "- gere roadmap MVP com fases e riscos"
