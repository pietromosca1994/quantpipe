from __future__ import annotations

import numpy as np
from darts import TimeSeries
from darts.models import AutoARIMA, ExponentialSmoothing, Theta

from quantpipe_common.forecasting.base import (
    BaseForecaster,
    ForecastResult,
    predict_with_auto_interval,
)


class _DartsStatisticalForecaster(BaseForecaster):
    """Shared fit/predict glue for classical statistical models — subclasses
    only need to set `self._model` in __init__. Interval comes from the
    model's own probabilistic sampling when supported, otherwise from
    `predict_with_auto_interval`'s residual-based fallback (see base.py).
    """

    _model: object

    def fit(self, series: TimeSeries) -> _DartsStatisticalForecaster:
        self._model.fit(series)
        self._fitted_values = series.values(copy=False).flatten()
        return self

    def predict(self, horizon: int, interval: float = 0.8) -> ForecastResult:
        return predict_with_auto_interval(self._model, self._fitted_values, horizon, interval)


class EtsForecaster(_DartsStatisticalForecaster):
    name = "ets"

    def __init__(self) -> None:
        self._model = ExponentialSmoothing()
        self._fitted_values: np.ndarray = np.array([])


class ThetaForecaster(_DartsStatisticalForecaster):
    name = "theta"

    def __init__(self) -> None:
        self._model = Theta()
        self._fitted_values: np.ndarray = np.array([])


class ArimaForecaster(_DartsStatisticalForecaster):
    name = "auto_arima"

    def __init__(self) -> None:
        self._model = AutoARIMA()
        self._fitted_values: np.ndarray = np.array([])
