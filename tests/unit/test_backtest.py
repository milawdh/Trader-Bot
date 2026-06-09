from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_bot.backtest import BacktestEngine
from trading_bot.config.models import Settings
from trading_bot.domain import Candle, Side, TradingSignal
from trading_bot.market_data import generate_demo_candles, generate_demo_candles_for_range
from trading_bot.strategies.base import StrategyContext
from trading_bot.strategies.strong_candle import StrongCandleStrategy


class _OneSignalStrategy:
    name = "TEST_STRATEGY"
    version = "1"
    description = "test"
    parameters_schema = {}

    def __init__(self) -> None:
        self.done = False

    def generate_signal(self, candles: list[Candle], context: StrategyContext) -> TradingSignal | None:
        if self.done or len(candles) < 5:
            return None
        self.done = True
        candle = candles[-1]
        return TradingSignal(
            signal_id="test-signal",
            symbol=context.settings.trading.symbol,
            timeframe=context.settings.trading.timeframe,
            side=Side.BUY,
            candle_time=candle.time,
            entry_reference_price=candle.close,
            stop_loss_price=candle.close - Decimal("0.001"),
            take_profit_price=candle.close + Decimal("0.0015"),
            atr=Decimal("0.001"),
            reason="test",
            strategy_name=self.name,
            indicators={"body_pips": Decimal("10")},
        )


class _EveryCandleStrategy:
    name = "EVERY_CANDLE"
    version = "1"
    description = "test"
    parameters_schema = {}

    def generate_signal(self, candles: list[Candle], context: StrategyContext) -> TradingSignal | None:
        candle = candles[-1]
        return TradingSignal(
            signal_id=f"test-signal-{candle.time.isoformat()}",
            symbol=context.settings.trading.symbol,
            timeframe=context.settings.trading.timeframe,
            side=Side.BUY,
            candle_time=candle.time,
            entry_reference_price=candle.close,
            stop_loss_price=candle.close - Decimal("0.001"),
            take_profit_price=candle.close + Decimal("0.001"),
            atr=Decimal("0.001"),
            reason="test",
            strategy_name=self.name,
        )


class _WrongSymbolStrategy(_OneSignalStrategy):
    def generate_signal(self, candles: list[Candle], context: StrategyContext) -> TradingSignal | None:
        signal = super().generate_signal(candles, context)
        if signal is None:
            return None
        return TradingSignal(
            signal_id=signal.signal_id,
            symbol="EURUSD",
            timeframe=signal.timeframe,
            side=signal.side,
            candle_time=signal.candle_time,
            entry_reference_price=signal.entry_reference_price,
            stop_loss_price=signal.stop_loss_price,
            take_profit_price=signal.take_profit_price,
            atr=signal.atr,
            reason=signal.reason,
            strategy_name=signal.strategy_name,
        )


class BacktestTests(unittest.TestCase):
    def test_backtest_generates_metrics_and_trade_rows(self) -> None:
        settings = Settings()
        settings.risk.minimum_stop_loss_points = 1
        settings.risk.maximum_stop_loss_points = 100000
        settings.session.enabled = False
        candles = generate_demo_candles(80, start=datetime(2024, 1, 1, tzinfo=UTC))
        result = BacktestEngine(settings, _OneSignalStrategy()).run(candles, run_stress=False)
        self.assertIn("net_profit", result.metrics)
        self.assertIn("highest_equity", result.metrics)
        self.assertIn("lowest_equity", result.metrics)
        self.assertGreaterEqual(len(result.equity_curve), 1)
        self.assertGreaterEqual(len(result.trades), 1)

    def test_daily_trade_limit_resets_on_each_new_backtest_day(self) -> None:
        settings = Settings()
        settings.risk.maximum_trades_per_day = 1
        settings.risk.minimum_stop_loss_points = 1
        settings.risk.maximum_stop_loss_points = 100000
        settings.risk.maximum_daily_loss_percent = Decimal("100")
        settings.risk.maximum_total_drawdown_percent = Decimal("100")
        settings.session.enabled = False
        candles = _three_candles_per_day(days=3)

        result = BacktestEngine(settings, _EveryCandleStrategy()).run(candles, run_stress=False)

        self.assertEqual(len(result.trades), 3)

    def test_demo_data_uses_selected_timeframe_step(self) -> None:
        start = datetime(2024, 1, 1, tzinfo=UTC)
        candles = generate_demo_candles_for_range(
            start,
            start,
            "M5",
            minimum_count=1,
            warmup_bars=0,
        )

        self.assertGreaterEqual(len(candles), 288)
        self.assertEqual(candles[1].time - candles[0].time, timedelta(minutes=5))

    def test_demo_data_uses_selected_symbol_price_scale(self) -> None:
        candles = generate_demo_candles(
            3,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            symbol="XAUUSD",
        )

        self.assertEqual(candles[0].open, Decimal("2300.00"))
        self.assertGreater(candles[0].close, Decimal("1000"))

    def test_backtest_result_and_trades_use_configured_symbol(self) -> None:
        settings = Settings()
        settings.trading.symbol = "GBPUSD"
        settings.trading.broker_symbol = "GBPUSD"
        settings.trading.timeframe = "M5"
        settings.risk.minimum_stop_loss_points = 1
        settings.risk.maximum_stop_loss_points = 100000
        settings.session.enabled = False
        candles = generate_demo_candles(80, start=datetime(2024, 1, 1, tzinfo=UTC))

        result = BacktestEngine(settings, _OneSignalStrategy()).run(candles, run_stress=False)

        self.assertEqual(result.symbol, "GBPUSD")
        self.assertEqual(result.timeframe, "M5")
        self.assertGreaterEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].symbol, "GBPUSD")
        self.assertEqual(result.trades[0].signal_reason, "test")
        self.assertEqual(result.trades[0].signal_indicators["body_pips"], Decimal("10"))

    def test_xauusd_demo_backtest_uses_gold_price_scale(self) -> None:
        settings = Settings()
        settings.trading.symbol = "XAUUSD"
        settings.trading.broker_symbol = "XAUUSD"
        settings.trading.timeframe = "M15"
        settings.session.enabled = False
        candles = generate_demo_candles(
            80,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            step=timedelta(minutes=15),
            symbol="XAUUSD",
        )

        result = BacktestEngine(settings, StrongCandleStrategy()).run(candles, run_stress=False)

        self.assertGreaterEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].symbol, "XAUUSD")
        self.assertGreater(result.trades[0].entry_price, Decimal("1000"))
        self.assertIn("body", result.trades[0].signal_reason)
        self.assertIn("total_shadow_pips", result.trades[0].signal_indicators)

    def test_backtest_trades_do_not_use_stale_signal_symbol(self) -> None:
        settings = Settings()
        settings.trading.symbol = "GBPUSD"
        settings.trading.broker_symbol = "GBPUSD"
        settings.risk.minimum_stop_loss_points = 1
        settings.risk.maximum_stop_loss_points = 100000
        settings.session.enabled = False
        candles = generate_demo_candles(80, start=datetime(2024, 1, 1, tzinfo=UTC))

        result = BacktestEngine(settings, _WrongSymbolStrategy()).run(candles, run_stress=False)

        self.assertGreaterEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].symbol, "GBPUSD")


def _three_candles_per_day(days: int) -> list[Candle]:
    candles: list[Candle] = []
    start = datetime(2024, 1, 1, 8, tzinfo=UTC)
    for day in range(days):
        for hour in range(3):
            candles.append(
                Candle(
                    time=start + timedelta(days=day, hours=hour),
                    open=Decimal("1.10000"),
                    high=Decimal("1.10200"),
                    low=Decimal("1.09950"),
                    close=Decimal("1.10000"),
                    spread=1,
                    complete=True,
                )
            )
    return candles


if __name__ == "__main__":
    unittest.main()
