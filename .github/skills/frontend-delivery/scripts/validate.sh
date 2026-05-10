#!/usr/bin/env bash
set -euo pipefail

echo "[frontend-delivery] Validacao rapida"
if [[ -d "frontend" ]]; then
  echo "- estrutura frontend encontrada"
else
  echo "- frontend nao encontrado" && exit 1
fi
if [[ -f "frontend/package.json" ]]; then
  echo "- package.json encontrado"
fi
echo "- execute build do frontend apos alteracoes"
