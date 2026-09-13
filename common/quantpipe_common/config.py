from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from quantpipe_common.enums import AssetClass, Timeframe

ALL_TIMEFRAMES: tuple[Timeframe, ...] = tuple(Timeframe)


class AlpacaConfig(BaseSettings):
    """Alpaca Market Data API credentials, loaded from ALPACA_* env vars."""

    model_config = SettingsConfigDict(env_prefix="ALPACA_", extra="ignore")

    api_key: SecretStr
    secret_key: SecretStr
    data_base_url: str = "https://data.alpaca.markets"
    # "iex" is the only feed a free/basic Alpaca plan can query for recent
    # (non-15-min-delayed) equity bars — "sip" needs a paid market data
    # subscription. Override via ALPACA_FEED if the account has one.
    feed: Literal["iex", "sip", "delayed_sip"] = "iex"


class DBConfig(BaseSettings):
    """Postgres/TimescaleDB connection settings, loaded from POSTGRES_* env vars."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    user: str
    password: SecretStr
    db: str
    host: str = "localhost"
    port: int = 5432

    @property
    def sqlalchemy_dsn(self) -> str:
        # Built via sqlalchemy.URL rather than an f-string so a password
        # containing "@", ":", or "/" is percent-encoded correctly.
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.db,
        ).render_as_string(hide_password=False)


class TickerConfig(BaseModel):
    """One entry from config/tickers.yaml."""

    symbol: str
    asset_class: AssetClass
    timeframes: list[Timeframe] = Field(default_factory=lambda: list(ALL_TIMEFRAMES))


class AppConfig(BaseModel):
    """The full validated contents of config/tickers.yaml."""

    tickers: list[TickerConfig]

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppConfig:
        raw = yaml.safe_load(Path(path).read_text())
        return cls.model_validate(raw)
