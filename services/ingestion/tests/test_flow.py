from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
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


def test_upsert_bars_executes_one_statement_against_bars_1m(monkeypatch):
    mock_session = MagicMock()

    @contextmanager
    def fake_session_scope():
        yield mock_session

    monkeypatch.setattr(flow_module, "session_scope", fake_session_scope)

    written = flow_module.upsert_bars.fn([_bar(), _bar(ticker="MSFT")])

    assert written == 2
    mock_session.execute.assert_called_once()
    (statement,) = mock_session.execute.call_args[0]
    assert statement.table.name == "bars_1m"


def test_upsert_bars_deduplicates_same_time_and_ticker(monkeypatch):
    mock_session = MagicMock()

    @contextmanager
    def fake_session_scope():
        yield mock_session

    monkeypatch.setattr(flow_module, "session_scope", fake_session_scope)

    stale = _bar()
    fresh = Bar(**{**stale.model_dump(), "close": 100.9})

    written = flow_module.upsert_bars.fn([stale, fresh])

    assert written == 1
    mock_session.execute.assert_called_once()


def test_upsert_bars_is_a_noop_for_an_empty_list(monkeypatch):
    mock_session = MagicMock()

    @contextmanager
    def fake_session_scope():
        yield mock_session

    monkeypatch.setattr(flow_module, "session_scope", fake_session_scope)

    written = flow_module.upsert_bars.fn([])

    assert written == 0
    mock_session.execute.assert_not_called()


def test_ingest_bars_wires_fetch_and_upsert_together(tmp_path, monkeypatch):
    config_path = tmp_path / "tickers.yaml"
    config_path.write_text(
        """
tickers:
  - symbol: AAPL
    asset_class: us_equity
"""
    )
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")

    fake_client_instance = MagicMock()
    fake_client_instance.fetch_latest_bars.return_value = [_bar(), _bar(ticker="MSFT")]
    fake_client_cls = MagicMock(return_value=fake_client_instance)
    monkeypatch.setattr(flow_module, "AlpacaBarsClient", fake_client_cls)

    mock_session = MagicMock()

    @contextmanager
    def fake_session_scope():
        yield mock_session

    monkeypatch.setattr(flow_module, "session_scope", fake_session_scope)

    rows_before = flow_module.INGEST_ROWS_WRITTEN._value.get()
    written = flow_module.ingest_bars.fn(config_path=str(config_path))

    assert written == 2
    assert flow_module.INGEST_ROWS_WRITTEN._value.get() == rows_before + 2
    fake_client_instance.fetch_latest_bars.assert_called_once()


def test_ingest_bars_increments_error_metric_and_reraises_on_failure(tmp_path, monkeypatch):
    config_path = tmp_path / "tickers.yaml"
    config_path.write_text(
        """
tickers:
  - symbol: AAPL
    asset_class: us_equity
"""
    )
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")

    fake_client_instance = MagicMock()
    fake_client_instance.fetch_latest_bars.side_effect = RuntimeError("boom")
    fake_client_cls = MagicMock(return_value=fake_client_instance)
    monkeypatch.setattr(flow_module, "AlpacaBarsClient", fake_client_cls)

    errors_before = flow_module.INGEST_ERRORS._value.get()

    with pytest.raises(RuntimeError):
        flow_module.ingest_bars.fn(config_path=str(config_path))

    assert flow_module.INGEST_ERRORS._value.get() == errors_before + 1
