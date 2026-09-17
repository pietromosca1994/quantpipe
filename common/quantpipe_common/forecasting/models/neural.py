from __future__ import annotations

from darts import TimeSeries
from darts.models import NBEATSModel, NHiTSModel
from darts.utils.likelihood_models import QuantileRegression

from quantpipe_common.forecasting.base import (
    BaseForecaster,
    ForecastResult,
    covariate_kwargs,
    interval_to_quantiles,
    result_from_stochastic_series,
)

_NUM_SAMPLES = 200  # neural sampling is heavier than statistical/GBM; keep smaller
_RANDOM_STATE = 42


class _QuantileNeuralForecaster(BaseForecaster):
    """Shared fit/predict glue for Darts neural models configured with a
    QuantileRegression likelihood — same fixed-interval-at-construction
    constraint as LightGbmForecaster and for the same reason (quantile heads
    are trained, not chosen at predict time). Subclasses set `self._model`.

    Both NBEATSModel and NHiTSModel support past_covariates (e.g. volume,
    realized volatility) out of the box, but neither supports
    future_covariates — `covariate_kwargs` drops it automatically.
    """

    _model: object

    def __init__(self, interval: float) -> None:
        self._interval = interval

    def fit(
        self,
        series: TimeSeries,
        past_covariates: TimeSeries | None = None,
        future_covariates: TimeSeries | None = None,
    ) -> _QuantileNeuralForecaster:
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


class NBeatsForecaster(_QuantileNeuralForecaster):
    name = "nbeats"

    def __init__(
        self,
        input_chunk_length: int = 60,
        output_chunk_length: int = 5,
        interval: float = 0.8,
        n_epochs: int = 20,
    ) -> None:
        super().__init__(interval)
        lower_q, upper_q = interval_to_quantiles(interval)
        self._model = NBEATSModel(
            input_chunk_length=input_chunk_length,
            output_chunk_length=output_chunk_length,
            likelihood=QuantileRegression(quantiles=[lower_q, 0.5, upper_q]),
            n_epochs=n_epochs,
            random_state=_RANDOM_STATE,
        )


class NHitsForecaster(_QuantileNeuralForecaster):
    name = "nhits"

    def __init__(
        self,
        input_chunk_length: int = 60,
        output_chunk_length: int = 5,
        interval: float = 0.8,
        n_epochs: int = 20,
    ) -> None:
        super().__init__(interval)
        lower_q, upper_q = interval_to_quantiles(interval)
        self._model = NHiTSModel(
            input_chunk_length=input_chunk_length,
            output_chunk_length=output_chunk_length,
            likelihood=QuantileRegression(quantiles=[lower_q, 0.5, upper_q]),
            n_epochs=n_epochs,
            random_state=_RANDOM_STATE,
        )
