from __future__ import annotations

import numpy as np
import pytest
from quantpipe_common.forecasting.base import ForecastResult
from quantpipe_common.forecasting.metrics import (
    coverage,
    directional_accuracy,
    evaluate,
    mae,
    pinball_loss,
    rmse,
)


def test_mae_and_rmse_match_hand_computed_values():
    actual = np.array([1.0, 2.0, 3.0])
    predicted = np.array([1.0, 4.0, 3.0])

    assert mae(actual, predicted) == pytest.approx(2 / 3)
    assert rmse(actual, predicted) == pytest.approx(np.sqrt(4 / 3))


def test_directional_accuracy_counts_correct_sign_matches():
    previous = np.array([10.0, 10.0, 10.0])
    actual = np.array([11.0, 9.0, 12.0])
    predicted = np.array([11.0, 11.0, 9.0])

    assert directional_accuracy(previous, actual, predicted) == pytest.approx(1 / 3)


def test_directional_accuracy_ignores_zero_actual_change():
    previous = np.array([10.0, 10.0])
    actual = np.array([10.0, 11.0])
    predicted = np.array([12.0, 11.0])

    assert directional_accuracy(previous, actual, predicted) == pytest.approx(1.0)


def test_directional_accuracy_is_nan_when_nothing_is_scoreable():
    previous = np.array([10.0])
    actual = np.array([10.0])
    predicted = np.array([11.0])

    assert np.isnan(directional_accuracy(previous, actual, predicted))


def test_pinball_loss_penalizes_underprediction_more_at_high_quantiles():
    actual = np.array([10.0])
    under = np.array([8.0])
    over = np.array([12.0])

    loss_under = pinball_loss(actual, under, quantile=0.9)
    loss_over = pinball_loss(actual, over, quantile=0.9)

    assert loss_under > loss_over


def test_coverage_fraction_inside_interval():
    actual = np.array([1.0, 5.0, 9.0])
    lower = np.array([0.0, 0.0, 0.0])
    upper = np.array([2.0, 6.0, 8.0])

    assert coverage(actual, lower, upper) == pytest.approx(2 / 3)


def test_evaluate_returns_all_metric_keys():
    forecast = ForecastResult(
        yhat=np.array([1.0, 2.0]),
        yhat_lower=np.array([0.0, 1.0]),
        yhat_upper=np.array([2.0, 3.0]),
        lower_quantile=0.1,
        upper_quantile=0.9,
    )
    actual = np.array([1.5, 2.5])
    previous = np.array([1.0, 1.5])

    metrics = evaluate(actual=actual, previous=previous, forecast=forecast)

    assert set(metrics) == {
        "mae",
        "rmse",
        "directional_accuracy",
        "pinball_lower",
        "pinball_upper",
        "coverage",
    }
