from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from alpaca.common.exceptions import APIError
from alpaca.data.enums import DataFeed
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from pydantic import ValidationError
from quantpipe_common.config import AlpacaConfig, TickerConfig
from quantpipe_common.enums import AssetClass, Source
from quantpipe_common.schemas import Bar

from ingestion.metrics import ALPACA_RATE_LIMIT_HITS

logger = logging.getLogger(__name__)

RATE_LIMIT_STATUS_CODE = 429

# Malformed provider data (a missing field, a null price, a wrong type) should
# drop that one bar, not abort the whole batch — every exception a bad raw
# bar could realistically raise while being converted is caught here.
_MALFORMED_BAR_ERRORS = (ValidationError, AttributeError, TypeError, KeyError)


def _bar_from_raw(symbol: str, raw: Any, asset_class: AssetClass) -> Bar | None:
    try:
        return Bar(
            time=raw.timestamp,
            ticker=symbol,
            asset_class=asset_class,
            open=raw.open,
            high=raw.high,
            low=raw.low,
            close=raw.close,
            volume=raw.volume,
            source=Source.ALPACA,
        )
    except _MALFORMED_BAR_ERRORS:
        logger.warning(
            "ingestion: dropping malformed bar for %s at %s", symbol, getattr(raw, "timestamp", "?")
        )
        return None


class AlpacaBarsClient:
    """Thin wrapper over alpaca-py's Market Data API, returning validated Bar objects."""

    def __init__(self, config: AlpacaConfig) -> None:
        api_key = config.api_key.get_secret_value()
        secret_key = config.secret_key.get_secret_value()
        self._stock_client = StockHistoricalDataClient(api_key, secret_key)
        self._crypto_client = CryptoHistoricalDataClient(api_key, secret_key)
        self._feed = DataFeed(config.feed)

    def fetch_latest_bars(self, tickers: Sequence[TickerConfig], lookback: timedelta) -> list[Bar]:
        end = datetime.now(UTC)
        start = end - lookback
        return self.fetch_bars_range(tickers, start=start, end=end)

    def fetch_bars_range(
        self, tickers: Sequence[TickerConfig], start: datetime, end: datetime
    ) -> list[Bar]:
        equities = [t.symbol for t in tickers if t.asset_class == AssetClass.US_EQUITY]
        cryptos = [t.symbol for t in tickers if t.asset_class == AssetClass.CRYPTO]

        bars: list[Bar] = []
        if equities:
            bars.extend(
                self._fetch_bars(
                    self._stock_client.get_stock_bars,
                    StockBarsRequest,
                    equities,
                    start,
                    end,
                    AssetClass.US_EQUITY,
                )
            )
        if cryptos:
            bars.extend(
                self._fetch_bars(
                    self._crypto_client.get_crypto_bars,
                    CryptoBarsRequest,
                    cryptos,
                    start,
                    end,
                    AssetClass.CRYPTO,
                )
            )
        return bars

    def _fetch_bars(
        self,
        get_bars: Callable[[StockBarsRequest | CryptoBarsRequest], Any],
        request_cls: type[StockBarsRequest] | type[CryptoBarsRequest],
        symbols: list[str],
        start: datetime,
        end: datetime,
        asset_class: AssetClass,
    ) -> list[Bar]:
        kwargs: dict[str, Any] = dict(
            symbol_or_symbols=symbols, timeframe=TimeFrame.Minute, start=start, end=end
        )
        if request_cls is StockBarsRequest:
            kwargs["feed"] = self._feed
        request = request_cls(**kwargs)
        try:
            response = get_bars(request)
        except APIError as exc:
            # Never log exc.request/exc.response here — they carry the raw
            # APCA-API-KEY-ID/APCA-API-SECRET-KEY headers. exc.status_code and
            # str(exc) (the JSON error body) are safe to log.
            if exc.status_code == RATE_LIMIT_STATUS_CODE:
                ALPACA_RATE_LIMIT_HITS.inc()
            raise
        return self._to_bars(response.data, asset_class=asset_class)

    @staticmethod
    def _to_bars(data: dict[str, list[Any]], asset_class: AssetClass) -> list[Bar]:
        bars: list[Bar] = []
        for symbol, raw_bars in data.items():
            for raw in raw_bars:
                bar = _bar_from_raw(symbol, raw, asset_class)
                if bar is not None:
                    bars.append(bar)
        return bars
