#!/bin/sh
set -e

echo "[entrypoint] Aplicando migrações Alembic..."
alembic upgrade head

echo "[entrypoint] Iniciando aplicação: $*"
exec "$@"
