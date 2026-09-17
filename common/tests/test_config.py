import pytest
from pydantic import ValidationError
from quantpipe_common.config import AlpacaConfig, AppConfig, DBConfig, TickerConfig


def test_alpaca_config_reads_from_env(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "key123")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret123")

    config = AlpacaConfig()

    assert config.api_key.get_secret_value() == "key123"
    assert config.secret_key.get_secret_value() == "secret123"
    assert config.data_base_url == "https://data.alpaca.markets"


def test_alpaca_config_missing_required_env_raises(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        AlpacaConfig()


def test_db_config_builds_sqlalchemy_dsn(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "quantpipe")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "quantpipe")
    monkeypatch.setenv("POSTGRES_HOST", "db-host")
    monkeypatch.setenv("POSTGRES_PORT", "5433")

    config = DBConfig()

    assert config.sqlalchemy_dsn == "postgresql+psycopg://quantpipe:secret@db-host:5433/quantpipe"


def test_ticker_config_defaults_to_all_timeframes():
    ticker = TickerConfig(symbol="AAPL", asset_class="us_equity")

    assert ticker.timeframes == ["1m", "5m", "15m", "1h", "1d"]


def test_ticker_config_rejects_unknown_asset_class():
    with pytest.raises(ValidationError):
        TickerConfig(symbol="AAPL", asset_class="futures")


def test_app_config_loads_from_yaml(tmp_path):
    yaml_content = """
tickers:
  - symbol: AAPL
    asset_class: us_equity
  - symbol: BTC/USD
    asset_class: crypto
    timeframes: ["1m", "1h"]
"""
    config_path = tmp_path / "tickers.yaml"
    config_path.write_text(yaml_content)

    config = AppConfig.from_yaml(config_path)

    assert len(config.tickers) == 2
    assert config.tickers[0].symbol == "AAPL"
    assert config.tickers[0].timeframes == ["1m", "5m", "15m", "1h", "1d"]
    assert config.tickers[1].symbol == "BTC/USD"
    assert config.tickers[1].timeframes == ["1m", "1h"]
