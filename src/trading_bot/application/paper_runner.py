from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading_bot.config.models import Settings
from trading_bot.domain import AccountSnapshot
from trading_bot.execution import PaperGateway, TradingGateway
from trading_bot.risk import PositionSizer, RiskManager, RuntimeRiskState
from trading_bot.strategies import default_strategy_registry
from trading_bot.strategies.base import StrategyContext


@dataclass(frozen=True, slots=True)
class PaperTickResult:
    processed: bool
    reason: str


class PaperRunner:
    def __init__(self, settings: Settings, data_gateway: TradingGateway) -> None:
        self.settings = settings
        self.gateway = PaperGateway(data_gateway)
        self.registry = default_strategy_registry()
        self.position_sizer = PositionSizer()
        self.risk_manager = RiskManager(settings)

    def run_once(self, state: RuntimeRiskState) -> PaperTickResult:
        descriptor = self.registry.get(self.settings.strategy.strategy_id)
        symbol_name = self.settings.trading.broker_symbol
        candles = self.gateway.get_candles(symbol_name, self.settings.trading.timeframe, 260)
        completed = [candle for candle in candles if candle.complete]
        if not completed:
            return PaperTickResult(False, "no completed candles")
        latest = completed[-1]
        if state.last_processed_candle and latest.time <= state.last_processed_candle:
            return PaperTickResult(False, "candle already processed")
        signal = descriptor.strategy.generate_signal(completed, StrategyContext(self.settings))
        state.last_processed_candle = latest.time
        if signal is None:
            return PaperTickResult(True, "no signal")

        account = self.gateway.get_account()
        symbol = self.gateway.get_symbol(symbol_name)
        tick = self.gateway.get_latest_tick(symbol_name)
        spread_points = int((tick.ask - tick.bid) / symbol.point)
        positions = self.gateway.get_open_positions(symbol_name, self.settings.trading.magic_number)
        decision = self.risk_manager.validate_entry(
            signal=signal,
            account=account,
            symbol=symbol,
            positions=positions,
            state=state,
            spread_points=spread_points,
        )
        if not decision.allowed:
            return PaperTickResult(True, decision.reason)

        entry = tick.ask if signal.side.value == "BUY" else tick.bid
        sizing = self.position_sizer.size_by_risk(
            equity=account.equity,
            risk_percent=self.settings.risk.risk_per_trade_percent,
            side=signal.side,
            symbol=symbol,
            entry_price=entry,
            stop_loss_price=signal.stop_loss_price,
            leverage=account.leverage or self.settings.backtest.leverage,
        )
        if sizing.volume <= Decimal("0"):
            return PaperTickResult(True, sizing.reason)
        state.trades_today += 1
        return PaperTickResult(True, "paper signal accepted")

