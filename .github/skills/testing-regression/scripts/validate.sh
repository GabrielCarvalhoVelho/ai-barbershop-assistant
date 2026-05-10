#!/usr/bin/env bash
set -euo pipefail

echo "[testing-regression] Validacao rapida"
if [[ -d "backend/tests" ]]; then
  echo "- suite backend detectada"
fi
if compgen -G "frontend/**/*.{test,spec}.{ts,tsx,js,jsx}" > /dev/null; then
  echo "- testes frontend detectados"
else
  echo "- nenhum padrao test/spec frontend detectado"
fi
echo "- priorize regressao + caminho feliz + erro relevante"
