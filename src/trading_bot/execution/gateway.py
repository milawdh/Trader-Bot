from __future__ import annotations

from decimal import Decimal
from typing import Protocol

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


class TradingGateway(Protocol):
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def get_account(self) -> AccountSnapshot:
        ...

    def get_symbol(self, symbol: str) -> SymbolSnapshot:
        ...

    def get_latest_tick(self, symbol: str) -> Tick:
        ...

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        ...

    def get_open_positions(self, symbol: str, magic_number: int) -> list[Position]:
        ...

    def calculate_profit(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        open_price: Decimal,
        close_price: Decimal,
    ) -> Decimal:
        ...

    def calculate_margin(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        price: Decimal,
    ) -> Decimal:
        ...

    def validate_order(self, order: OrderRequest) -> OrderValidationResult:
        ...

    def send_market_order(self, order: OrderRequest) -> OrderResult:
        ...

