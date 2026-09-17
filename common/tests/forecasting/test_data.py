from __future__ import annotations

import numpy as np
import pandas as pd
from quantpipe_common.forecasting.data import compute_future_covariates, compute_past_covariates


def test_compute_past_covariates_has_no_nans_from_the_first_bar():
    close = pd.Series([100.0, 101.0, 99.0, 102.0, 103.0])
    volume = pd.Series([1000, 1500, 1200, 900, 1100])

    covariates = compute_past_covariates(close, volume)
    values = covariates.values(copy=False)

    assert covariates.columns.tolist() == ["log_volume", "lagged_return", "rolling_volatility"]
    assert not np.isnan(values).any()


def test_compute_past_covariates_lagged_return_matches_pct_change():
    close = pd.Series([100.0, 110.0, 99.0])
    volume = pd.Series([1000, 1000, 1000])

    covariates = compute_past_covariates(close, volume)
    lagged_return = covariates["lagged_return"].values(copy=False).flatten()

    assert lagged_return[0] == 0.0
    np.testing.assert_allclose(lagged_return[1], 0.10)
    np.testing.assert_allclose(lagged_return[2], -0.1, rtol=1e-6)


def test_compute_past_covariates_log_volume_is_monotonic_in_volume():
    close = pd.Series([100.0, 100.0])
    volume = pd.Series([1000, 2000])

    covariates = compute_past_covariates(close, volume)
    log_volume = covariates["log_volume"].values(copy=False).flatten()

    assert log_volume[1] > log_volume[0]
    np.testing.assert_allclose(log_volume, np.log1p(volume.to_numpy()))


def test_compute_future_covariates_cyclical_values_stay_in_unit_range():
    times = pd.DatetimeIndex(
        ["2026-01-05 09:30", "2026-01-05 15:59", "2026-01-06 12:00", "2026-01-09 12:00"],
        tz="UTC",
    )

    covariates = compute_future_covariates(times)
    values = covariates.values(copy=False)

    assert covariates.columns.tolist() == ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]
    assert np.all(values >= -1.0) and np.all(values <= 1.0)


def test_compute_future_covariates_midnight_and_23_59_are_close():
    # Cyclical encoding should place hour 0 and hour ~24 near each other,
    # not at opposite ends of a raw 0-23 scale.
    times = pd.DatetimeIndex(["2026-01-05 00:00", "2026-01-05 23:59"], tz="UTC")

    covariates = compute_future_covariates(times)
    hour_sin, hour_cos = covariates["hour_sin"].values(copy=False).flatten(), covariates[
        "hour_cos"
    ].values(copy=False).flatten()

    midnight = np.array([hour_sin[0], hour_cos[0]])
    almost_midnight = np.array([hour_sin[1], hour_cos[1]])
    assert np.linalg.norm(midnight - almost_midnight) < 0.01
