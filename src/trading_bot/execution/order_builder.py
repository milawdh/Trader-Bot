from __future__ import annotations

import uuid
from decimal import Decimal

from trading_bot.common.decimal_utils import quantize_price
from trading_bot.config.models import Settings
from trading_bot.domain import OrderRequest, Side, SymbolSnapshot, Tick, TradingSignal


class OrderBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_market_order(
        self,
        signal: TradingSignal,
        tick: Tick,
        symbol: SymbolSnapshot,
        volume: Decimal,
    ) -> OrderRequest:
        entry = tick.ask if signal.side is Side.BUY else tick.bid
        stop_distance = abs(signal.entry_reference_price - signal.stop_loss_price)
        take_profit_distance = abs(signal.take_profit_price - signal.entry_reference_price)
        if signal.side is Side.BUY:
            stop_loss = entry - stop_distance
            take_profit = entry + take_profit_distance
        else:
            stop_loss = entry + stop_distance
            take_profit = entry - take_profit_distance
        return OrderRequest(
            client_order_id=uuid.uuid4().hex,
            signal_id=signal.signal_id,
            symbol=symbol.name,
            side=signal.side,
            volume=volume,
            entry_price=quantize_price(entry, symbol.digits),
            stop_loss=quantize_price(stop_loss, symbol.digits),
            take_profit=quantize_price(take_profit, symbol.digits),
            deviation_points=self.settings.execution.maximum_deviation_points,
            magic_number=self.settings.trading.magic_number,
            comment=self.settings.trading.comment,
        )
