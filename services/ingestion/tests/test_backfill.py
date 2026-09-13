from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from ingestion import backfill as backfill_module
from ingestion import flow as flow_module
from quantpipe_common.schemas import Bar

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _bar(ticker: str = "AAPL") -> Bar:
    return Bar(
        time=_NOW,
        ticker=ticker,
        asset_class="us_equity",
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000,
    )


@pytest.fixture
def mock_session_scope(monkeypatch):
    mock_session = MagicMock()

    @contextmanager
    def fake_session_scope():
        yield mock_session

    monkeypatch.setattr(flow_module, "session_scope", fake_session_scope)
    return mock_session


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "tickers.yaml"
    path.write_text(
        """
tickers:
  - symbol: AAPL
    asset_class: us_equity
"""
    )
    return str(path)


def test_backfill_fetches_the_requested_day_range_and_upserts(
    config_path, mock_session_scope, monkeypatch
):
    fake_client_instance = MagicMock()
    fake_client_instance.fetch_bars_range.return_value = [_bar()]
    monkeypatch.setattr(
        backfill_module, "AlpacaBarsClient", MagicMock(return_value=fake_client_instance)
    )
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")

    written = backfill_module.backfill(config_path=config_path, days=30)

    assert written == 1
    (call_args, call_kwargs) = fake_client_instance.fetch_bars_range.call_args
    assert call_args[0][0].symbol == "AAPL"
    assert (call_kwargs["end"] - call_kwargs["start"]).days == 30
    mock_session_scope.execute.assert_called_once()


def test_backfill_batches_large_results_into_multiple_upserts(
    config_path, mock_session_scope, monkeypatch
):
    bars = [_bar(ticker=f"T{i}") for i in range(backfill_module.UPSERT_BATCH_SIZE + 1)]
    fake_client_instance = MagicMock()
    fake_client_instance.fetch_bars_range.return_value = bars
    monkeypatch.setattr(
        backfill_module, "AlpacaBarsClient", MagicMock(return_value=fake_client_instance)
    )
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")

    written = backfill_module.backfill(config_path=config_path)

    assert written == len(bars)
    assert mock_session_scope.execute.call_count == 2


def test_backfill_is_a_noop_when_alpaca_returns_no_bars(config_path, mock_session_scope, monkeypatch):
    fake_client_instance = MagicMock()
    fake_client_instance.fetch_bars_range.return_value = []
    monkeypatch.setattr(
        backfill_module, "AlpacaBarsClient", MagicMock(return_value=fake_client_instance)
    )
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")

    written = backfill_module.backfill(config_path=config_path)

    assert written == 0
    mock_session_scope.execute.assert_not_called()
