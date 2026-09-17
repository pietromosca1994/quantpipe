from __future__ import annotations

import numpy as np
from darts import TimeSeries
from darts.models import NaiveDrift, NaiveSeasonal

from quantpipe_common.forecasting.base import (
    BaseForecaster,
    ForecastResult,
    predict_with_auto_interval,
)


class NaiveSeasonalForecaster(BaseForecaster):
    """Repeats the value from `seasonal_period` bars ago — the floor every
    other model family needs to beat. K=1 is a plain random-walk/naive-last-value
    forecast.
    """

    name = "naive_seasonal"

    def __init__(self, seasonal_period: int = 1) -> None:
        self._seasonal_period = seasonal_period
        self._model = NaiveSeasonal(K=seasonal_period)
        self._fitted_values: np.ndarray = np.array([])

    def fit(self, series: TimeSeries) -> NaiveSeasonalForecaster:
        self._model.fit(series)
        self._fitted_values = series.values(copy=False).flatten()
        return self

    def predict(self, horizon: int, interval: float = 0.8) -> ForecastResult:
        return predict_with_auto_interval(
            self._model,
            self._fitted_values,
            horizon,
            interval,
            step_back=self._seasonal_period,
        )


class NaiveDriftForecaster(BaseForecaster):
    """Extrapolates the average bar-over-bar change across the whole training
    window — the other standard naive floor, complementary to naive-seasonal.
    """

    name = "naive_drift"

    def __init__(self) -> None:
        self._model = NaiveDrift()
        self._fitted_values: np.ndarray = np.array([])

    def fit(self, series: TimeSeries) -> NaiveDriftForecaster:
        self._model.fit(series)
        self._fitted_values = series.values(copy=False).flatten()
        return self

    def predict(self, horizon: int, interval: float = 0.8) -> ForecastResult:
        return predict_with_auto_interval(self._model, self._fitted_values, horizon, interval)
