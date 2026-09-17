from __future__ import annotations

import os

from prometheus_client import CollectorRegistry, Counter, Histogram, multiprocess, start_http_server

# Must exist before any Counter/Histogram below is constructed — prometheus_client
# opens each metric's mmap file eagerly at construction time, not on first .inc().
# Every process that imports this module (the long-lived serve() process and each
# flow-run subprocess it spawns — see start_metrics_server) needs this to exist;
# only the entrypoint clears stale files from a previous container run, in
# services/prefect_flows/deployments.py, before this module is ever imported.
_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if _multiproc_dir:
    os.makedirs(_multiproc_dir, exist_ok=True)

INGEST_ROWS_WRITTEN = Counter(
    "quantpipe_ingest_rows_written_total",
    "Rows upserted into bars_1m",
)
INGEST_ERRORS = Counter(
    "quantpipe_ingest_errors_total",
    "Ingestion cycle failures",
)
ALPACA_RATE_LIMIT_HITS = Counter(
    "quantpipe_alpaca_rate_limit_hits_total",
    "Alpaca API rate-limit responses encountered",
)
INGEST_CYCLE_SECONDS = Histogram(
    "quantpipe_ingest_cycle_duration_seconds",
    "Ingestion cycle duration",
)


def start_metrics_server(port: int = 8000) -> None:
    """Expose the above counters on /metrics for Prometheus to scrape.

    Prefect's Runner (serve()) executes each ingest_bars flow run in its own
    spawned subprocess, so the .inc()/.time() calls inside it update that
    subprocess's own in-memory metric state, not this long-lived process's —
    without multiprocess mode the counters exposed here would stay at zero
    forever. PROMETHEUS_MULTIPROC_DIR (set in docker-compose.yml) makes every
    process write its deltas to files instead; MultiProcessCollector sums
    them back up here on every scrape.
    """
    if not _multiproc_dir:
        start_http_server(port)
        return

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    start_http_server(port, registry=registry)
