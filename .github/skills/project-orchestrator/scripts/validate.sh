#!/usr/bin/env bash
set -euo pipefail

echo "[project-orchestrator] Validacao de consistencia"
if [[ -d "backend" ]]; then
  echo "- backend detectado"
fi
if [[ -d "frontend" ]]; then
  echo "- frontend detectado"
fi
echo "- checklist recomendado: assets/checklist.md"
