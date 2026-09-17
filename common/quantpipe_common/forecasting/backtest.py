from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from quantpipe_common.forecasting.base import BaseForecaster, ForecastResult
from quantpipe_common.forecasting.metrics import evaluate

if TYPE_CHECKING:
    from darts import TimeSeries


@dataclass(frozen=True)
class Fold:
    train_end: int  # index (exclusive) of the last training observation
    horizon: int


def walk_forward_folds(
    n_observations: int, horizon: int, min_train_size: int, step: int
) -> list[Fold]:
    """Expanding-window fold boundaries: each fold trains on values[:train_end]
    and scores the next `horizon` values. A `step` of `horizon` gives
    non-overlapping test windows, the typical choice for walk-forward
    evaluation; a smaller step reuses more of the history at the cost of
    overlapping (correlated) fold scores.
    """
    if min_train_size + horizon > n_observations:
        return []
    folds = []
    train_end = min_train_size
    while train_end + horizon <= n_observations:
        folds.append(Fold(train_end=train_end, horizon=horizon))
        train_end += step
    return folds


@dataclass(frozen=True)
class FoldResult:
    fold: Fold
    forecast: ForecastResult
    actual: np.ndarray
    metrics: dict[str, float]


def run_backtest(
    forecaster_factory: Callable[[], BaseForecaster],
    series: TimeSeries,
    folds: list[Fold],
    interval: float = 0.8,
) -> list[FoldResult]:
    """Fit-predict-score a fresh model instance per fold. Each fold retrains
    from scratch on its own expanding training window — never reuse a fitted
    model across folds, or later folds leak information about how well it did
    on data it was never actually blind to.
    """
    values = series.values(copy=False).flatten()
    results = []
    for fold in folds:
        train_series = series[: fold.train_end]
        model = forecaster_factory()
        model.fit(train_series)
        forecast = model.predict(fold.horizon, interval=interval)
        actual = values[fold.train_end : fold.train_end + fold.horizon]
        previous = values[fold.train_end - 1 : fold.train_end + fold.horizon - 1]
        results.append(
            FoldResult(
                fold=fold,
                forecast=forecast,
                actual=actual,
                metrics=evaluate(actual=actual, previous=previous, forecast=forecast),
            )
        )
    return results
