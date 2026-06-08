from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_bot.config.models import Settings
from trading_bot.domain import Candle, Side
from trading_bot.strategies.base import StrategyContext
from trading_bot.strategies.trend_pullback import TrendPullbackStrategy


class StrategyTests(unittest.TestCase):
    def test_buy_signal_generation(self) -> None:
        settings = _fast_settings()
        closes = ["1.00", "1.01", "1.02", "1.03", "1.04", "1.05", "1.06", "1.03", "1.02", "1.08"]
        candles = _candles(closes)
        signal = TrendPullbackStrategy().generate_signal(candles, StrategyContext(settings))
        self.assertIsNotNone(signal)
        self.assertEqual(signal.side, Side.BUY)

    def test_sell_signal_generation(self) -> None:
        settings = _fast_settings()
        closes = ["1.10", "1.09", "1.08", "1.07", "1.06", "1.05", "1.04", "1.07", "1.08", "1.02"]
        candles = _candles(closes)
        signal = TrendPullbackStrategy().generate_signal(candles, StrategyContext(settings))
        self.assertIsNotNone(signal)
        self.assertEqual(signal.side, Side.SELL)

    def test_incomplete_latest_candle_is_excluded(self) -> None:
        settings = _fast_settings()
        closes = ["1.00", "1.01", "1.02", "1.03", "1.04", "1.05", "1.06", "1.03", "1.02", "1.08"]
        candles = _candles(closes)
        candles.append(
            Candle(
                candles[-1].time + timedelta(hours=1),
                Decimal("1.08"),
                Decimal("1.12"),
                Decimal("1.07"),
                Decimal("1.11"),
                complete=False,
            )
        )
        signal = TrendPullbackStrategy().generate_signal(candles, StrategyContext(settings))
        self.assertIsNotNone(signal)
        self.assertEqual(signal.candle_time, candles[-2].time)


def _fast_settings() -> Settings:
    settings = Settings()
    settings.strategy.fast_ema_period = 3
    settings.strategy.slow_ema_period = 5
    settings.strategy.rsi_period = 3
    settings.strategy.atr_period = 3
    settings.strategy.pullback_lookback_bars = 3
    settings.strategy.stop_loss_atr_multiplier = Decimal("1")
    settings.strategy.take_profit_atr_multiplier = Decimal("1.5")
    settings.risk.minimum_stop_loss_points = 1
    settings.risk.maximum_stop_loss_points = 100000
    return settings


def _candles(closes: list[str]) -> list[Candle]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles: list[Candle] = []
    previous = Decimal(closes[0])
    for index, value in enumerate(closes):
        close = Decimal(value)
        open_price = previous
        high = max(open_price, close) + Decimal("0.004")
        low = min(open_price, close) - Decimal("0.004")
        candles.append(
            Candle(
                time=start + timedelta(hours=index),
                open=open_price,
                high=high,
                low=low,
                close=close,
                tick_volume=1000,
                spread=12,
                complete=True,
            )
        )
        previous = close
    return candles


if __name__ == "__main__":
    unittest.main()

