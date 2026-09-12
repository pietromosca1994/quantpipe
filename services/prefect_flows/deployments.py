"""Schedules for all QuantPipe flows, centralized and kept separate from flow logic.

Run this module as a long-lived process (see docker-compose.yml's `ingestion-flows`
service) to keep every deployment below scheduled and served.
"""

from __future__ import annotations

from ingestion.flow import ingest_bars
from ingestion.metrics import start_metrics_server
from prefect import serve

INGEST_BARS_INTERVAL_SECONDS = 120
METRICS_PORT = 8000


def main() -> None:
    # This process is what actually runs in docker-compose (see the
    # ingestion-flows service) — start the /metrics endpoint here, not in
    # flow.py's __main__, since that path isn't used when serve()d.
    start_metrics_server(port=METRICS_PORT)

    ingest_deployment = ingest_bars.to_deployment(
        name="ingest-bars",
        interval=INGEST_BARS_INTERVAL_SECONDS,
    )

    # Future deployments, added once services/training and services/inference exist:
    #
    # from training.flow import train_model
    # train_1h_deployment = train_model.to_deployment(
    #     name="train-model-1h",
    #     cron="0 3 * * 1",  # weekly — matched to the 1h timeframe's retrain cadence
    # )
    #
    # from inference.flow import predict
    # predict_1h_deployment = predict.to_deployment(
    #     name="predict-1h",
    #     cron="1 * * * *",  # a few seconds after each hour boundary
    # )
    #
    # serve(ingest_deployment, train_1h_deployment, predict_1h_deployment)

    serve(ingest_deployment)


if __name__ == "__main__":
    main()
