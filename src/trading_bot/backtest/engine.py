from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.backtest.metrics import calculate_metrics, calculate_period_returns, drawdown_curve
from trading_bot.config.models import Settings
from trading_bot.domain import (
    AccountSnapshot,
    BacktestResult,
    Candle,
    Position,
    Side,
    SymbolSnapshot,
    Trade,
    TradingSignal,
)
from trading_bot.market_data import default_symbol_snapshot
from trading_bot.risk import PositionSizer, RiskManager, RuntimeRiskState
from trading_bot.strategies.base import StrategyContext, TradingStrategy


@dataclass(slots=True)
class _OpenTrade:
    signal: TradingSignal
    side: Side
    entry_time: datetime
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    volume: Decimal
    margin_required: Decimal


class BacktestEngine:
    def __init__(
        self,
        settings: Settings,
        strategy: TradingStrategy,
        symbol: SymbolSnapshot | None = None,
    ) -> None:
        self.settings = settings
        self.strategy = strategy
        self.symbol = symbol or default_symbol_snapshot(
            settings.trading.broker_symbol or settings.trading.symbol
        )
        self.position_sizer = PositionSizer()

    def run(self, candles: list[Candle], run_stress: bool = True) -> BacktestResult:
        clean_candles = sorted((c for c in candles if c.complete), key=lambda candle: candle.time)
        run_id = uuid.uuid4().hex[:12]
        started_at = datetime.now(UTC)
        result = self._run_single(clean_candles, run_id=run_id, scenario_name="Base Scenario")
        if run_stress:
            result.stress_results.extend(self._run_stress(clean_candles))
        completed_at = datetime.now(UTC)
        return BacktestResult(
            run_id=run_id,
            strategy_name=self.strategy.name,
            symbol=self.settings.trading.symbol,
            timeframe=self.settings.trading.timeframe,
            started_at=started_at,
            completed_at=completed_at,
            metrics=result.metrics,
            trades=result.trades,
            equity_curve=result.equity_curve,
            drawdown_curve=result.drawdown_curve,
            monthly_returns=result.monthly_returns,
            daily_returns=result.daily_returns,
            candle_markers=result.candle_markers,
            stress_results=result.stress_results,
        )

    def _run_single(
        self,
        candles: list[Candle],
        run_id: str,
        scenario_name: str,
    ) -> BacktestResult:
        balance = self.settings.backtest.initial_balance
        equity_curve: list[tuple[datetime, Decimal]] = []
        trades: list[Trade] = []
        markers: list[dict[str, object]] = []
        pending_signal: TradingSignal | None = None
        open_trade: _OpenTrade | None = None
        risk_state = RuntimeRiskState(start_of_day_equity=balance, equity_peak=balance)
        risk_manager = RiskManager(self.settings)
        current_risk_day = None

        for index, candle in enumerate(candles):
            candle_day = candle.time.date()
            if current_risk_day != candle_day:
                current_risk_day = candle_day
                risk_state.start_of_day_equity = balance
                risk_state.trades_today = 0
                risk_state.realized_daily_pnl = Decimal("0")
                risk_state.floating_daily_pnl = Decimal("0")

            if pending_signal is not None and open_trade is None:
                open_trade = self._open_from_signal(
                    pending_signal,
                    candle,
                    balance,
                )
                if open_trade is not None:
                    markers.append(
                        {
                            "time": candle.time,
                            "side": open_trade.side.value,
                            "price": open_trade.entry_price,
                            "signal_id": open_trade.signal.signal_id,
                        }
                    )
                pending_signal = None

            if open_trade is not None:
                closed = self._maybe_close(open_trade, candle)
                if closed is not None:
                    trade = self._to_trade(open_trade, closed[0], closed[1], closed[2])
                    trades.append(trade)
                    balance += trade.net_pnl
                    risk_state.realized_daily_pnl += trade.net_pnl
                    risk_state.trades_today += 1
                    open_trade = None

            floating = self._floating_pnl(open_trade, candle.close) if open_trade else Decimal("0")
            risk_state.floating_daily_pnl = floating
            equity = balance + floating
            risk_state.equity_peak = max(risk_state.equity_peak, equity)
            equity_curve.append((candle.time, equity))

            if index >= len(candles) - 1 or open_trade is not None or pending_signal is not None:
                continue

            history = candles[: index + 1]
            signal = self.strategy.generate_signal(history, StrategyContext(self.settings))
            if signal is None:
                continue
            spread_points = candle.spread or self.settings.backtest.default_spread_points
            account = AccountSnapshot(
                login=None,
                server="BACKTEST",
                currency=self.settings.backtest.account_currency,
                balance=balance,
                equity=equity,
                margin=Decimal("0"),
                free_margin=equity,
                leverage=self.settings.backtest.leverage,
                trade_allowed=True,
            )
            decision = risk_manager.validate_entry(
                signal=signal,
                account=account,
                symbol=self.symbol,
                positions=[],
                state=risk_state,
                spread_points=spread_points,
            )
            if decision.allowed:
                pending_signal = signal

        if open_trade is not None and candles:
            last = candles[-1]
            trade = self._to_trade(open_trade, last.time, last.close, "END_OF_TEST")
            trades.append(trade)
            balance += trade.net_pnl
            equity_curve.append((last.time, balance))

        metrics = calculate_metrics(trades, equity_curve, self.settings.backtest.initial_balance)
        metrics["scenario"] = scenario_name
        dd_curve = drawdown_curve(equity_curve)
        return BacktestResult(
            run_id=run_id,
            strategy_name=self.strategy.name,
            symbol=self.settings.trading.symbol,
            timeframe=self.settings.trading.timeframe,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=dd_curve,
            monthly_returns=calculate_period_returns(equity_curve, "%Y-%m"),
            daily_returns=calculate_period_returns(equity_curve, "%Y-%m-%d"),
            candle_markers=markers,
        )

    def _run_stress(self, candles: list[Candle]) -> list[dict[str, object]]:
        scenarios = [
            ("Higher Spread", Decimal("1.5"), self.settings.backtest.slippage_points, Decimal("1")),
            ("Higher Slippage", Decimal("1"), 5, Decimal("1")),
            ("Combined Adverse Costs", Decimal("1.5"), 5, Decimal("1.25")),
        ]
        original_spread = self.settings.backtest.default_spread_points
        original_slippage = self.settings.backtest.slippage_points
        original_commission = self.settings.backtest.commission_per_lot_round_turn
        results: list[dict[str, object]] = []
        for name, spread_multiplier, slippage, commission_multiplier in scenarios:
            self.settings.backtest.default_spread_points = int(
                Decimal(original_spread) * spread_multiplier
            )
            self.settings.backtest.slippage_points = slippage
            self.settings.backtest.commission_per_lot_round_turn = (
                original_commission * commission_multiplier
            )
            result = self._run_single(candles, run_id=f"stress-{name}", scenario_name=name)
            results.append(
                {
                    "scenario": name,
                    "net_profit": result.metrics["net_profit"],
                    "profit_factor": result.metrics["profit_factor"],
                    "maximum_drawdown_percent": result.metrics["maximum_drawdown_percent"],
                    "total_trades": result.metrics["total_trades"],
                }
            )
        self.settings.backtest.default_spread_points = original_spread
        self.settings.backtest.slippage_points = original_slippage
        self.settings.backtest.commission_per_lot_round_turn = original_commission
        return results

    def _open_from_signal(
        self,
        signal: TradingSignal,
        candle: Candle,
        equity: Decimal,
    ) -> _OpenTrade | None:
        entry = candle.open
        stop_distance = abs(signal.entry_reference_price - signal.stop_loss_price)
        take_profit_distance = abs(signal.take_profit_price - signal.entry_reference_price)
        if signal.side is Side.BUY:
            stop_loss = entry - stop_distance
            take_profit = entry + take_profit_distance
        else:
            stop_loss = entry + stop_distance
            take_profit = entry - take_profit_distance
        sizing = self.position_sizer.size_by_risk(
            equity=equity,
            risk_percent=self.settings.risk.risk_per_trade_percent,
            side=signal.side,
            symbol=self.symbol,
            entry_price=entry,
            stop_loss_price=stop_loss,
            leverage=self.settings.backtest.leverage,
        )
        if sizing.volume <= 0 or sizing.margin_required > equity:
            return None
        return _OpenTrade(
            signal=signal,
            side=signal.side,
            entry_time=candle.time,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=sizing.volume,
            margin_required=sizing.margin_required,
        )

    def _maybe_close(
        self,
        open_trade: _OpenTrade,
        candle: Candle,
    ) -> tuple[datetime, Decimal, str] | None:
        if open_trade.side is Side.BUY:
            stop_hit = candle.low <= open_trade.stop_loss
            target_hit = candle.high >= open_trade.take_profit
            if stop_hit and target_hit:
                return candle.time, open_trade.stop_loss, "STOP_LOSS_AND_TAKE_PROFIT_STOP_FIRST"
            if stop_hit:
                return candle.time, open_trade.stop_loss, "STOP_LOSS"
            if target_hit:
                return candle.time, open_trade.take_profit, "TAKE_PROFIT"
        else:
            stop_hit = candle.high >= open_trade.stop_loss
            target_hit = candle.low <= open_trade.take_profit
            if stop_hit and target_hit:
                return candle.time, open_trade.stop_loss, "STOP_LOSS_AND_TAKE_PROFIT_STOP_FIRST"
            if stop_hit:
                return candle.time, open_trade.stop_loss, "STOP_LOSS"
            if target_hit:
                return candle.time, open_trade.take_profit, "TAKE_PROFIT"
        return None

    def _to_trade(
        self,
        open_trade: _OpenTrade,
        exit_time: datetime,
        exit_price: Decimal,
        exit_reason: str,
    ) -> Trade:
        gross = self._gross_pnl(open_trade.side, open_trade.entry_price, exit_price, open_trade.volume)
        spread_points = self.settings.backtest.default_spread_points
        spread_cost = Decimal(spread_points) * self.symbol.point * self.symbol.contract_size * open_trade.volume
        slippage_cost = (
            Decimal(self.settings.backtest.slippage_points)
            * self.symbol.point
            * self.symbol.contract_size
            * open_trade.volume
        )
        commission = self.settings.backtest.commission_per_lot_round_turn * open_trade.volume
        net = gross - spread_cost - slippage_cost - commission
        return Trade(
            trade_id=uuid.uuid4().hex[:12],
            signal_id=open_trade.signal.signal_id,
            symbol=self.settings.trading.symbol,
            side=open_trade.side,
            candle_time=open_trade.signal.candle_time,
            entry_time=open_trade.entry_time,
            entry_price=open_trade.entry_price,
            exit_time=exit_time,
            exit_price=exit_price,
            stop_loss=open_trade.stop_loss,
            take_profit=open_trade.take_profit,
            volume=open_trade.volume,
            gross_pnl=gross,
            commission=commission,
            spread_cost=spread_cost,
            slippage_cost=slippage_cost,
            net_pnl=net,
            exit_reason=exit_reason,
            margin_required=open_trade.margin_required,
            signal_reason=open_trade.signal.reason,
            signal_indicators=dict(open_trade.signal.indicators),
        )

    def _floating_pnl(self, open_trade: _OpenTrade, current_price: Decimal) -> Decimal:
        return self._gross_pnl(open_trade.side, open_trade.entry_price, current_price, open_trade.volume)

    def _gross_pnl(
        self,
        side: Side,
        entry_price: Decimal,
        exit_price: Decimal,
        volume: Decimal,
    ) -> Decimal:
        direction = Decimal("1") if side is Side.BUY else Decimal("-1")
        return (exit_price - entry_price) * direction * self.symbol.contract_size * volume
