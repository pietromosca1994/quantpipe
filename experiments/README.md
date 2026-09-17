# Forecasting model comparison

Research/backtesting harness for evaluating candidate forecasting model
families against real QuantPipe bar data, before any model type is chosen for
`services/training`. This code is **not deployed** — no Dockerfile, no
Prefect flow, no schedule. Run it locally against the same TimescaleDB the
ingestion service writes to.

## Where the code actually lives

The reusable forecasting core — `BaseForecaster`, the model wrappers, the
walk-forward backtest engine, the metrics — lives in
`common/quantpipe_common/forecasting/`, **not** in this directory. That's
deliberate: `services/training` will need the exact same interface and model
implementations to actually fit and validate whichever model family gets
chosen, and duplicating that logic here vs. there would drift. This
directory only holds what's specific to *comparing many candidates at once*:

- `forecasting/run_experiment.py` — the CLI that sweeps ticker × timeframe ×
  model, using `quantpipe_common.forecasting` for every fit/predict/score
  step, and logs to MLflow.
- `forecasting/viz.py` — builds the Plotly HTML comparison report (see
  below). Nothing outside `experiments/` depends on this — a production
  training run doesn't need an interactive dashboard, just the chosen
  metric.

See `common/quantpipe_common/forecasting/`'s module docstrings for the core
design notes (integer-RangeIndex series, the `BaseForecaster` contract, how
intervals are extracted per model family, the metric definitions). This file
only covers what's specific to running the comparison sweep.

## Setup

```
.venv/Scripts/pip install -e "./common[forecasting]"
.venv/Scripts/pip install -r experiments/requirements.txt
```

Assumes `requirements-dev.txt` is already installed per the root README's
local dev setup, and the same `POSTGRES_*` env vars ingestion uses (from
`.env`) are available in the shell.

## Before trusting this against your installed Darts version

The exact method Darts uses to pull a quantile out of a probabilistic
prediction (`TimeSeries.quantile()`, renamed from `quantile_timeseries()`
pre-0.31) has moved across releases.
`result_from_stochastic_series()` in
`common/quantpipe_common/forecasting/base.py` is the single place that calls
it — if a run errors there, that's the first thing to check against whatever
`darts` version `pip install` actually resolved.

## Running

```
.venv/Scripts/python -m forecasting.run_experiment \
  --tickers AAPL MSFT \
  --timeframes 5m 15m 1h 1d \
  --horizon 5 \
  --max-folds 8
```

Neural models (`nbeats`, `nhits`) are the slowest to backtest — each fold
retrains from scratch by design (a real walk-forward evaluation, not a single
train/test split), so start with the cheaper families to get baseline numbers
quickly:

```
--models naive_seasonal naive_drift ets theta auto_arima lightgbm
```

then add `nbeats nhits` once those look reasonable. `--max-folds` caps how
many walk-forward folds run per (ticker, timeframe, model) — lower it further
while iterating. `1m`/`5m` history needs a much longer backfill than `1d` to
produce enough folds — run `./scripts/backfill.sh` first if a timeframe gets
skipped with "not enough history".

## Reading the results

Besides the printed/CSV summary and MLflow logging, every run writes a
self-contained HTML report (`--report-html`, default
`experiments/output/report.html`; pass `--report-html ""` to skip it) with:

- A **model × timeframe heatmap** per metric (MAE, RMSE, directional
  accuracy, coverage), averaged across tickers — the fastest way to see
  which model family wins at which aggregation, per the original "some
  models work fine on different aggregations" question this harness exists
  to answer.
- A **grouped bar comparison** of every model's metrics, per (ticker, timeframe).
- A **forecast-vs-actual overlay** per (ticker, timeframe): the real close
  price in black, each model's stitched-across-folds forecast as its own
  toggleable line (click a legend entry to isolate one model) with its
  interval band shaded — this is the "does the forecast actually track the
  new data" view, not just an aggregate error number.

Open the file directly in a browser; it loads Plotly from a CDN so it's a
single portable file, no server needed.

## Once you've picked a model family

This harness is deliberately separate from `services/training` — nothing
here is wired into a Prefect schedule. When a model family (possibly a
different one per timeframe) is chosen, that's the point to build
`services/training/src/training/{features,train,flow}.py` against
`quantpipe_common.forecasting` directly, with an explicit promotion metric
per the model-lifecycle design notes — `run_backtest`/`walk_forward_folds`
are exactly what that promotion-check validation should use too, not just
this comparison sweep.
