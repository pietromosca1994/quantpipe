# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository is currently pre-implementation: it contains only `README.md` and `.gitignore` (a Python-oriented ignore file). There is no code, no `docker-compose.yml`, no Terraform, and no build/lint/test tooling yet. The full design lives in an Obsidian vault at `C:\Users\pmosca\Desktop\repos\obsidian_vault\Projects\QuantPipe\` (README, architecture, data-model, orchestration, model-lifecycle, observability, infrastructure, repository-structure, roadmap) — treat those notes as the spec. When implementation begins, follow the structure and conventions below and update this file with real commands (package manager, test runner, migration commands, etc.) once they exist.

## What QuantPipe is

Self-hosted infrastructure (single Oracle Cloud Always-Free VM) that periodically ingests market data (stocks + crypto via Alpaca), stores it in TimescaleDB, retrains per-ticker/per-timeframe forecasting models tracked in MLflow, computes and stores predictions, and visualizes both via Grafana. All scheduled work is orchestrated by Prefect; all cloud resources are provisioned by Terraform; all services run via Docker Compose on one VM.

v1 scope is stocks + crypto through Alpaca on a single VM. Explicitly deferred: true commodities/futures data, CI/CD, backup/DR automation, secrets management beyond `.env`, Grafana alerting, and any multi-instance/HA setup — do not build toward these unless asked.

## Planned repository layout

```
quantpipe/
├── infra/terraform/          # VCN/subnet/security list, Ampere A1 instance, Block Volume, Object Storage bucket
├── docker-compose.yml        # timescaledb, prefect-server/-worker, ingestion, training, inference, mlflow, prometheus, grafana, exporters
├── services/
│   ├── ingestion/            # Alpaca client + Prefect flow: fetch -> validate -> upsert bars_1m
│   ├── training/             # pulls history -> trains -> logs to MLflow -> promotes if better
│   ├── inference/             # resolves production model -> predicts -> writes to predictions
│   └── prefect_flows/         # deployments.py: schedules for all three flows, kept separate from flow logic
├── common/quantpipe_common/   # shared package: Pydantic config/schemas, SQLAlchemy models, session factory, Alembic migrations
├── experiments/                # research harness: backtests candidate forecasting models, not deployed
├── monitoring/                # prometheus.yml, Grafana datasource/dashboard provisioning
└── config/tickers.yaml        # user-editable ticker/timeframe list, read via quantpipe_common.config
```

`common/quantpipe_common` is the single source of truth for schemas and DB models — every service depends on it rather than redefining `Bar`/`Prediction`/DB session logic independently. Keep it that way as services are built: don't let a service define its own copy of a shared schema.

## Core architectural principles (apply these when adding anything)

1. **Ingest only the finest granularity.** `bars_1m` is the only table ingestion ever writes to. `bars_5m`/`bars_15m`/`bars_1h`/`bars_1d` are TimescaleDB **continuous aggregates** derived from it, not separately ingested tables — adding a timeframe is a migration, not a new ingestion job. Never add a second ingestion path for a coarser timeframe.
2. **Pydantic at the boundary, SQLAlchemy at the database.** Every external input (Alpaca API responses, `config/tickers.yaml`, env-derived settings via `pydantic-settings`) is validated into a Pydantic model first. Every DB read/write goes through SQLAlchemy ORM models (`Bar`, `Prediction`, `ModelRegistryEntry`) managed by Alembic migrations. Pydantic objects are converted to ORM objects/dicts immediately before persistence — don't let validation and persistence concerns mix in the same object.
3. **MLflow's registry is the only source of truth for "current production model."** Training logs runs and promotes to `Production` only after an explicit metric comparison against the current Production version (never "always promote newest"). The `model_registry` Postgres table is a queryable cache of MLflow's state, kept in sync by the training service on every promotion — inference reads that table, not the MLflow API, on each cycle.
4. **Prefect owns all scheduling.** Ingestion, training, and inference cadence, retries, and run history all live in Prefect deployments (`services/prefect_flows/deployments.py`), not in ad hoc cron/sleep loops inside a service. Training cadence is matched to timeframe (e.g. `1m`/`5m`/`15m` daily, `1h`/`1d` weekly-or-monthly) — don't retrain a coarse-timeframe model on a fine-timeframe schedule.
5. **Every service is observable the same way.** Each of ingestion/training/inference exposes a `/metrics` endpoint via `prometheus_client` with counters for the same shape of thing (rows written, errors, cycle duration) so Grafana's ops dashboard stays uniform as services are added.
6. **Terraform provisions; Compose runs.** `terraform apply` only touches VM/network/storage. `docker compose up -d --build` is how code changes reach the VM. Never fold service deployment logic into Terraform or infrastructure provisioning into Compose.
7. **Nothing but SSH and Grafana is exposed on the public network.** Postgres/Timescale, Prometheus, MLflow, and the Prefect API are reachable only on the Docker-internal network. Don't add a `ports:` mapping that exposes an internal service publicly without updating the Terraform security list deliberately.

## Data model quick reference

- `bars_1m` (hypertable): `time, ticker, asset_class, open, high, low, close, volume, source, created_at, created_by` — uniqueness on `(ticker, time)`.
- `predictions` (hypertable): `time, ticker, timeframe, model_version, horizon, yhat, yhat_lower, yhat_upper, mlflow_run_id, created_at, created_by`.
- `model_registry` (plain table): `ticker, timeframe, mlflow_run_id, mlflow_model_uri, version, status (staging|production|archived), trained_at, metrics (jsonb)`.

Full column/type detail and the continuous-aggregate definitions are in the vault's `data-model.md`.

## Secrets

Alpaca keys, DB credentials, and Object Storage credentials live in a `.env` file on the VM (`.env.example` is the committed template) — this is a known v1 limitation, not a pattern to extend. Terraform variables (admin IP, tenancy/compartment OCIDs, SSH key) belong in `terraform.tfvars` (gitignored); `terraform.tfvars.example` is the template. Never commit `*.tfstate*` — it contains plaintext resource attributes including generated credentials; `.terraform.lock.hcl` is the one Terraform file that *should* be committed.
