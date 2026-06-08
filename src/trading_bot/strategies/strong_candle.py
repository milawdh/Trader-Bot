from __future__ import annotations

from decimal import Decimal

from trading_bot.common.decimal_utils import quantize_price
from trading_bot.common.identifiers import signal_id
from trading_bot.domain import Candle, Side, TradingSignal
from trading_bot.strategies.base import StrategyContext


PIP_SIZE = Decimal("0.0001")


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
        "strong_candle_max_total_wick_pips": "Maximum allowed upper+lower wick sum in pips",
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
        if candle.close == candle.open:
            return None

        body_pips = abs(candle.close - candle.open) / PIP_SIZE
        upper_wick_pips = (candle.high - max(candle.open, candle.close)) / PIP_SIZE
        lower_wick_pips = (min(candle.open, candle.close) - candle.low) / PIP_SIZE
        total_wick_pips = upper_wick_pips + lower_wick_pips
        if body_pips < settings.strong_candle_min_body_pips:
            return None
        if body_pips > settings.strong_candle_max_body_pips:
            return None
        if total_wick_pips > settings.strong_candle_max_total_wick_pips:
            return None

        side = Side.BUY if candle.close > candle.open else Side.SELL
        entry = candle.close
        take_profit_distance = settings.strong_candle_take_profit_pips * PIP_SIZE
        stop_loss_distance = settings.strong_candle_stop_loss_pips * PIP_SIZE
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
            stop_loss_price=quantize_price(stop_loss, 5),
            take_profit_price=quantize_price(take_profit, 5),
            atr=stop_loss_distance,
            reason=(
                f"body {body_pips:.2f} pips, upper wick {upper_wick_pips:.2f}, "
                f"lower wick {lower_wick_pips:.2f}, total wick {total_wick_pips:.2f}"
            ),
            strategy_name=self.name,
            indicators={
                "body_pips": body_pips,
                "upper_wick_pips": upper_wick_pips,
                "lower_wick_pips": lower_wick_pips,
                "total_wick_pips": total_wick_pips,
            },
        )
