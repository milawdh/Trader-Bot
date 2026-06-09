from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.config.models import Settings
from trading_bot.domain import Candle, Side
from trading_bot.strategies.base import StrategyContext
from trading_bot.strategies.strong_candle import StrongCandleStrategy


class StrongCandleStrategyTests(unittest.TestCase):
    def test_bullish_large_body_limited_wick_candle_generates_buy(self) -> None:
        signal = StrongCandleStrategy().generate_signal(
            [_candle("1.10000", "1.10600", "1.09950", "1.10550")],
            StrategyContext(Settings()),
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal.side, Side.BUY)
        self.assertEqual(signal.stop_loss_price, Decimal("1.10350"))
        self.assertEqual(signal.take_profit_price, Decimal("1.11050"))
        self.assertEqual(signal.indicators["body_pips"], Decimal("55"))
        self.assertEqual(signal.indicators["candle_range_pips"], Decimal("65"))
        self.assertEqual(signal.indicators["total_shadow_pips"], Decimal("10"))

    def test_bearish_large_body_limited_wick_candle_generates_sell(self) -> None:
        signal = StrongCandleStrategy().generate_signal(
            [_candle("1.10550", "1.10600", "1.09950", "1.10000")],
            StrategyContext(Settings()),
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal.side, Side.SELL)
        self.assertEqual(signal.stop_loss_price, Decimal("1.10200"))
        self.assertEqual(signal.take_profit_price, Decimal("1.09500"))

    def test_xauusd_uses_gold_pip_size_and_price_digits(self) -> None:
        settings = Settings()
        settings.trading.symbol = "XAUUSD"
        settings.trading.broker_symbol = "XAUUSD"

        signal = StrongCandleStrategy().generate_signal(
            [_candle("2300.00", "2306.00", "2299.50", "2305.50")],
            StrategyContext(settings),
        )

        self.assertIsNotNone(signal)
        self.assertEqual(signal.side, Side.BUY)
        self.assertEqual(signal.stop_loss_price, Decimal("2303.50"))
        self.assertEqual(signal.take_profit_price, Decimal("2310.50"))

    def test_body_must_be_at_least_configured_minimum(self) -> None:
        signal = StrongCandleStrategy().generate_signal(
            [_candle("1.10000", "1.10100", "1.10000", "1.10050")],
            StrategyContext(Settings()),
        )
        self.assertIsNone(signal)

    def test_body_must_not_exceed_configured_maximum(self) -> None:
        signal = StrongCandleStrategy().generate_signal(
            [_candle("1.10000", "1.12600", "1.09950", "1.12500")],
            StrategyContext(Settings()),
        )
        self.assertIsNone(signal)

    def test_total_wick_must_not_exceed_configured_maximum(self) -> None:
        signal = StrongCandleStrategy().generate_signal(
            [_candle("1.10000", "1.10700", "1.09950", "1.10550")],
            StrategyContext(Settings()),
        )
        self.assertIsNone(signal)


def _candle(open_: str, high: str, low: str, close: str) -> Candle:
    return Candle(
        time=datetime(2024, 1, 1, tzinfo=UTC),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        complete=True,
    )


if __name__ == "__main__":
    unittest.main()
