from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from math import sqrt
from statistics import mean, pstdev
from typing import Any

from trading_bot.domain import Side, Trade


def calculate_metrics(
    trades: list[Trade],
    equity_curve: list[tuple[datetime, Decimal]],
    initial_balance: Decimal,
) -> dict[str, Any]:
    final_balance = equity_curve[-1][1] if equity_curve else initial_balance
    net_profit = final_balance - initial_balance
    gross_profit = sum((trade.net_pnl for trade in trades if trade.net_pnl > 0), Decimal("0"))
    gross_loss = sum((trade.net_pnl for trade in trades if trade.net_pnl < 0), Decimal("0"))
    winners = [trade for trade in trades if trade.net_pnl > 0]
    losers = [trade for trade in trades if trade.net_pnl < 0]
    total_trades = len(trades)
    max_drawdown_amount, max_drawdown_pct = _max_drawdown(equity_curve)
    daily_returns = calculate_period_returns(equity_curve, "%Y-%m-%d")
    monthly_returns = calculate_period_returns(equity_curve, "%Y-%m")
    daily_return_values = [float(value) / 100 for _, value in daily_returns]
    sharpe = _sharpe(daily_return_values)
    calmar = _calmar(net_profit, initial_balance, max_drawdown_pct)

    return {
        "initial_balance": initial_balance,
        "final_balance": final_balance,
        "net_profit": net_profit,
        "total_return_percent": _pct(net_profit, initial_balance),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": _profit_factor(gross_profit, gross_loss),
        "maximum_drawdown_amount": max_drawdown_amount,
        "maximum_drawdown_percent": max_drawdown_pct,
        "win_rate_percent": _pct(Decimal(len(winners)), Decimal(total_trades))
        if total_trades
        else None,
        "total_trades": total_trades,
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "average_winning_trade": _avg([trade.net_pnl for trade in winners]),
        "average_losing_trade": _avg([trade.net_pnl for trade in losers]),
        "average_trade_expectancy": _avg([trade.net_pnl for trade in trades]),
        "largest_winning_trade": max((trade.net_pnl for trade in winners), default=None),
        "largest_losing_trade": min((trade.net_pnl for trade in losers), default=None),
        "average_risk_reward_achieved": _average_risk_reward(trades),
        "maximum_consecutive_wins": _max_streak(trades, winning=True),
        "maximum_consecutive_losses": _max_streak(trades, winning=False),
        "sharpe_ratio": sharpe,
        "calmar_ratio": calmar,
        "exposure_percent": _exposure_percent(trades, equity_curve),
        "average_trade_duration_hours": _average_duration_hours(trades),
        "long_net_profit": sum((t.net_pnl for t in trades if t.side is Side.BUY), Decimal("0")),
        "short_net_profit": sum((t.net_pnl for t in trades if t.side is Side.SELL), Decimal("0")),
        "total_spread_cost": sum((trade.spread_cost for trade in trades), Decimal("0")),
        "total_commission": sum((trade.commission for trade in trades), Decimal("0")),
        "total_slippage_cost": sum((trade.slippage_cost for trade in trades), Decimal("0")),
    }


def calculate_period_returns(
    equity_curve: list[tuple[datetime, Decimal]],
    period_format: str,
) -> list[tuple[str, Decimal]]:
    if not equity_curve:
        return []
    buckets: dict[str, list[Decimal]] = defaultdict(list)
    for timestamp, equity in equity_curve:
        buckets[timestamp.strftime(period_format)].append(equity)
    result: list[tuple[str, Decimal]] = []
    for period in sorted(buckets):
        values = buckets[period]
        start = values[0]
        end = values[-1]
        result.append((period, _pct(end - start, start) or Decimal("0")))
    return result


def drawdown_curve(equity_curve: list[tuple[datetime, Decimal]]) -> list[tuple[datetime, Decimal]]:
    result: list[tuple[datetime, Decimal]] = []
    peak: Decimal | None = None
    for timestamp, equity in equity_curve:
        peak = equity if peak is None else max(peak, equity)
        pct = Decimal("0") if peak == 0 else (peak - equity) / peak * Decimal("100")
        result.append((timestamp, pct))
    return result


def _max_drawdown(equity_curve: list[tuple[datetime, Decimal]]) -> tuple[Decimal, Decimal]:
    peak: Decimal | None = None
    max_amount = Decimal("0")
    max_pct = Decimal("0")
    for _, equity in equity_curve:
        peak = equity if peak is None else max(peak, equity)
        amount = peak - equity
        pct = Decimal("0") if peak == 0 else amount / peak * Decimal("100")
        max_amount = max(max_amount, amount)
        max_pct = max(max_pct, pct)
    return max_amount, max_pct


def _pct(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator * Decimal("100")


def _profit_factor(gross_profit: Decimal, gross_loss: Decimal) -> Decimal | None:
    if gross_loss == 0:
        return None if gross_profit == 0 else Decimal("999")
    return gross_profit / abs(gross_loss)


def _avg(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _max_streak(trades: list[Trade], winning: bool) -> int:
    best = current = 0
    for trade in trades:
        is_match = trade.net_pnl > 0 if winning else trade.net_pnl < 0
        if is_match:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _average_risk_reward(trades: list[Trade]) -> Decimal | None:
    ratios: list[Decimal] = []
    for trade in trades:
        risk = abs(trade.entry_price - trade.stop_loss)
        reward = abs(trade.take_profit - trade.entry_price)
        if risk > 0:
            ratios.append(reward / risk)
    return _avg(ratios)


def _average_duration_hours(trades: list[Trade]) -> Decimal | None:
    if not trades:
        return None
    hours = [
        Decimal(str((trade.exit_time - trade.entry_time).total_seconds() / 3600))
        for trade in trades
    ]
    return _avg(hours)


def _exposure_percent(
    trades: list[Trade],
    equity_curve: list[tuple[datetime, Decimal]],
) -> Decimal | None:
    if not trades or len(equity_curve) < 2:
        return None
    total_seconds = Decimal(str((equity_curve[-1][0] - equity_curve[0][0]).total_seconds()))
    if total_seconds <= 0:
        return None
    exposed = sum(
        (Decimal(str((trade.exit_time - trade.entry_time).total_seconds())) for trade in trades),
        Decimal("0"),
    )
    return exposed / total_seconds * Decimal("100")


def _sharpe(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    deviation = pstdev(values)
    if deviation == 0:
        return None
    return sqrt(252) * mean(values) / deviation


def _calmar(net_profit: Decimal, initial_balance: Decimal, max_drawdown_pct: Decimal) -> Decimal | None:
    total_return = _pct(net_profit, initial_balance)
    if total_return is None or max_drawdown_pct == 0:
        return None
    return total_return / max_drawdown_pct

