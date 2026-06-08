class TradingBotError(Exception):
    """Base application exception."""


class ConfigurationError(TradingBotError):
    """Raised when configuration is invalid."""


class MarketDataError(TradingBotError):
    """Raised when candles, ticks, or symbol metadata are invalid."""


class ExecutionError(TradingBotError):
    """Raised when execution validation or order submission fails."""

