from __future__ import annotations

import numpy as np
from darts import TimeSeries
from darts.models import AutoARIMA, ExponentialSmoothing, Theta

from quantpipe_common.forecasting.base import (
    BaseForecaster,
    ForecastResult,
    covariate_kwargs,
    predict_with_auto_interval,
)


class _DartsStatisticalForecaster(BaseForecaster):
    """Shared fit/predict glue for classical statistical models — subclasses
    only need to set `self._model` in __init__. Interval comes from the
    model's own probabilistic sampling when supported, otherwise from
    `predict_with_auto_interval`'s residual-based fallback (see base.py).

    Of this family, only AutoARIMA actually supports covariates (future_covariates,
    i.e. exogenous regressors) — ETS and Theta support neither. `covariate_kwargs`
    checks each model's own support flags, so this shared glue works for all three
    without a subclass needing to override anything.
    """

    _model: object

    def fit(
        self,
        series: TimeSeries,
        past_covariates: TimeSeries | None = None,
        future_covariates: TimeSeries | None = None,
    ) -> _DartsStatisticalForecaster:
        self._model.fit(series, **covariate_kwargs(self._model, past_covariates, future_covariates))
        self._fitted_values = series.values(copy=False).flatten()
        return self

    def predict(
        self,
        horizon: int,
        interval: float = 0.8,
        past_covariates: TimeSeries | None = None,
        future_covariates: TimeSeries | None = None,
    ) -> ForecastResult:
        return predict_with_auto_interval(
            self._model,
            self._fitted_values,
            horizon,
            interval,
            past_covariates=past_covariates,
            future_covariates=future_covariates,
        )


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
