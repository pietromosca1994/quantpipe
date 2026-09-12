from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quantpipe_common.enums import AssetClass, ModelStage, Source, Timeframe


class Bar(BaseModel):
    """A single OHLCV bar, validated before it touches the database."""

    model_config = ConfigDict(frozen=True)

    time: datetime
    ticker: str
    asset_class: AssetClass
    open: float = Field(ge=0)
    high: float = Field(ge=0)
    low: float = Field(ge=0)
    close: float = Field(ge=0)
    volume: float = Field(ge=0)
    source: Source = Source.ALPACA

    @model_validator(mode="after")
    def _check_price_bounds(self) -> Bar:
        if self.low > self.high:
            raise ValueError(f"low ({self.low}) cannot exceed high ({self.high})")
        if not self.low <= self.open <= self.high:
            raise ValueError(f"open ({self.open}) must fall within [low, high]")
        if not self.low <= self.close <= self.high:
            raise ValueError(f"close ({self.close}) must fall within [low, high]")
        return self


class Prediction(BaseModel):
    """A single forecast point, validated before it touches the database."""

    model_config = ConfigDict(frozen=True)

    time: datetime
    ticker: str
    timeframe: Timeframe
    model_version: str
    horizon: int
    yhat: float
    yhat_lower: float
    yhat_upper: float
    generated_at: datetime


class ModelMetadata(BaseModel):
    """Mirrors a row of model_registry — the training service's promotion record."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    timeframe: Timeframe
    mlflow_run_id: str
    mlflow_model_uri: str
    version: int
    status: ModelStage
    trained_at: datetime
    metrics: dict[str, float] = Field(default_factory=dict)
