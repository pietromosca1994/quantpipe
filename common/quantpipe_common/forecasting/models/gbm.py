from __future__ import annotations

from darts import TimeSeries
from darts.models import LightGBMModel

from quantpipe_common.forecasting.base import (
    BaseForecaster,
    ForecastResult,
    covariate_kwargs,
    interval_to_quantiles,
    result_from_stochastic_series,
)

_NUM_SAMPLES = 500


class LightGbmForecaster(BaseForecaster):
    """Gradient-boosted trees on lagged/rolling close-price features, via
    Darts' LightGBMModel with quantile regression for the interval.

    Quantile regression trains a dedicated model per quantile, so the
    interval level is fixed at construction time rather than choosable per
    predict() call the way the sampling-based statistical/neural models are —
    predict() raises if asked for a different interval than the one this
    instance was built with.

    `output_chunk_length` is set to the full horizon (not 1) specifically so
    covariates never need to extend past what's actually known at predict
    time: with output_chunk_length < horizon, Darts would forecast
    autoregressively and — for a real "past" covariate like volume — that
    would require future values of it for steps beyond the first, which
    isn't real data. `lags_past_covariates`/`lags_future_covariates` are
    optional so this still works with no covariates at all (both left None
    disables that input entirely — Darts wouldn't need what was never
    configured).
    """

    name = "lightgbm"

    def __init__(
        self,
        lags: int = 20,
        output_chunk_length: int = 1,
        lags_past_covariates: int | None = None,
        lags_future_covariates: tuple[int, int] | None = None,
        interval: float = 0.8,
    ) -> None:
        self._interval = interval
        lower_q, upper_q = interval_to_quantiles(interval)
        self._model = LightGBMModel(
            lags=lags,
            output_chunk_length=output_chunk_length,
            lags_past_covariates=lags_past_covariates,
            lags_future_covariates=lags_future_covariates,
            likelihood="quantile",
            quantiles=[lower_q, 0.5, upper_q],
            verbosity=-1,
        )

    def fit(
        self,
        series: TimeSeries,
        past_covariates: TimeSeries | None = None,
        future_covariates: TimeSeries | None = None,
    ) -> LightGbmForecaster:
        self._model.fit(series, **covariate_kwargs(self._model, past_covariates, future_covariates))
        return self

    def predict(
        self,
        horizon: int,
        interval: float = 0.8,
        past_covariates: TimeSeries | None = None,
        future_covariates: TimeSeries | None = None,
    ) -> ForecastResult:
        if abs(interval - self._interval) > 1e-9:
            raise ValueError(
                f"{self.name} was constructed for interval={self._interval}; "
                f"got predict(interval={interval}). Construct a new instance to change it."
            )
        predict_kwargs = covariate_kwargs(self._model, past_covariates, future_covariates)
        pred = self._model.predict(horizon, num_samples=_NUM_SAMPLES, **predict_kwargs)
        return result_from_stochastic_series(pred, interval)
