from __future__ import annotations

from decimal import Decimal

from trading_bot.common.decimal_utils import quantize_price
from trading_bot.common.identifiers import signal_id
from trading_bot.domain import Candle, Side, TradingSignal
from trading_bot.market_data import pip_size_for_symbol
from trading_bot.strategies.base import StrategyContext


class StrongCandleStrategy:
    name = "STRONG_CANDLE_V1"
    version = "1.0.0"
    description = (
        "Opens a trade after a closed candle whose body is inside the configured pip range "
        "and whose total upper+lower wick size is limited. Bullish candles create BUY "
        "signals and bearish candles create SELL signals."
    )
    parameters_schema = {
        "strong_candle_min_body_pips": "Minimum candle body size in pips",
        "strong_candle_max_body_pips": "Maximum candle body size in pips",
        "strong_candle_max_total_wick_pips": "Maximum allowed total shadow size in pips",
        "strong_candle_take_profit_pips": "Fixed take profit in pips",
        "strong_candle_stop_loss_pips": "Fixed stop loss in pips",
    }

    def generate_signal(
        self,
        candles: list[Candle],
        context: StrategyContext,
    ) -> TradingSignal | None:
        completed = [candle for candle in candles if candle.complete]
        if not completed:
            return None

        candle = completed[-1]
        settings = context.settings.strategy
        symbol_name = context.settings.trading.broker_symbol or context.settings.trading.symbol
        pip_size = pip_size_for_symbol(symbol_name)
        if candle.close == candle.open:
            return None
        if candle.high < max(candle.open, candle.close) or candle.low > min(
            candle.open,
            candle.close,
        ):
            return None

        body_pips = abs(candle.close - candle.open) / pip_size
        candle_range_pips = (candle.high - candle.low) / pip_size
        total_shadow_pips = candle_range_pips - body_pips
        if body_pips < settings.strong_candle_min_body_pips:
            return None
        if body_pips > settings.strong_candle_max_body_pips:
            return None
        if total_shadow_pips > settings.strong_candle_max_total_wick_pips:
            return None

        side = Side.BUY if candle.close > candle.open else Side.SELL
        entry = candle.close
        entry_digits = _price_digits(entry)
        take_profit_distance = settings.strong_candle_take_profit_pips * pip_size
        stop_loss_distance = settings.strong_candle_stop_loss_pips * pip_size
        if side is Side.BUY:
            stop_loss = entry - stop_loss_distance
            take_profit = entry + take_profit_distance
        else:
            stop_loss = entry + stop_loss_distance
            take_profit = entry - take_profit_distance

        return TradingSignal(
            signal_id=signal_id(
                context.settings.trading.symbol,
                context.settings.trading.timeframe,
                candle.time,
                side.value,
                self.name,
            ),
            symbol=context.settings.trading.symbol,
            timeframe=context.settings.trading.timeframe,
            side=side,
            candle_time=candle.time,
            entry_reference_price=entry,
            stop_loss_price=quantize_price(stop_loss, entry_digits),
            take_profit_price=quantize_price(take_profit, entry_digits),
            atr=stop_loss_distance,
            reason=(
                f"body {body_pips:.2f} pips, range {candle_range_pips:.2f}, "
                f"total shadow {total_shadow_pips:.2f}"
            ),
            strategy_name=self.name,
            indicators={
                "body_pips": body_pips,
                "candle_range_pips": candle_range_pips,
                "total_shadow_pips": total_shadow_pips,
                "total_wick_pips": total_shadow_pips,
            },
        )


def _price_digits(price: Decimal) -> int:
    return max(0, -price.as_tuple().exponent)
