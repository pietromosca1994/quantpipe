from __future__ import annotations

import logging
from datetime import timedelta

from prefect import flow, task
from quantpipe_common.config import AlpacaConfig, AppConfig, TickerConfig
from quantpipe_common.db.models import Bar as BarORM
from quantpipe_common.db.session import session_scope
from quantpipe_common.schemas import Bar
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ingestion.alpaca_client import AlpacaBarsClient
from ingestion.metrics import INGEST_CYCLE_SECONDS, INGEST_ERRORS, INGEST_ROWS_WRITTEN

logger = logging.getLogger(__name__)

DEFAULT_TICKERS_CONFIG_PATH = "config/tickers.yaml"
FETCH_LOOKBACK = timedelta(minutes=10)


@task(retries=3, retry_delay_seconds=10)
def fetch_bars(client: AlpacaBarsClient, tickers: list[TickerConfig]) -> list[Bar]:
    return client.fetch_latest_bars(tickers, lookback=FETCH_LOOKBACK)


@task(retries=2, retry_delay_seconds=5)
def upsert_bars(bars: list[Bar]) -> int:
    if not bars:
        return 0

    # ON CONFLICT DO UPDATE can't affect the same row twice in one statement —
    # Postgres raises CardinalityViolation if two bars share (time, ticker)
    # (e.g. a ticker misconfigured under both asset classes). Keep the last
    # occurrence rather than let one bad config entry fail the whole cycle.
    deduped = {(bar.time, bar.ticker): bar for bar in bars}
    rows = [bar.model_dump() for bar in deduped.values()]
    with session_scope() as session:
        stmt = pg_insert(BarORM).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[BarORM.time, BarORM.ticker],
            set_={
                "asset_class": stmt.excluded.asset_class,
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "source": stmt.excluded.source,
            },
        )
        session.execute(stmt)
    return len(rows)


@flow(name="ingest-bars")
def ingest_bars(config_path: str = DEFAULT_TICKERS_CONFIG_PATH) -> int:
    """Fetch the latest 1-minute bars for every configured ticker and upsert into bars_1m.

    This is the only ingestion path — bars_5m/15m/1h/1d are TimescaleDB continuous
    aggregates derived from bars_1m, never written here.
    """
    with INGEST_CYCLE_SECONDS.time():
        try:
            app_config = AppConfig.from_yaml(config_path)
            client = AlpacaBarsClient(AlpacaConfig())
            bars = fetch_bars(client, app_config.tickers)
            written = upsert_bars(bars)
        except Exception:
            INGEST_ERRORS.inc()
            logger.exception("ingest-bars: cycle failed")
            raise

    INGEST_ROWS_WRITTEN.inc(written)
    logger.info("ingest-bars: wrote %d rows", written)
    return written


if __name__ == "__main__":
    # Manual/ad-hoc single-cycle entrypoint (see services/ingestion/Dockerfile) —
    # the process exits right after this, so there's no persistent /metrics
    # endpoint here to scrape. The scheduled production path is
    # services/prefect_flows/deployments.py, which starts the metrics server
    # once and keeps it alive for the life of that long-running process.
    ingest_bars()
