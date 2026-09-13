#!/usr/bin/env bash
# Bring up the local development stack: Docker Compose services + DB migrations.
# One-time setup (.env, the venv) is still manual — see README.md#local-development.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  echo "Missing .env — copy .env.example to .env and fill in secrets first (see README.md)." >&2
  exit 1
fi

set -a
source .env
set +a

if [ -x .venv/Scripts/python.exe ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -x .venv/bin/python ]; then
  PYTHON=".venv/bin/python"
else
  echo "Missing .venv — set it up first (see README.md#local-development, step 2)." >&2
  exit 1
fi

echo "==> Starting Docker Compose stack"
docker compose up -d --build

echo "==> Waiting for TimescaleDB to be healthy"
until [ "$(docker compose ps -q timescaledb | xargs docker inspect -f '{{.State.Health.Status}}')" = "healthy" ]; do
  sleep 2
done

echo "==> Running Alembic migrations"
(
  cd common
  POSTGRES_USER="$POSTGRES_USER" POSTGRES_PASSWORD="$POSTGRES_PASSWORD" POSTGRES_DB="$POSTGRES_DB" \
    POSTGRES_HOST=localhost POSTGRES_PORT=5432 \
    "../$PYTHON" -m alembic upgrade head
)

cat <<EOF

Stack is up:
  Grafana:    http://localhost:3000
  Prefect UI: http://localhost:4200
  MLflow:     http://localhost:5000

Edit config/tickers.yaml and restart ingestion-flows to change tracked tickers.
EOF
