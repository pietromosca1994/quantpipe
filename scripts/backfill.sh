#!/usr/bin/env bash
# One-off historical backfill of bars_1m. Run once (before or after starting
# the stack) so dashboards have history instead of only what accumulates from
# periodic ingestion going forward — its lookback is only 5 minutes. Safe to
# re-run: upserts on (time, ticker) the same way periodic ingestion does.
#
# Usage: ./scripts/backfill.sh [--days N] [--config path/to/tickers.yaml]
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

echo "==> Backfilling bars_1m"
# TimescaleDB is reached via localhost:5432 (docker-compose.override.yml's
# published port), not the .env default of the in-network hostname "timescaledb".
PYTHONPATH="services/ingestion/src" POSTGRES_HOST=localhost POSTGRES_PORT=5432 \
  "$PYTHON" -m ingestion.backfill "$@"
