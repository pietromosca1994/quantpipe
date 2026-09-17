from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from forecasting.viz import (
    build_html_report,
    plot_forecast_vs_actual,
    plot_metric_comparison,
    plot_metric_heatmap,
    stitch_fold_forecasts,
)
from quantpipe_common.forecasting.backtest import Fold, FoldResult
from quantpipe_common.forecasting.base import ForecastResult


def _fold_result(train_end: int, actual: list[float], yhat: list[float]) -> FoldResult:
    yhat_arr = np.array(yhat)
    return FoldResult(
        fold=Fold(train_end=train_end, horizon=len(actual)),
        forecast=ForecastResult(
            yhat=yhat_arr,
            yhat_lower=yhat_arr - 1,
            yhat_upper=yhat_arr + 1,
            lower_quantile=0.1,
            upper_quantile=0.9,
        ),
        actual=np.array(actual),
        metrics={"mae": 0.5, "rmse": 0.7, "directional_accuracy": 0.55, "coverage": 0.8},
    )


def _fake_bundle(n: int = 8) -> SimpleNamespace:
    return SimpleNamespace(
        ticker="AAPL",
        timeframe=SimpleNamespace(value="1h"),
        times=pd.DatetimeIndex(pd.date_range("2026-01-01", periods=n, freq="h")),
    )


def _summary_long() -> pd.DataFrame:
    rows = [
        {"ticker": "AAPL", "timeframe": timeframe, "model": model, "metric": metric, "value": value}
        for model in ("naive_seasonal", "lightgbm")
        for timeframe in ("5m", "1h")
        for metric, value in (
            ("mae", 0.5),
            ("rmse", 0.7),
            ("directional_accuracy", 0.55),
            ("coverage", 0.8),
        )
    ]
    return pd.DataFrame(rows)


def test_stitch_fold_forecasts_concatenates_folds_by_bar_index():
    fold_results = [
        _fold_result(train_end=4, actual=[10.5, 11.5], yhat=[10.0, 11.0]),
        _fold_result(train_end=6, actual=[12.5, 13.5], yhat=[12.0, 13.0]),
    ]

    frame = stitch_fold_forecasts(fold_results)

    assert list(frame["bar_index"]) == [4, 5, 6, 7]
    assert list(frame["actual"]) == [10.5, 11.5, 12.5, 13.5]
    assert list(frame["yhat"]) == [10.0, 11.0, 12.0, 13.0]


def test_plot_forecast_vs_actual_draws_actual_and_each_model_as_a_trace():
    fold_results = [
        _fold_result(train_end=4, actual=[10.5, 11.5, 12.5, 13.5], yhat=[10, 11, 12, 13])
    ]

    fig = plot_forecast_vs_actual(_fake_bundle(), {"naive_seasonal": fold_results})

    assert isinstance(fig, go.Figure)
    trace_names = [trace.name for trace in fig.data]
    assert "actual" in trace_names
    assert "naive_seasonal forecast" in trace_names


def test_plot_forecast_vs_actual_handles_no_successful_models():
    fig = plot_forecast_vs_actual(_fake_bundle(), {})

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_plot_metric_comparison_returns_a_figure():
    fig = plot_metric_comparison(_summary_long(), "AAPL", "1h")

    assert isinstance(fig, go.Figure)


def test_plot_metric_heatmap_returns_a_figure():
    fig = plot_metric_heatmap(_summary_long(), "mae")

    assert isinstance(fig, go.Figure)


def test_build_html_report_writes_a_self_contained_html_file(tmp_path):
    fold_results = [
        _fold_result(train_end=4, actual=[10.5, 11.5, 12.5, 13.5], yhat=[10, 11, 12, 13])
    ]
    run = SimpleNamespace(
        bundle=_fake_bundle(), fold_results_by_model={"naive_seasonal": fold_results}
    )
    output_path = tmp_path / "report.html"

    build_html_report(_summary_long(), [run], str(output_path))

    content = output_path.read_text(encoding="utf-8")
    assert "plotly" in content.lower()
