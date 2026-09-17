from __future__ import annotations

from collections.abc import Callable

from quantpipe_common.forecasting.base import BaseForecaster
from quantpipe_common.forecasting.models.baselines import (
    NaiveDriftForecaster,
    NaiveSeasonalForecaster,
)
from quantpipe_common.forecasting.models.gbm import LightGbmForecaster
from quantpipe_common.forecasting.models.neural import NBeatsForecaster, NHitsForecaster
from quantpipe_common.forecasting.models.statistical import (
    ArimaForecaster,
    EtsForecaster,
    ThetaForecaster,
)

# Each factory takes the experiment's forecast horizon (in bars) and the
# interval level being backtested, returning a freshly-initialized model —
# never reuse a fitted instance across folds/tickers. Lag/window sizes scale
# off horizon so a single registry works across timeframes without hardcoding
# numbers tuned for one bar size. Every factory takes `interval` even though
# only the quantile-regression models (lightgbm/nbeats/nhits) use it at
# construction time — they fix their interval when trained, so the value here
# must be the same one predict() is later called with, which is what run_one()
# passes as --interval end to end. Statistical/naive models ignore it here and
# accept interval per predict() call instead.
MODEL_REGISTRY: dict[str, Callable[[int, float], BaseForecaster]] = {
    "naive_seasonal": lambda horizon, interval: NaiveSeasonalForecaster(seasonal_period=1),
    "naive_drift": lambda horizon, interval: NaiveDriftForecaster(),
    "ets": lambda horizon, interval: EtsForecaster(),
    "theta": lambda horizon, interval: ThetaForecaster(),
    "auto_arima": lambda horizon, interval: ArimaForecaster(),
    "lightgbm": lambda horizon, interval: LightGbmForecaster(
        lags=max(20, 4 * horizon), interval=interval
    ),
    "nbeats": lambda horizon, interval: NBeatsForecaster(
        input_chunk_length=max(60, 8 * horizon),
        output_chunk_length=horizon,
        interval=interval,
    ),
    "nhits": lambda horizon, interval: NHitsForecaster(
        input_chunk_length=max(60, 8 * horizon),
        output_chunk_length=horizon,
        interval=interval,
    ),
}

BASELINE_NAMES = ("naive_seasonal", "naive_drift")
