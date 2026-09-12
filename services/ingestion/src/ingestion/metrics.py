from __future__ import annotations

from prometheus_client import Counter, Histogram, start_http_server

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
    """Expose the above counters on /metrics for Prometheus to scrape."""
    start_http_server(port)
