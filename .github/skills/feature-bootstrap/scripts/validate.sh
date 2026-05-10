#!/usr/bin/env bash
set -euo pipefail

echo "[feature-bootstrap] Validacao rapida"
if [[ -f ".github/project-bible.md" ]]; then
  echo "- biblia do projeto encontrada"
else
  echo "- biblia do projeto ausente" && exit 1
fi
if [[ -d ".github/skills/backend-delivery" && -d ".github/skills/frontend-delivery" && -d ".github/skills/testing-regression" ]]; then
  echo "- skills principais encontradas"
fi
echo "- checklist recomendado: assets/checklist.md"
