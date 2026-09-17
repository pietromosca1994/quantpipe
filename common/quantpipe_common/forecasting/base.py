from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    # Kept behind TYPE_CHECKING so metrics/backtest logic can be unit-tested
    # without darts installed — only the real model wrappers in
    # forecasting/models/ need it importable at runtime.
    from darts import TimeSeries


@dataclass(frozen=True)
class ForecastResult:
    """A forecaster's output for one predict() call: point forecast plus a
    lower/upper interval bound, and the quantile levels those bounds represent
    (needed by metrics.pinball_loss, which is quantile-specific).
    """

    yhat: np.ndarray
    yhat_lower: np.ndarray
    yhat_upper: np.ndarray
    lower_quantile: float
    upper_quantile: float

    def __post_init__(self) -> None:
        lengths = {len(self.yhat), len(self.yhat_lower), len(self.yhat_upper)}
        if len(lengths) != 1:
            raise ValueError("yhat, yhat_lower, and yhat_upper must be the same length")
        if not self.lower_quantile < 0.5 < self.upper_quantile:
            raise ValueError("lower_quantile must be < 0.5 < upper_quantile")


class BaseForecaster(ABC):
    """Common fit/predict contract every candidate model family implements.

    `series` is a Darts TimeSeries indexed by an integer RangeIndex — one step
    per trading bar, not per calendar unit. Financial series have gaps
    (nights, weekends, holidays) that don't map onto a fixed pandas frequency
    the way Darts' datetime-indexed mode expects; treating "one step" as "one
    bar" sidesteps that instead of forcing a business-day/business-hour
    calendar that still breaks around holidays. `horizon` and fold boundaries
    in the backtest are counted in bars for the same reason.
    """

    name: str

    @abstractmethod
    def fit(self, series: TimeSeries) -> BaseForecaster: ...

    @abstractmethod
    def predict(self, horizon: int, interval: float = 0.8) -> ForecastResult: ...


def interval_to_quantiles(interval: float) -> tuple[float, float]:
    if not 0 < interval < 1:
        raise ValueError("interval must be between 0 and 1")
    tail = (1 - interval) / 2
    return tail, 1 - tail


def result_from_stochastic_series(pred: TimeSeries, interval: float) -> ForecastResult:
    """Build a ForecastResult from a Darts probabilistic (sampled) prediction.

    `TimeSeries.quantile()` is the one Darts call in this whole codebase most
    likely to have shifted name/signature across versions (it was
    `quantile_timeseries()` pre-0.31) — see experiments/README.md's "before
    trusting this" note if this errors.
    """
    lower_q, upper_q = interval_to_quantiles(interval)
    median = pred.quantile(0.5).values(copy=False).flatten()
    lower = pred.quantile(lower_q).values(copy=False).flatten()
    upper = pred.quantile(upper_q).values(copy=False).flatten()
    return ForecastResult(
        yhat=median,
        yhat_lower=lower,
        yhat_upper=upper,
        lower_quantile=lower_q,
        upper_quantile=upper_q,
    )


def _residual_std(values: np.ndarray, step_back: int) -> float:
    if len(values) <= step_back:
        return 0.0
    residuals = values[step_back:] - values[:-step_back]
    return float(np.std(residuals))


def predict_with_auto_interval(
    model,
    fitted_values: np.ndarray,
    horizon: int,
    interval: float,
    step_back: int = 1,
    num_samples: int = 500,
) -> ForecastResult:
    """Shared predict-with-interval glue for any fitted Darts model.

    Uses the model's own probabilistic sampling when it supports one
    (`num_samples` draws -> empirical quantiles). Falls back to a symmetric
    interval built from in-sample residual std, scaled by sqrt(step) — the
    standard growing-uncertainty assumption for a random-walk-like series —
    for models with no native probabilistic output (e.g. Darts' naive
    baselines, or AutoARIMA depending on backend/version).
    """
    lower_q, upper_q = interval_to_quantiles(interval)
    if getattr(model, "supports_probabilistic_prediction", False):
        pred = model.predict(horizon, num_samples=num_samples)
        return result_from_stochastic_series(pred, interval)

    # Imported here, not at module level, so importing base.py (and therefore
    # metrics.py/backtest.py, which both import from it) doesn't require scipy
    # unless a model actually falls back to this residual-based interval.
    from scipy.stats import norm

    point = model.predict(horizon).values(copy=False).flatten()
    resid_std = _residual_std(fitted_values, step_back)
    z = norm.ppf(upper_q)
    steps = np.arange(1, len(point) + 1)
    width = z * resid_std * np.sqrt(steps)
    return ForecastResult(
        yhat=point,
        yhat_lower=point - width,
        yhat_upper=point + width,
        lower_quantile=lower_q,
        upper_quantile=upper_q,
    )
