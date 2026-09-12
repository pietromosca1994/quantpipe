from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Bar(Base):
    """Raw 1-minute bars — the only table ingestion writes to.

    Coarser timeframes (bars_15m/1h/1d) are TimescaleDB continuous aggregates
    derived from this table, not separate ORM models — see the initial migration.
    """

    __tablename__ = "bars_1m"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    asset_class: Mapped[str] = mapped_column(String, nullable=False)
    open: Mapped[float] = mapped_column(Numeric, nullable=False)
    high: Mapped[float] = mapped_column(Numeric, nullable=False)
    low: Mapped[float] = mapped_column(Numeric, nullable=False)
    close: Mapped[float] = mapped_column(Numeric, nullable=False)
    volume: Mapped[float] = mapped_column(Numeric, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="alpaca")


class Prediction(Base):
    """A forecast point. Not yet written by any service — inference will own this."""

    __tablename__ = "predictions"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    timeframe: Mapped[str] = mapped_column(String, primary_key=True)
    model_version: Mapped[str] = mapped_column(String, primary_key=True)
    horizon: Mapped[int] = mapped_column(primary_key=True)
    yhat: Mapped[float] = mapped_column(Numeric, nullable=False)
    yhat_lower: Mapped[float] = mapped_column(Numeric, nullable=False)
    yhat_upper: Mapped[float] = mapped_column(Numeric, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelRegistryEntry(Base):
    """Queryable cache of MLflow's registry state. Not yet written by any service —
    training will upsert this on every promotion; inference will read it.
    """

    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    mlflow_run_id: Mapped[str] = mapped_column(String, nullable=False)
    mlflow_model_uri: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
