from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

if TYPE_CHECKING:
    from quantpipe_common.forecasting.backtest import FoldResult
    from quantpipe_common.forecasting.data import SeriesBundle

# Lower-is-better metrics get a reversed (low=green) colorscale in the heatmap;
# anything else (directional_accuracy, coverage) is treated as higher-is-better.
_LOWER_IS_BETTER = {"mae", "rmse", "pinball_lower", "pinball_upper"}
_COMPARISON_METRICS = ("mae", "rmse", "directional_accuracy", "coverage")


def stitch_fold_forecasts(fold_results: list[FoldResult]) -> pd.DataFrame:
    """Concatenate one model's per-fold forecasts into a single frame indexed
    by the bar position each forecast step was made for, so the whole
    backtest can be drawn as one continuous line instead of per-fold
    fragments. Folds are non-overlapping by construction (see
    `walk_forward_folds`'s default `step=horizon`), so this never double-counts
    a bar.
    """
    rows = [
        {
            "bar_index": fold_result.fold.train_end + step,
            "actual": actual,
            "yhat": yhat,
            "yhat_lower": lower,
            "yhat_upper": upper,
        }
        for fold_result in fold_results
        for step, (actual, yhat, lower, upper) in enumerate(
            zip(
                fold_result.actual,
                fold_result.forecast.yhat,
                fold_result.forecast.yhat_lower,
                fold_result.forecast.yhat_upper,
                strict=True,
            )
        )
    ]
    return pd.DataFrame(rows)


def plot_forecast_vs_actual(
    bundle: SeriesBundle,
    fold_results_by_model: dict[str, list[FoldResult]],
    title: str | None = None,
) -> go.Figure:
    """Overlay every model's stitched forecast against the actual close price
    over the backtest window. Actual is drawn once in black; each model is a
    separate, independently toggleable trace (click its legend entry to
    isolate it) with its interval band as a matching shaded region.
    """
    fig = go.Figure()
    frames = {
        name: stitch_fold_forecasts(results) for name, results in fold_results_by_model.items()
    }
    frames = {name: frame for name, frame in frames.items() if not frame.empty}
    if not frames:
        fig.update_layout(title=title or "no successful model runs to plot")
        return fig

    times = bundle.times.to_numpy()
    palette = px.colors.qualitative.Plotly

    actual_frame = next(iter(frames.values()))
    fig.add_trace(
        go.Scatter(
            x=times[actual_frame["bar_index"].to_numpy()],
            y=actual_frame["actual"].to_numpy(),
            name="actual",
            mode="lines",
            line={"color": "black", "width": 2},
        )
    )

    for i, (name, frame) in enumerate(frames.items()):
        color = palette[i % len(palette)]
        frame_times = times[frame["bar_index"].to_numpy()]
        fig.add_trace(
            go.Scatter(
                x=frame_times,
                y=frame["yhat"],
                name=f"{name} forecast",
                mode="lines",
                line={"color": color},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=list(frame_times) + list(frame_times[::-1]),
                y=list(frame["yhat_upper"]) + list(frame["yhat_lower"][::-1]),
                fill="toself",
                fillcolor=color,
                opacity=0.15,
                line={"width": 0},
                name=f"{name} interval",
                legendgroup=name,
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title=title or f"{bundle.ticker} ({bundle.timeframe.value}) — forecast vs. actual",
        xaxis_title="time",
        yaxis_title="close",
        legend={"orientation": "h", "y": -0.2},
    )
    return fig


def plot_metric_comparison(summary_long: pd.DataFrame, ticker: str, timeframe: str) -> go.Figure:
    """Grouped bar chart of every model's mean metrics for one ticker/timeframe."""
    subset = summary_long[
        (summary_long["ticker"] == ticker)
        & (summary_long["timeframe"] == timeframe)
        & (summary_long["metric"].isin(_COMPARISON_METRICS))
    ]
    fig = px.bar(
        subset,
        x="model",
        y="value",
        color="model",
        facet_col="metric",
        facet_col_wrap=2,
        title=f"{ticker} ({timeframe}) — model comparison",
    )
    fig.update_yaxes(matches=None)
    return fig


def plot_metric_heatmap(summary_long: pd.DataFrame, metric: str) -> go.Figure:
    """Model x timeframe heatmap of one metric, averaged across tickers —
    surfaces which model families work best at which aggregation.
    """
    subset = summary_long[summary_long["metric"] == metric]
    pivot = subset.pivot_table(index="model", columns="timeframe", values="value", aggfunc="mean")
    color_scale = "RdYlGn_r" if metric in _LOWER_IS_BETTER else "RdYlGn"
    fig = px.imshow(pivot, text_auto=".3f", aspect="auto", color_continuous_scale=color_scale)
    fig.update_layout(title=f"{metric} by model x timeframe (mean across tickers)")
    return fig


def build_html_report(summary_long: pd.DataFrame, runs: list, output_path: str) -> None:
    """Assemble the heatmaps, per-(ticker,timeframe) comparison bars, and
    forecast-vs-actual overlays into one self-contained HTML file. `runs` is
    the list of `TickerTimeframeRun` objects `run_experiment.py` collects —
    typed loosely here (not imported directly) to avoid a circular import
    between this module and run_experiment.py.
    """
    figures: list[go.Figure] = [
        plot_metric_heatmap(summary_long, metric)
        for metric in _COMPARISON_METRICS
        if metric in set(summary_long["metric"])
    ]

    for run in runs:
        ticker, timeframe = run.bundle.ticker, run.bundle.timeframe.value
        figures.append(plot_metric_comparison(summary_long, ticker, timeframe))
        figures.append(plot_forecast_vs_actual(run.bundle, run.fold_results_by_model))

    html_parts = [
        fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False)
        for i, fig in enumerate(figures)
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<html><head><title>Forecasting model comparison</title></head><body>\n"
        + "\n<hr>\n".join(html_parts)
        + "\n</body></html>\n",
        encoding="utf-8",
    )
