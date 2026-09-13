"""initial schema: bars_1m, continuous aggregates, predictions, model_registry

Revision ID: 0001
Revises:
Create Date: 2026-09-12

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (view_name, time_bucket width) — derived from bars_1m, never ingested directly.
_AGGREGATES: tuple[tuple[str, str], ...] = (
    ("bars_15m", "15 minutes"),
    ("bars_1h", "1 hour"),
    ("bars_1d", "1 day"),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.create_table(
        "bars_1m",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("ticker", sa.String, primary_key=True),
        sa.Column("asset_class", sa.String, nullable=False),
        sa.Column("open", sa.Numeric, nullable=False),
        sa.Column("high", sa.Numeric, nullable=False),
        sa.Column("low", sa.Numeric, nullable=False),
        sa.Column("close", sa.Numeric, nullable=False),
        sa.Column("volume", sa.Numeric, nullable=False),
        sa.Column("source", sa.String, nullable=False, server_default="alpaca"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String, nullable=False),
    )
    op.execute("SELECT create_hypertable('bars_1m', 'time')")

    for view_name, bucket in _AGGREGATES:
        op.execute(f"""
            CREATE MATERIALIZED VIEW {view_name}
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('{bucket}', time) AS time,
                ticker,
                asset_class,
                first(open, time) AS open,
                max(high) AS high,
                min(low) AS low,
                last(close, time) AS close,
                sum(volume) AS volume
            FROM bars_1m
            GROUP BY time_bucket('{bucket}', time), ticker, asset_class
            WITH NO DATA
        """)
        op.execute(f"""
            SELECT add_continuous_aggregate_policy('{view_name}',
                start_offset => NULL,
                end_offset => INTERVAL '{bucket}',
                schedule_interval => INTERVAL '{bucket}')
        """)

    op.create_table(
        "predictions",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("ticker", sa.String, primary_key=True),
        sa.Column("timeframe", sa.String, primary_key=True),
        sa.Column("model_version", sa.String, primary_key=True),
        sa.Column("horizon", sa.Integer, primary_key=True),
        sa.Column("yhat", sa.Numeric, nullable=False),
        sa.Column("yhat_lower", sa.Numeric, nullable=False),
        sa.Column("yhat_upper", sa.Numeric, nullable=False),
        sa.Column("mlflow_run_id", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String, nullable=False),
    )
    op.execute("SELECT create_hypertable('predictions', 'time')")

    op.create_table(
        "model_registry",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String, nullable=False),
        sa.Column("timeframe", sa.String, nullable=False),
        sa.Column("mlflow_run_id", sa.String, nullable=False),
        sa.Column("mlflow_model_uri", sa.String, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_model_registry_ticker_timeframe_status",
        "model_registry",
        ["ticker", "timeframe", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_registry_ticker_timeframe_status", table_name="model_registry")
    op.drop_table("model_registry")
    op.drop_table("predictions")
    for view_name, _ in reversed(_AGGREGATES):
        op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {view_name} CASCADE")
    op.drop_table("bars_1m")
