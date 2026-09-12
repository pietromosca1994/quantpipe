from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from alpaca.common.exceptions import APIError
from ingestion.alpaca_client import AlpacaBarsClient
from quantpipe_common.config import AlpacaConfig, TickerConfig

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _raw_bar(**overrides):
    defaults = dict(timestamp=_NOW, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000)
    return SimpleNamespace(**{**defaults, **overrides})


def _api_error(status_code: int) -> APIError:
    http_error = SimpleNamespace(response=SimpleNamespace(status_code=status_code))
    return APIError('{"message": "error"}', http_error)


@pytest.fixture
def alpaca_config():
    return AlpacaConfig(api_key="key", secret_key="secret")


@pytest.fixture
def client(alpaca_config, monkeypatch):
    monkeypatch.setattr("ingestion.alpaca_client.StockHistoricalDataClient", MagicMock())
    monkeypatch.setattr("ingestion.alpaca_client.CryptoHistoricalDataClient", MagicMock())
    return AlpacaBarsClient(alpaca_config)


def test_fetch_latest_bars_routes_equities_and_crypto_to_the_right_client(client):
    client._stock_client.get_stock_bars.return_value = SimpleNamespace(
        data={"AAPL": [_raw_bar()]}
    )
    client._crypto_client.get_crypto_bars.return_value = SimpleNamespace(
        data={"BTC/USD": [_raw_bar(open=41800.0, high=42500.0, low=41500.0, close=42000.0)]}
    )
    tickers = [
        TickerConfig(symbol="AAPL", asset_class="us_equity"),
        TickerConfig(symbol="BTC/USD", asset_class="crypto"),
    ]

    bars = client.fetch_latest_bars(tickers, lookback=timedelta(minutes=5))

    assert {bar.ticker for bar in bars} == {"AAPL", "BTC/USD"}
    assert {bar.asset_class for bar in bars} == {"us_equity", "crypto"}
    client._crypto_client.get_crypto_bars.assert_called_once()
    client._stock_client.get_stock_bars.assert_called_once()


def test_fetch_latest_bars_skips_asset_class_with_no_tickers(client):
    client._stock_client.get_stock_bars.return_value = SimpleNamespace(
        data={"AAPL": [_raw_bar()]}
    )
    tickers = [TickerConfig(symbol="AAPL", asset_class="us_equity")]

    client.fetch_latest_bars(tickers, lookback=timedelta(minutes=5))

    client._crypto_client.get_crypto_bars.assert_not_called()


def test_malformed_bar_is_dropped_not_raised(client, caplog):
    client._stock_client.get_stock_bars.return_value = SimpleNamespace(
        data={"AAPL": [_raw_bar(close=None), _raw_bar()]}
    )
    tickers = [TickerConfig(symbol="AAPL", asset_class="us_equity")]

    bars = client.fetch_latest_bars(tickers, lookback=timedelta(minutes=5))

    assert len(bars) == 1
    assert "dropping malformed bar" in caplog.text


def test_bar_missing_an_attribute_is_dropped_not_raised(client, caplog):
    bad_bar = SimpleNamespace(timestamp=_NOW, open=100.0, high=101.0, low=99.0)  # no close/volume
    client._stock_client.get_stock_bars.return_value = SimpleNamespace(
        data={"AAPL": [bad_bar, _raw_bar()]}
    )
    tickers = [TickerConfig(symbol="AAPL", asset_class="us_equity")]

    bars = client.fetch_latest_bars(tickers, lookback=timedelta(minutes=5))

    assert len(bars) == 1
    assert "dropping malformed bar" in caplog.text


def test_rate_limit_error_increments_metric_and_reraises(client):
    from ingestion.metrics import ALPACA_RATE_LIMIT_HITS

    before = ALPACA_RATE_LIMIT_HITS._value.get()
    client._stock_client.get_stock_bars.side_effect = _api_error(429)
    tickers = [TickerConfig(symbol="AAPL", asset_class="us_equity")]

    with pytest.raises(APIError):
        client.fetch_latest_bars(tickers, lookback=timedelta(minutes=5))

    assert ALPACA_RATE_LIMIT_HITS._value.get() == before + 1


def test_non_rate_limit_error_does_not_increment_metric(client):
    from ingestion.metrics import ALPACA_RATE_LIMIT_HITS

    before = ALPACA_RATE_LIMIT_HITS._value.get()
    client._stock_client.get_stock_bars.side_effect = _api_error(500)
    tickers = [TickerConfig(symbol="AAPL", asset_class="us_equity")]

    with pytest.raises(APIError):
        client.fetch_latest_bars(tickers, lookback=timedelta(minutes=5))

    assert ALPACA_RATE_LIMIT_HITS._value.get() == before
