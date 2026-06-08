from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_bot.domain import Candle
from trading_bot.indicators import atr, ema, rsi


class IndicatorTests(unittest.TestCase):
    def test_ema_calculates_seed_and_next_value(self) -> None:
        values = [Decimal(v) for v in ["1", "2", "3", "4"]]
        result = ema(values, 3)
        self.assertIsNone(result[1])
        self.assertEqual(result[2], Decimal("2"))
        self.assertEqual(result[3], Decimal("3.0"))

    def test_rsi_returns_100_when_no_losses(self) -> None:
        values = [Decimal(v) for v in ["1", "2", "3", "4", "5"]]
        result = rsi(values, 3)
        self.assertEqual(result[3], Decimal("100"))

    def test_atr_uses_true_range(self) -> None:
        start = datetime(2024, 1, 1, tzinfo=UTC)
        candles = [
            Candle(start + timedelta(hours=i), Decimal("1"), Decimal("2"), Decimal("0.5"), Decimal("1.5"))
            for i in range(4)
        ]
        result = atr(candles, 3)
        self.assertEqual(result[2], Decimal("1.5"))


if __name__ == "__main__":
    unittest.main()

