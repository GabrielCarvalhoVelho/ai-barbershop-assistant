#!/usr/bin/env bash
set -euo pipefail

echo "[backend-delivery] Validacao rapida"
if [[ -d "backend" ]]; then
  echo "- estrutura backend encontrada"
else
  echo "- backend nao encontrado" && exit 1
fi
if [[ -f "backend/pytest.ini" ]]; then
  echo "- pytest.ini encontrado"
fi
echo "- execute testes do modulo alterado"
