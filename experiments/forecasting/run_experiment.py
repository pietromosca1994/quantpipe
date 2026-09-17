from __future__ import annotations

import argparse
import functools
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from argparse import Namespace

import mlflow
import pandas as pd
from quantpipe_common.config import AppConfig
from quantpipe_common.enums import Timeframe
from quantpipe_common.forecasting.backtest import FoldResult, run_backtest, walk_forward_folds
from quantpipe_common.forecasting.data import SeriesBundle, load_series
from quantpipe_common.forecasting.models import MODEL_REGISTRY

from forecasting.viz import build_html_report

logger = logging.getLogger(__name__)

DEFAULT_TICKERS_CONFIG_PATH = "config/tickers.yaml"
DEFAULT_HORIZON = 5
DEFAULT_MIN_TRAIN_FRACTION = 0.6
DEFAULT_INTERVAL = 0.8
DEFAULT_MAX_FOLDS = 8
DEFAULT_REPORT_HTML = "experiments/output/report.html"
# 1m history is ~100k+ bars/year — every model here is far slower to backtest
# at that size (minutes-to-hours per fold for the neural models), and
# auto_arima's exogenous-regression path outright OOMs on it (see README's
# "Feature support per model" note). Excluded from the default sweep; still
# runnable explicitly via `--timeframes 1m`.
DEFAULT_TIMEFRAMES = [tf.value for tf in Timeframe if tf != Timeframe.ONE_MINUTE]


def _min_train_size(n_observations: int, fraction: float) -> int:
    return max(int(n_observations * fraction), 1)


@dataclass
class TickerTimeframeRun:
    """Everything one (ticker, timeframe) run produced — the long-format rows
    feed the printed/CSV summary and MLflow; `fold_results_by_model` (raw, not
    just the mean) is what the Plotly report needs to draw forecast-vs-actual.
    """

    bundle: SeriesBundle
    rows: list[dict]
    fold_results_by_model: dict[str, list[FoldResult]] = field(default_factory=dict)


def run_one(
    ticker: str,
    timeframe: Timeframe,
    model_names: Iterable[str],
    horizon: int,
    interval: float,
    max_folds: int,
) -> TickerTimeframeRun | None:
    bundle = load_series(ticker, timeframe)
    n = len(bundle.series)
    min_train = _min_train_size(n, DEFAULT_MIN_TRAIN_FRACTION)
    folds = walk_forward_folds(n, horizon=horizon, min_train_size=min_train, step=horizon)
    if len(folds) > max_folds:
        folds = folds[-max_folds:]
    if not folds:
        logger.warning(
            "skipping ticker=%s timeframe=%s: not enough history for horizon=%d "
            "(have %d bars)",
            ticker,
            timeframe.value,
            horizon,
            n,
        )
        return None

    run = TickerTimeframeRun(bundle=bundle, rows=[])
    with mlflow.start_run(run_name=f"{ticker}-{timeframe.value}", nested=True):
        mlflow.log_params(
            {
                "ticker": ticker,
                "timeframe": timeframe.value,
                "horizon": horizon,
                "interval": interval,
                "n_folds": len(folds),
            }
        )
        for name in model_names:
            factory = MODEL_REGISTRY[name]
            with mlflow.start_run(run_name=name, nested=True):
                # Mirrored from the parent run so a model run is self-describing
                # in the MLflow UI (filterable/comparable) without walking up
                # the run tree to see what horizon/interval it was backtested at.
                mlflow.log_params(
                    {
                        "model": name,
                        "ticker": ticker,
                        "timeframe": timeframe.value,
                        "horizon": horizon,
                        "interval": interval,
                    }
                )
                try:
                    fold_results = run_backtest(
                        functools.partial(factory, horizon, interval),
                        bundle.series,
                        folds,
                        interval=interval,
                        past_covariates=bundle.past_covariates,
                        future_covariates=bundle.future_covariates,
                    )
                except Exception:
                    logger.exception(
                        "model=%s failed on ticker=%s timeframe=%s — skipping",
                        name,
                        ticker,
                        timeframe.value,
                    )
                    mlflow.set_tag("status", "failed")
                    continue

                run.fold_results_by_model[name] = fold_results
                mean_metrics = pd.DataFrame([fr.metrics for fr in fold_results]).mean().to_dict()
                mlflow.log_metrics(mean_metrics)
                for metric_name, value in mean_metrics.items():
                    run.rows.append(
                        {
                            "ticker": ticker,
                            "timeframe": timeframe.value,
                            "model": name,
                            "metric": metric_name,
                            "value": value,
                        }
                    )
    return run

def arg_parse() -> Namespace: 
    parser = argparse.ArgumentParser(
        description="Backtest candidate forecasting models across tickers/timeframes."
    )
    parser.add_argument("--tickers-config", default=DEFAULT_TICKERS_CONFIG_PATH)
    parser.add_argument(
        "--tickers",
        nargs="*",
        default=None,
        help="Subset of ticker symbols (default: all from config)",
    )
    parser.add_argument(
        "--timeframes",
        nargs="*",
        default=DEFAULT_TIMEFRAMES,
        help="Subset of timeframes to run (default: all except 1m — see README)",
    )
    parser.add_argument(
        "--models", nargs="*", default=list(MODEL_REGISTRY), help="Subset of model names to run"
    )
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--max-folds", type=int, default=DEFAULT_MAX_FOLDS)
    parser.add_argument("--mlflow-experiment", default="forecasting-model-comparison")
    parser.add_argument("--output-csv", default=None)
    parser.add_argument(
        "--report-html",
        default=DEFAULT_REPORT_HTML,
        help="Path to write the Plotly comparison report to (empty string to skip)",
    )
    args = parser.parse_args()

    return args

def main() -> None:

    args = arg_parse()

    logging.basicConfig(level=logging.INFO)

    app_config = AppConfig.from_yaml(args.tickers_config)
    tickers = args.tickers or [t.symbol for t in app_config.tickers]
    timeframe_by_ticker = {t.symbol: set(t.timeframes) for t in app_config.tickers}
    requested_timeframes = {Timeframe(tf) for tf in args.timeframes}

    mlflow.set_experiment(args.mlflow_experiment)

    runs: list[TickerTimeframeRun] = []
    with mlflow.start_run(run_name="comparison"):
        mlflow.log_params(
            {
                "tickers": ",".join(tickers),
                "timeframes": ",".join(sorted(tf.value for tf in requested_timeframes)),
                "models": ",".join(args.models),
                "horizon": args.horizon,
                "interval": args.interval,
                "max_folds": args.max_folds,
            }
        )
        for ticker in tickers:
            available = timeframe_by_ticker.get(ticker, set())
            for timeframe in sorted(requested_timeframes & available, key=lambda tf: tf.value):
                logger.info("running ticker=%s timeframe=%s", ticker, timeframe.value)
                run = run_one(
                    ticker, timeframe, args.models, args.horizon, args.interval, args.max_folds
                )
                if run is not None:
                    runs.append(run)

    all_rows = [row for run in runs for row in run.rows]
    if not all_rows:
        logger.warning(
            "no results produced — check ticker/timeframe availability and history depth"
        )
        return

    results = pd.DataFrame(all_rows)
    summary = results.pivot_table(
        index=["ticker", "timeframe", "model"], columns="metric", values="value"
    )
    print(summary.to_string())
    if args.output_csv:
        summary.to_csv(args.output_csv)
        logger.info("wrote %s", args.output_csv)

    if args.report_html:
        build_html_report(results, runs, args.report_html)
        logger.info("wrote %s", args.report_html)


if __name__ == "__main__":
    main()
