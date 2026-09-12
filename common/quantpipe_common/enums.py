from enum import StrEnum


class AssetClass(StrEnum):
    US_EQUITY = "us_equity"
    CRYPTO = "crypto"


class Timeframe(StrEnum):
    ONE_MINUTE = "1m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


class ModelStage(StrEnum):
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class Source(StrEnum):
    ALPACA = "alpaca"