from __future__ import annotations

import numpy as np

from quantpipe_common.forecasting.base import ForecastResult


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def directional_accuracy(
    previous: np.ndarray, actual: np.ndarray, predicted: np.ndarray
) -> float:
    """Fraction of steps where the forecast got the sign of the change right.

    `previous` is the true value one step before each scored step, matching
    how a trading rule would actually use the forecast (at h=2 that's the
    true actual at h=1, not the train-time last observation). A step where
    the actual didn't move at all has no direction to be right or wrong
    about, so it's excluded rather than scored as a miss.
    """
    actual_direction = np.sign(actual - previous)
    predicted_direction = np.sign(predicted - previous)
    scoreable = actual_direction != 0
    if not np.any(scoreable):
        return float("nan")
    return float(np.mean(actual_direction[scoreable] == predicted_direction[scoreable]))


def pinball_loss(actual: np.ndarray, quantile_forecast: np.ndarray, quantile: float) -> float:
    diff = actual - quantile_forecast
    return float(np.mean(np.maximum(quantile * diff, (quantile - 1) * diff)))


def coverage(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    """Fraction of actuals that fell inside [lower, upper] — should track the
    interval's nominal level (e.g. ~0.8 for an 80% interval) if it's calibrated.
    """
    return float(np.mean((actual >= lower) & (actual <= upper)))


def evaluate(
    actual: np.ndarray, previous: np.ndarray, forecast: ForecastResult
) -> dict[str, float]:
    return {
        "mae": mae(actual, forecast.yhat),
        "rmse": rmse(actual, forecast.yhat),
        "directional_accuracy": directional_accuracy(previous, actual, forecast.yhat),
        "pinball_lower": pinball_loss(actual, forecast.yhat_lower, forecast.lower_quantile),
        "pinball_upper": pinball_loss(actual, forecast.yhat_upper, forecast.upper_quantile),
        "coverage": coverage(actual, forecast.yhat_lower, forecast.yhat_upper),
    }
