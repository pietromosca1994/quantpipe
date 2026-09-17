"""Schedules for all QuantPipe flows, centralized and kept separate from flow logic.

Run this module as a long-lived process (see docker-compose.yml's `ingestion-flows`
service) to keep every deployment below scheduled and served.
"""

from __future__ import annotations

import logging
import os
import shutil

# Must run before any ingestion.* import below — they transitively import
# ingestion.metrics, which constructs its Counters/Histogram (and thus opens
# their PROMETHEUS_MULTIPROC_DIR value files) at module-import time. This is
# the one place in the process tree that should wipe stale files left behind
# by a previous container run: every flow-run subprocess serve() spawns
# re-imports ingestion.metrics too, and wiping there would race the still-
# running main process (and any sibling in-flight subprocess).
_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if _multiproc_dir:
    shutil.rmtree(_multiproc_dir, ignore_errors=True)

from ingestion.backfill import backfill  # noqa: E402
from ingestion.flow import ingest_bars  # noqa: E402
from ingestion.metrics import start_metrics_server  # noqa: E402
from prefect import serve  # noqa: E402

logger = logging.getLogger(__name__)

INGEST_BARS_INTERVAL_SECONDS = 120
METRICS_PORT = 8000

# ingest_bars only looks back FETCH_LOOKBACK (10 minutes), so any downtime
# between this process stopping and restarting (crash, redeploy, VM reboot)
# would otherwise leave a permanent gap in bars_1m. A few days comfortably
# covers realistic downtime while staying cheap to re-run on every restart —
# backfill() upserts on (time, ticker), so re-fetching already-ingested bars
# is a no-op.
STARTUP_BACKFILL_DAYS = 3


def main() -> None:
    # This process is what actually runs in docker-compose (see the
    # ingestion-flows service) — start the /metrics endpoint here, not in
    # flow.py's __main__, since that path isn't used when serve()d.
    start_metrics_server(port=METRICS_PORT)

    try:
        backfill(days=STARTUP_BACKFILL_DAYS)
    except Exception:
        # Don't let a startup backfill failure (e.g. Alpaca down, bad creds)
        # crash-loop the whole ingestion service — periodic ingest_bars still
        # runs on schedule below and will keep the gap from growing further.
        logger.exception("startup backfill failed; continuing without it")

    ingest_deployment = ingest_bars.to_deployment(
        name="ingest-bars",
        interval=INGEST_BARS_INTERVAL_SECONDS,
    )

    # Future deployments, added once services/training and services/inference exist:
    #
    # from training.flow import train_model
    # train_1h_deployment = train_model.to_deployment(
    #     name="train-model-1h",
    #     cron="0 3 * * 1",  # weekly — matched to the 1h timeframe's retrain cadence
    # )
    #
    # from inference.flow import predict
    # predict_1h_deployment = predict.to_deployment(
    #     name="predict-1h",
    #     cron="1 * * * *",  # a few seconds after each hour boundary
    # )
    #
    # serve(ingest_deployment, train_1h_deployment, predict_1h_deployment)

    serve(ingest_deployment)


if __name__ == "__main__":
    main()
