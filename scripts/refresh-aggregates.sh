#!/usr/bin/env bash
# One-off refresh of the bars_5m/15m/1h/1d continuous aggregates over their
# full range. Each aggregate only catches up to bars_1m on its own schedule
# (5m/15m/1h/1 day — see the add_continuous_aggregate_policy calls in
# common/quantpipe_common/db/migrations/versions/0001_initial_schema.py), so
# after a bulk backfill (scripts/backfill.sh) the coarser timeframes can lag
# behind by up to that long. Run this to make them available immediately
# instead of waiting. Safe to re-run: refreshing is idempotent.
#
# Usage: ./scripts/refresh-aggregates.sh
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  echo "Missing .env — copy .env.example to .env and fill in secrets first (see README.md)." >&2
  exit 1
fi

set -a
source .env
set +a

if [ "$(docker compose ps -q timescaledb)" = "" ]; then
  echo "timescaledb isn't running — start the stack first (see scripts/dev-up.sh)." >&2
  exit 1
fi

# Kept in sync with _AGGREGATES in 0001_initial_schema.py — these are the
# only continuous aggregates derived from bars_1m.
AGGREGATES=(bars_5m bars_15m bars_1h bars_1d)

for view in "${AGGREGATES[@]}"; do
  echo "==> Refreshing $view"
  docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "CALL refresh_continuous_aggregate('$view', NULL, NULL);"
done
