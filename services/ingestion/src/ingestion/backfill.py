"""Historical backfill for bars_1m.

The periodic ingest-bars flow only looks back FETCH_LOOKBACK (10 minutes), so
it never fills in history on its own. Run this manually against a fresh
database to provision it with history before periodic ingestion starts
covering new bars going forward — see scripts/backfill.sh. It's also called
automatically on every ingestion-flows startup (services/prefect_flows/deployments.py)
to close any gap left by downtime. Safe to re-run: it upserts on (time,
ticker) the same way the periodic flow does.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime, timedelta

from quantpipe_common.config import AlpacaConfig, AppConfig
from quantpipe_common.schemas import Bar

from ingestion.alpaca_client import AlpacaBarsClient
from ingestion.flow import DEFAULT_TICKERS_CONFIG_PATH, upsert_bars

logger = logging.getLogger(__name__)

DEFAULT_BACKFILL_DAYS = 30
UPSERT_BATCH_SIZE = 2000


def _batches(bars: list[Bar], size: int) -> list[list[Bar]]:
    return [bars[i : i + size] for i in range(0, len(bars), size)]


def backfill(config_path: str = DEFAULT_TICKERS_CONFIG_PATH, days: int = DEFAULT_BACKFILL_DAYS) -> int:
    app_config = AppConfig.from_yaml(config_path)
    client = AlpacaBarsClient(AlpacaConfig())

    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    bars = client.fetch_bars_range(app_config.tickers, start=start, end=end)

    # A single multi-week, multi-ticker backfill can be tens of thousands of
    # rows — batch the upsert instead of one giant INSERT statement.
    written = sum(upsert_bars.fn(batch) for batch in _batches(bars, UPSERT_BATCH_SIZE))
    logger.info("backfill: wrote %d rows across %d day(s) of history", written, days)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_TICKERS_CONFIG_PATH, help="Path to tickers.yaml")
    parser.add_argument(
        "--days", type=int, default=DEFAULT_BACKFILL_DAYS, help="How many days of history to backfill"
    )
    args = parser.parse_args()

    # force=True: alpaca-py/Prefect may already have configured the root
    # logger by the time this runs, which would otherwise make basicConfig a
    # no-op and silently swallow this script's own progress output.
    logging.basicConfig(level=logging.INFO, force=True)
    backfill(config_path=args.config, days=args.days)


if __name__ == "__main__":
    main()
