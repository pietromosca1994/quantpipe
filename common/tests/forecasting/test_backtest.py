from __future__ import annotations

import numpy as np
from quantpipe_common.forecasting.backtest import Fold, run_backtest, walk_forward_folds
from quantpipe_common.forecasting.base import BaseForecaster, ForecastResult


class _FakeSeries:
    """Duck-typed stand-in for darts.TimeSeries — supports just the slicing
    and `.values()` surface run_backtest actually uses, so these tests don't
    require darts installed.
    """

    def __init__(self, values: np.ndarray) -> None:
        self._values = values

    def __getitem__(self, key):
        return _FakeSeries(self._values[key])

    def __len__(self) -> int:
        return len(self._values)

    def values(self, copy: bool = True) -> np.ndarray:
        return self._values.reshape(-1, 1)


class _LastValueForecaster(BaseForecaster):
    name = "last_value"

    def fit(self, series):
        self._last = series.values(copy=False).flatten()[-1]
        return self

    def predict(self, horizon: int, interval: float = 0.8) -> ForecastResult:
        yhat = np.full(horizon, self._last)
        return ForecastResult(
            yhat=yhat,
            yhat_lower=yhat - 1,
            yhat_upper=yhat + 1,
            lower_quantile=0.1,
            upper_quantile=0.9,
        )


def test_walk_forward_folds_produces_expanding_windows():
    folds = walk_forward_folds(n_observations=10, horizon=2, min_train_size=6, step=2)

    assert folds == [Fold(train_end=6, horizon=2), Fold(train_end=8, horizon=2)]


def test_walk_forward_folds_returns_empty_when_not_enough_history():
    assert walk_forward_folds(n_observations=5, horizon=3, min_train_size=4, step=1) == []


def test_run_backtest_scores_each_fold_against_the_right_actuals():
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    series = _FakeSeries(values)
    folds = walk_forward_folds(n_observations=len(values), horizon=2, min_train_size=4, step=2)

    results = run_backtest(_LastValueForecaster, series, folds, interval=0.8)

    assert len(results) == 2
    first = results[0]
    assert first.fold.train_end == 4
    np.testing.assert_array_equal(first.actual, values[4:6])
    np.testing.assert_array_equal(first.forecast.yhat, [values[3], values[3]])
    assert first.metrics["mae"] == np.mean(np.abs(values[4:6] - values[3]))
