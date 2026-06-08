from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_bot.common.time_utils import is_hour_inside_session
from trading_bot.config.models import Settings
from trading_bot.domain import AccountSnapshot, Position, Side, SymbolSnapshot, TradingSignal


@dataclass(frozen=True, slots=True)
class RiskDecision:
    allowed: bool
    reason: str = ""


@dataclass(slots=True)
class RuntimeRiskState:
    start_of_day_equity: Decimal
    equity_peak: Decimal
    trades_today: int = 0
    realized_daily_pnl: Decimal = Decimal("0")
    floating_daily_pnl: Decimal = Decimal("0")
    circuit_breaker_active: bool = False
    last_processed_candle: datetime | None = None


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_entry(
        self,
        signal: TradingSignal,
        account: AccountSnapshot,
        symbol: SymbolSnapshot,
        positions: list[Position],
        state: RuntimeRiskState,
        spread_points: int,
    ) -> RiskDecision:
        if signal.side is Side.BUY and not self.settings.execution.allow_buy:
            return RiskDecision(False, "buy entries are disabled")
        if signal.side is Side.SELL and not self.settings.execution.allow_sell:
            return RiskDecision(False, "sell entries are disabled")
        if state.circuit_breaker_active:
            return RiskDecision(False, "drawdown circuit breaker is active")
        if len(positions) >= self.settings.risk.maximum_open_positions:
            return RiskDecision(False, "maximum open positions reached")
        if state.trades_today >= self.settings.risk.maximum_trades_per_day:
            return RiskDecision(False, "maximum trades per day reached")
        if spread_points > self.settings.execution.maximum_spread_points:
            return RiskDecision(False, "spread is above configured maximum")
        if self.settings.session.enabled and not is_hour_inside_session(
            signal.candle_time,
            self.settings.session.start_hour,
            self.settings.session.end_hour,
        ):
            return RiskDecision(False, "trading session is closed")
        if account.equity <= 0:
            return RiskDecision(False, "account equity is invalid")
        if not account.trade_allowed and self.settings.application.mode == "LIVE":
            return RiskDecision(False, "terminal trading is not allowed")

        stop_points = int(abs(signal.entry_reference_price - signal.stop_loss_price) / symbol.point)
        if stop_points < self.settings.risk.minimum_stop_loss_points:
            return RiskDecision(False, "stop loss distance is below configured minimum")
        if stop_points > self.settings.risk.maximum_stop_loss_points:
            return RiskDecision(False, "stop loss distance is above configured maximum")

        daily_loss_limit = (
            state.start_of_day_equity * self.settings.risk.maximum_daily_loss_percent / Decimal("100")
        )
        current_daily_loss = -state.realized_daily_pnl
        if self.settings.risk.include_floating_loss_in_daily_limit:
            current_daily_loss += max(Decimal("0"), -state.floating_daily_pnl)
        if current_daily_loss >= daily_loss_limit:
            return RiskDecision(False, "daily loss limit reached")

        if state.equity_peak > 0:
            drawdown = (state.equity_peak - account.equity) / state.equity_peak * Decimal("100")
            if drawdown >= self.settings.risk.maximum_total_drawdown_percent:
                state.circuit_breaker_active = True
                return RiskDecision(False, "maximum total drawdown reached")

        return RiskDecision(True)

