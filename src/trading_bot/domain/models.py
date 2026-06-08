from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Candle:
    time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    tick_volume: int = 0
    spread: int = 0
    real_volume: int = 0
    complete: bool = True


@dataclass(frozen=True, slots=True)
class TradingSignal:
    signal_id: str
    symbol: str
    timeframe: str
    side: Side
    candle_time: datetime
    entry_reference_price: Decimal
    stop_loss_price: Decimal
    take_profit_price: Decimal
    atr: Decimal
    reason: str
    strategy_name: str
    indicators: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    login: int | None
    server: str
    currency: str
    balance: Decimal
    equity: Decimal
    margin: Decimal = Decimal("0")
    free_margin: Decimal = Decimal("0")
    leverage: int = 100
    trade_allowed: bool = False


@dataclass(frozen=True, slots=True)
class SymbolSnapshot:
    name: str
    digits: int
    point: Decimal
    volume_min: Decimal
    volume_max: Decimal
    volume_step: Decimal
    contract_size: Decimal = Decimal("100000")
    trade_stops_level: int = 0
    trade_freeze_level: int = 0
    filling_modes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: str
    time: datetime
    bid: Decimal
    ask: Decimal

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")


@dataclass(frozen=True, slots=True)
class Position:
    position_id: str
    symbol: str
    side: Side
    volume: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    open_time: datetime
    magic_number: int
    comment: str
    unrealized_pnl: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class OrderRequest:
    client_order_id: str
    signal_id: str
    symbol: str
    side: Side
    volume: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    deviation_points: int
    magic_number: int
    comment: str


@dataclass(frozen=True, slots=True)
class OrderValidationResult:
    success: bool
    reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderResult:
    success: bool
    client_order_id: str
    signal_id: str
    order_ticket: int | None = None
    deal_ticket: int | None = None
    result_code: int | None = None
    execution_price: Decimal | None = None
    volume: Decimal | None = None
    reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Trade:
    trade_id: str
    signal_id: str
    symbol: str
    side: Side
    candle_time: datetime
    entry_time: datetime
    entry_price: Decimal
    exit_time: datetime
    exit_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    volume: Decimal
    gross_pnl: Decimal
    commission: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    net_pnl: Decimal
    exit_reason: str
    margin_required: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    run_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    started_at: datetime
    completed_at: datetime
    metrics: dict[str, Any]
    trades: list[Trade]
    equity_curve: list[tuple[datetime, Decimal]]
    drawdown_curve: list[tuple[datetime, Decimal]]
    monthly_returns: list[tuple[str, Decimal]]
    daily_returns: list[tuple[str, Decimal]]
    candle_markers: list[dict[str, Any]]
    stress_results: list[dict[str, Any]] = field(default_factory=list)

