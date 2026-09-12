from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from quantpipe_common.schemas import Bar, ModelMetadata, Prediction

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _valid_bar_kwargs() -> dict:
    return dict(
        time=_NOW,
        ticker="AAPL",
        asset_class="us_equity",
        open=100.0,
        high=101.0,
        low=99.5,
        close=100.5,
        volume=12345,
    )


def test_bar_accepts_valid_payload_and_defaults_source():
    bar = Bar(**_valid_bar_kwargs())

    assert bar.source == "alpaca"


def test_bar_rejects_invalid_asset_class():
    with pytest.raises(ValidationError):
        Bar(**{**_valid_bar_kwargs(), "asset_class": "futures"})


def test_bar_is_immutable():
    bar = Bar(**_valid_bar_kwargs())

    with pytest.raises(ValidationError):
        bar.close = 200.0


def test_bar_rejects_negative_price():
    with pytest.raises(ValidationError):
        Bar(**{**_valid_bar_kwargs(), "close": -1.0})


def test_bar_rejects_negative_volume():
    with pytest.raises(ValidationError):
        Bar(**{**_valid_bar_kwargs(), "volume": -1})


def test_bar_rejects_low_above_high():
    with pytest.raises(ValidationError):
        Bar(**{**_valid_bar_kwargs(), "low": 200.0, "high": 100.0})


def test_bar_rejects_open_outside_low_high_range():
    with pytest.raises(ValidationError):
        Bar(**{**_valid_bar_kwargs(), "open": 500.0})


def test_bar_rejects_close_outside_low_high_range():
    with pytest.raises(ValidationError):
        Bar(**{**_valid_bar_kwargs(), "close": 500.0})


def test_prediction_rejects_invalid_timeframe():
    with pytest.raises(ValidationError):
        Prediction(
            time=_NOW,
            ticker="AAPL",
            timeframe="4h",
            model_version="1",
            horizon=1,
            yhat=1.0,
            yhat_lower=0.9,
            yhat_upper=1.1,
            generated_at=_NOW,
        )


def test_model_metadata_defaults_metrics_to_empty_dict():
    metadata = ModelMetadata(
        ticker="AAPL",
        timeframe="1h",
        mlflow_run_id="run-1",
        mlflow_model_uri="models:/quantpipe-AAPL-1h/1",
        version=1,
        status="staging",
        trained_at=_NOW,
    )

    assert metadata.metrics == {}


def test_model_metadata_rejects_invalid_status():
    with pytest.raises(ValidationError):
        ModelMetadata(
            ticker="AAPL",
            timeframe="1h",
            mlflow_run_id="run-1",
            mlflow_model_uri="models:/quantpipe-AAPL-1h/1",
            version=1,
            status="deployed",
            trained_at=_NOW,
        )
