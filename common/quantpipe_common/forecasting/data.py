from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from darts import TimeSeries
from sqlalchemy import text

from quantpipe_common.config import DBConfig
from quantpipe_common.db.session import get_engine
from quantpipe_common.enums import Timeframe

_BARS_TABLE_BY_TIMEFRAME: dict[Timeframe, str] = {
    Timeframe.ONE_MINUTE: "bars_1m",
    Timeframe.FIVE_MINUTES: "bars_5m",
    Timeframe.FIFTEEN_MINUTES: "bars_15m",
    Timeframe.ONE_HOUR: "bars_1h",
    Timeframe.ONE_DAY: "bars_1d",
}

# Trailing window (in bars) for realized-volatility — a rolling stat, so it
# widens as more history accumulates rather than needing its own lookback
# beyond what's already loaded.
_VOLATILITY_WINDOW = 20


@dataclass(frozen=True)
class SeriesBundle:
    """A ticker/timeframe's close-price history as a Darts TimeSeries with an
    integer RangeIndex (one step per trading bar — see BaseForecaster's
    docstring for why), plus the real timestamps each step corresponds to,
    kept alongside for reporting since the RangeIndex itself carries no
    wall-clock information.

    `past_covariates` and `future_covariates` share that same integer
    RangeIndex (same rows, same order as `series`), so they can be sliced by
    fold boundary exactly like `series` in run_backtest.
    """

    ticker: str
    timeframe: Timeframe
    series: TimeSeries
    times: pd.DatetimeIndex
    past_covariates: TimeSeries
    future_covariates: TimeSeries


def compute_past_covariates(close: pd.Series, volume: pd.Series) -> TimeSeries:
    """Volume and price-derived signals available at each historical bar.

    Each column only ever uses values up to and including its own bar (a
    trailing return, a trailing rolling std, the bar's own volume) — never a
    later one — so it's safe to feed a model as a 'past' covariate without
    leaking data a real prediction wouldn't have had yet.
    """
    log_volume = np.log1p(volume.astype(float))
    lagged_return = close.astype(float).pct_change().fillna(0.0)
    # ddof=0 so a single-observation window returns 0.0 rather than NaN,
    # avoiding a separate fill step for the first few bars.
    rolling_volatility = lagged_return.rolling(_VOLATILITY_WINDOW, min_periods=1).std(ddof=0).fillna(0.0)
    values = np.column_stack(
        [log_volume.to_numpy(), lagged_return.to_numpy(), rolling_volatility.to_numpy()]
    )
    return TimeSeries.from_values(values, columns=["log_volume", "lagged_return", "rolling_volatility"])


def compute_future_covariates(times: pd.DatetimeIndex) -> TimeSeries:
    """Calendar features derived purely from the timestamp — known for any
    bar, historical or future, so these are legitimate 'future' covariates
    (unlike volume/volatility, which only exist once a bar has closed).

    Hour-of-day and day-of-week are cyclically (sin/cos) encoded rather than
    passed as raw integers so e.g. 23:00 and 00:00 stay close together
    instead of looking maximally far apart to the model.
    """
    fractional_hour = times.hour + times.minute / 60.0
    hour_angle = 2 * np.pi * fractional_hour / 24.0
    dow_angle = 2 * np.pi * times.dayofweek / 7.0
    values = np.column_stack(
        [np.sin(hour_angle), np.cos(hour_angle), np.sin(dow_angle), np.cos(dow_angle)]
    )
    return TimeSeries.from_values(values, columns=["hour_sin", "hour_cos", "dow_sin", "dow_cos"])


def load_series(ticker: str, timeframe: Timeframe, config: DBConfig | None = None) -> SeriesBundle:
    # `table` is looked up from the fixed, closed-enum mapping above, never
    # built from caller-supplied text, so interpolating it into the query is
    # not an injection surface — `ticker` is the only actual input, and it's
    # bound as a parameter below.
    table = _BARS_TABLE_BY_TIMEFRAME[timeframe]
    query = text(f"SELECT time, close, volume FROM {table} WHERE ticker = :ticker ORDER BY time")

    engine = get_engine(config)
    with engine.connect() as conn:
        frame = pd.read_sql(query, conn, params={"ticker": ticker})

    if frame.empty:
        raise ValueError(f"no bars found for ticker={ticker!r} timeframe={timeframe.value!r}")

    times = pd.DatetimeIndex(frame["time"])
    series = TimeSeries.from_values(frame["close"].astype(float).to_numpy())
    return SeriesBundle(
        ticker=ticker,
        timeframe=timeframe,
        series=series,
        times=times,
        past_covariates=compute_past_covariates(frame["close"], frame["volume"]),
        future_covariates=compute_future_covariates(times),
    )
