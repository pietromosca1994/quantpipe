from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class SeriesBundle:
    """A ticker/timeframe's close-price history as a Darts TimeSeries with an
    integer RangeIndex (one step per trading bar — see BaseForecaster's
    docstring for why), plus the real timestamps each step corresponds to,
    kept alongside for reporting since the RangeIndex itself carries no
    wall-clock information.
    """

    ticker: str
    timeframe: Timeframe
    series: TimeSeries
    times: pd.DatetimeIndex


def load_series(ticker: str, timeframe: Timeframe, config: DBConfig | None = None) -> SeriesBundle:
    # `table` is looked up from the fixed, closed-enum mapping above, never
    # built from caller-supplied text, so interpolating it into the query is
    # not an injection surface — `ticker` is the only actual input, and it's
    # bound as a parameter below.
    table = _BARS_TABLE_BY_TIMEFRAME[timeframe]
    query = text(f"SELECT time, close FROM {table} WHERE ticker = :ticker ORDER BY time")

    engine = get_engine(config)
    with engine.connect() as conn:
        frame = pd.read_sql(query, conn, params={"ticker": ticker})

    if frame.empty:
        raise ValueError(f"no bars found for ticker={ticker!r} timeframe={timeframe.value!r}")

    series = TimeSeries.from_values(frame["close"].astype(float).to_numpy())
    return SeriesBundle(
        ticker=ticker,
        timeframe=timeframe,
        series=series,
        times=pd.DatetimeIndex(frame["time"]),
    )
