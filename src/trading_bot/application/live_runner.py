from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

from trading_bot.common.exceptions import ExecutionError
from trading_bot.config.models import Settings
from trading_bot.execution.order_builder import OrderBuilder, market_order_levels
from trading_bot.execution import MT5Gateway
from trading_bot.risk import PositionSizer, RiskManager, RuntimeRiskState
from trading_bot.strategies import default_strategy_registry
from trading_bot.strategies.base import StrategyContext


@dataclass(frozen=True, slots=True)
class LiveStartupCheck:
    allowed: bool
    reason: str


class LiveRunner:
    def __init__(self, settings: Settings, gateway: MT5Gateway) -> None:
        self.settings = settings
        self.gateway = gateway
        self.registry = default_strategy_registry()
        self.risk_manager = RiskManager(settings)
        self.position_sizer = PositionSizer()
        self.order_builder = OrderBuilder(settings)

    def startup_check(self) -> LiveStartupCheck:
        if self.settings.application.mode != "LIVE":
            return LiveStartupCheck(False, "application mode is not LIVE")
        if os.getenv("LIVE_TRADING_ENABLED", "false").lower() != "true":
            return LiveStartupCheck(False, "LIVE_TRADING_ENABLED is not true")
        account = self.gateway.get_account()
        expected = os.getenv("MT5_EXPECTED_ACCOUNT", "").strip()
        if expected and str(account.login) != expected:
            return LiveStartupCheck(False, "connected account does not match expected account")
        if not account.trade_allowed:
            return LiveStartupCheck(False, "terminal trading is disabled")
        return LiveStartupCheck(True, "live startup checks passed")

    def run_once(self, state: RuntimeRiskState) -> str:
        check = self.startup_check()
        if not check.allowed:
            raise ExecutionError(check.reason)

        descriptor = self.registry.get(self.settings.strategy.strategy_id)
        symbol_name = self.settings.trading.broker_symbol
        candles = self.gateway.get_candles(symbol_name, self.settings.trading.timeframe, 260)
        completed = [candle for candle in candles if candle.complete]
        if not completed:
            return "No completed candles available."
        latest = completed[-1]
        if state.last_processed_candle and latest.time <= state.last_processed_candle:
            return f"No new closed candle. Last processed: {state.last_processed_candle.isoformat()}"

        signal = descriptor.strategy.generate_signal(completed, StrategyContext(self.settings))
        state.last_processed_candle = latest.time
        if signal is None:
            return f"Processed {latest.time.isoformat()}: no signal."

        account = self.gateway.get_account()
        symbol = self.gateway.get_symbol(symbol_name)
        tick = self.gateway.get_latest_tick(symbol_name)
        positions = self.gateway.get_open_positions(symbol_name, self.settings.trading.magic_number)
        spread_points = int((tick.ask - tick.bid) / symbol.point)
        decision = self.risk_manager.validate_entry(
            signal=signal,
            account=account,
            symbol=symbol,
            positions=positions,
            state=state,
            spread_points=spread_points,
        )
        if not decision.allowed:
            return f"Signal rejected: {decision.reason}"

        entry = tick.ask if signal.side.value == "BUY" else tick.bid
        stop_loss, _ = market_order_levels(signal, entry)
        sizing = self.position_sizer.size_by_risk(
            equity=account.equity,
            risk_percent=self.settings.risk.risk_per_trade_percent,
            side=signal.side,
            symbol=symbol,
            entry_price=entry,
            stop_loss_price=stop_loss,
            leverage=account.leverage or self.settings.backtest.leverage,
        )
        if sizing.volume <= Decimal("0"):
            return f"Signal rejected: {sizing.reason}"

        order = self.order_builder.build_market_order(signal, tick, symbol, sizing.volume)
        validation = self.gateway.validate_order(order)
        if not validation.success:
            return f"Order validation failed: {validation.reason}"

        result = self.gateway.send_market_order(order)
        if not result.success:
            return f"Order send failed: {result.reason} / code={result.result_code}"
        state.trades_today += 1
        return (
            f"Order executed: {order.side.value} {order.volume} {order.symbol} "
            f"at {result.execution_price} / ticket={result.order_ticket}"
        )
