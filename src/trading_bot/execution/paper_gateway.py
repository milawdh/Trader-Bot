from __future__ import annotations

from decimal import Decimal

from trading_bot.domain import (
    AccountSnapshot,
    Candle,
    OrderRequest,
    OrderResult,
    OrderValidationResult,
    Position,
    SymbolSnapshot,
    Tick,
)
from trading_bot.execution.gateway import TradingGateway


class PaperGateway:
    def __init__(self, data_gateway: TradingGateway) -> None:
        self.data_gateway = data_gateway

    def connect(self) -> None:
        self.data_gateway.connect()

    def disconnect(self) -> None:
        self.data_gateway.disconnect()

    def get_account(self) -> AccountSnapshot:
        return self.data_gateway.get_account()

    def get_symbol(self, symbol: str) -> SymbolSnapshot:
        return self.data_gateway.get_symbol(symbol)

    def get_latest_tick(self, symbol: str) -> Tick:
        return self.data_gateway.get_latest_tick(symbol)

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        return self.data_gateway.get_candles(symbol, timeframe, count)

    def get_open_positions(self, symbol: str, magic_number: int) -> list[Position]:
        del symbol, magic_number
        return []

    def calculate_profit(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        open_price: Decimal,
        close_price: Decimal,
    ) -> Decimal:
        return self.data_gateway.calculate_profit(side, symbol, volume, open_price, close_price)

    def calculate_margin(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        price: Decimal,
    ) -> Decimal:
        return self.data_gateway.calculate_margin(side, symbol, volume, price)

    def validate_order(self, order: OrderRequest) -> OrderValidationResult:
        del order
        return OrderValidationResult(True, "paper order accepted")

    def send_market_order(self, order: OrderRequest) -> OrderResult:
        return OrderResult(
            success=True,
            client_order_id=order.client_order_id,
            signal_id=order.signal_id,
            execution_price=order.entry_price,
            volume=order.volume,
            reason="paper mode: no real order was sent",
        )

