from __future__ import annotations

from darts import TimeSeries
from darts.models import LightGBMModel

from quantpipe_common.forecasting.base import (
    BaseForecaster,
    ForecastResult,
    interval_to_quantiles,
    result_from_stochastic_series,
)

_NUM_SAMPLES = 500


class LightGbmForecaster(BaseForecaster):
    """Gradient-boosted trees on lagged/rolling close-price features, via
    Darts' LightGBMModel with quantile regression for the interval.

    Quantile regression trains a dedicated model per quantile, so the
    interval level is fixed at construction time rather than choosable per
    predict() call the way the sampling-based statistical/neural models are —
    predict() raises if asked for a different interval than the one this
    instance was built with.
    """

    name = "lightgbm"

    def __init__(self, lags: int = 20, interval: float = 0.8) -> None:
        self._interval = interval
        lower_q, upper_q = interval_to_quantiles(interval)
        self._model = LightGBMModel(
            lags=lags,
            output_chunk_length=1,
            likelihood="quantile",
            quantiles=[lower_q, 0.5, upper_q],
            verbosity=-1,
        )

    def fit(self, series: TimeSeries) -> LightGbmForecaster:
        self._model.fit(series)
        return self

    def predict(self, horizon: int, interval: float = 0.8) -> ForecastResult:
        if abs(interval - self._interval) > 1e-9:
            raise ValueError(
                f"{self.name} was constructed for interval={self._interval}; "
                f"got predict(interval={interval}). Construct a new instance to change it."
            )
        pred = self._model.predict(horizon, num_samples=_NUM_SAMPLES)
        return result_from_stochastic_series(pred, interval)
