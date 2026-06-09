from __future__ import annotations

from decimal import Decimal

from trading_bot.common.decimal_utils import quantize_price
from trading_bot.common.identifiers import signal_id
from trading_bot.config.models import StrategySettings
from trading_bot.domain import Candle, Side, TradingSignal
from trading_bot.indicators import atr, ema, rsi
from trading_bot.market_data import price_digits_for_symbol
from trading_bot.strategies.base import StrategyContext


class TrendPullbackStrategy:
    name = "TREND_PULLBACK_V1"
    version = "1.0.0"
    description = (
        "EURUSD H1 trend-pullback strategy using EMA 50/200, RSI 14 pullback and "
        "RSI 50 confirmation. Signals are generated only from completed candles."
    )
    parameters_schema = {
        "fast_ema_period": "Fast trend EMA period",
        "slow_ema_period": "Slow trend EMA period",
        "rsi_period": "RSI period used for pullback and confirmation",
        "atr_period": "ATR period used for SL/TP",
        "stop_loss_atr_multiplier": "ATR multiplier for stop loss",
        "take_profit_atr_multiplier": "ATR multiplier for take profit",
    }

    def generate_signal(
        self,
        candles: list[Candle],
        context: StrategyContext,
    ) -> TradingSignal | None:
        completed = [candle for candle in candles if candle.complete]
        settings = context.settings.strategy
        minimum = self.required_history(settings)
        if len(completed) < minimum:
            return None

        closes = [candle.close for candle in completed]
        fast = ema(closes, settings.fast_ema_period)
        slow = ema(closes, settings.slow_ema_period)
        rsi_values = rsi(closes, settings.rsi_period)
        atr_values = atr(completed, settings.atr_period)

        current = completed[-1]
        previous_index = len(completed) - 2
        current_index = len(completed) - 1
        current_fast = fast[current_index]
        current_slow = slow[current_index]
        current_rsi = rsi_values[current_index]
        previous_rsi = rsi_values[previous_index]
        current_atr = atr_values[current_index]
        if None in {current_fast, current_slow, current_rsi, previous_rsi, current_atr}:
            return None
        if current_atr is None or current_atr <= 0:
            return None

        lookback_start = max(0, current_index - settings.pullback_lookback_bars)
        lookback_rsi = [
            value
            for value in rsi_values[lookback_start:current_index]
            if value is not None
        ]
        if not lookback_rsi:
            return None

        buy_signal = self._is_buy(
            current=current,
            fast=current_fast,
            slow=current_slow,
            previous_rsi=previous_rsi,
            current_rsi=current_rsi,
            lookback_rsi=lookback_rsi,
            settings=settings,
        )
        sell_signal = self._is_sell(
            current=current,
            fast=current_fast,
            slow=current_slow,
            previous_rsi=previous_rsi,
            current_rsi=current_rsi,
            lookback_rsi=lookback_rsi,
            settings=settings,
        )
        if not buy_signal and not sell_signal:
            return None

        side = Side.BUY if buy_signal else Side.SELL
        entry = current.close
        symbol_name = context.settings.trading.broker_symbol or context.settings.trading.symbol
        digits = price_digits_for_symbol(symbol_name)
        if side is Side.BUY:
            stop_loss = entry - current_atr * settings.stop_loss_atr_multiplier
            take_profit = entry + current_atr * settings.take_profit_atr_multiplier
        else:
            stop_loss = entry + current_atr * settings.stop_loss_atr_multiplier
            take_profit = entry - current_atr * settings.take_profit_atr_multiplier

        return TradingSignal(
            signal_id=signal_id(
                context.settings.trading.symbol,
                context.settings.trading.timeframe,
                current.time,
                side.value,
                self.name,
            ),
            symbol=context.settings.trading.symbol,
            timeframe=context.settings.trading.timeframe,
            side=side,
            candle_time=current.time,
            entry_reference_price=entry,
            stop_loss_price=quantize_price(stop_loss, digits),
            take_profit_price=quantize_price(take_profit, digits),
            atr=current_atr,
            reason="trend pullback confirmation",
            strategy_name=self.name,
            indicators={
                "ema_fast": current_fast,
                "ema_slow": current_slow,
                "rsi": current_rsi,
                "atr": current_atr,
            },
        )

    @staticmethod
    def required_history(settings: StrategySettings) -> int:
        return max(settings.slow_ema_period, settings.rsi_period + 1, settings.atr_period) + (
            settings.pullback_lookback_bars + 2
        )

    @staticmethod
    def _is_buy(
        current: Candle,
        fast: Decimal,
        slow: Decimal,
        previous_rsi: Decimal,
        current_rsi: Decimal,
        lookback_rsi: list[Decimal],
        settings: StrategySettings,
    ) -> bool:
        return (
            fast > slow
            and current.close > slow
            and min(lookback_rsi) <= settings.buy_pullback_rsi_level
            and previous_rsi <= settings.buy_confirmation_rsi_level
            and current_rsi > settings.buy_confirmation_rsi_level
            and current.close > current.open
        )

    @staticmethod
    def _is_sell(
        current: Candle,
        fast: Decimal,
        slow: Decimal,
        previous_rsi: Decimal,
        current_rsi: Decimal,
        lookback_rsi: list[Decimal],
        settings: StrategySettings,
    ) -> bool:
        return (
            fast < slow
            and current.close < slow
            and max(lookback_rsi) >= settings.sell_pullback_rsi_level
            and previous_rsi >= settings.sell_confirmation_rsi_level
            and current_rsi < settings.sell_confirmation_rsi_level
            and current.close < current.open
        )
