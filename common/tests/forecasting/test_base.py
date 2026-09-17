from __future__ import annotations

import numpy as np
import pytest
from quantpipe_common.forecasting.base import ForecastResult, interval_to_quantiles


def test_interval_to_quantiles_splits_symmetric_tails():
    lower, upper = interval_to_quantiles(0.8)

    assert lower == pytest.approx(0.1)
    assert upper == pytest.approx(0.9)


def test_interval_to_quantiles_rejects_out_of_range_interval():
    with pytest.raises(ValueError):
        interval_to_quantiles(1.5)


def test_forecast_result_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        ForecastResult(
            yhat=np.array([1.0, 2.0]),
            yhat_lower=np.array([0.0]),
            yhat_upper=np.array([2.0, 3.0]),
            lower_quantile=0.1,
            upper_quantile=0.9,
        )


def test_forecast_result_rejects_quantiles_not_straddling_median():
    with pytest.raises(ValueError):
        ForecastResult(
            yhat=np.array([1.0]),
            yhat_lower=np.array([0.0]),
            yhat_upper=np.array([2.0]),
            lower_quantile=0.6,
            upper_quantile=0.9,
        )
