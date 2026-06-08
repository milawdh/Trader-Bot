from __future__ import annotations

from datetime import date, datetime

from trading_bot.backtest import BacktestEngine
from trading_bot.config.models import Settings
from trading_bot.domain import BacktestResult, Candle
from trading_bot.persistence import TradingBotDatabase
from trading_bot.strategies import default_strategy_registry


class BacktestRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = default_strategy_registry()

    def run(self, candles: list[Candle], persist: bool = True) -> BacktestResult:
        descriptor = self.registry.get(self.settings.strategy.strategy_id)
        engine = BacktestEngine(self.settings, descriptor.strategy)
        result = engine.run(self._filter_by_date_range(candles))
        if persist:
            TradingBotDatabase(self.settings.ui.database_path).save_backtest_result(result)
        return result

    def _filter_by_date_range(self, candles: list[Candle]) -> list[Candle]:
        start_date = _parse_date(self.settings.backtest.start_date)
        end_date = _parse_date(self.settings.backtest.end_date)
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        return [
            candle
            for candle in candles
            if start_date <= candle.time.date() <= end_date
        ]


def _parse_date(value: str) -> date:
    parsed = datetime.fromisoformat(str(value))
    return parsed.date()
