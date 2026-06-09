from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_bot.domain import BacktestResult, Trade


class TradingBotDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    run_id TEXT PRIMARY KEY,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    equity_json TEXT NOT NULL,
                    drawdown_json TEXT NOT NULL,
                    monthly_returns_json TEXT NOT NULL,
                    daily_returns_json TEXT NOT NULL,
                    stress_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    side TEXT NOT NULL,
                    candle_time TEXT NOT NULL,
                    entry_reference_price TEXT NOT NULL,
                    stop_loss TEXT NOT NULL,
                    take_profit TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rejection_reason TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS orders (
                    client_order_id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    mt5_order_ticket TEXT,
                    mt5_deal_ticket TEXT,
                    request_json TEXT NOT NULL,
                    response_json TEXT,
                    result_code TEXT,
                    execution_price TEXT,
                    volume TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    candle_time TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    entry_price TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    exit_price TEXT NOT NULL,
                    stop_loss TEXT NOT NULL,
                    take_profit TEXT NOT NULL,
                    volume TEXT NOT NULL,
                    gross_pnl TEXT NOT NULL,
                    commission TEXT NOT NULL,
                    spread_cost TEXT NOT NULL,
                    slippage_cost TEXT NOT NULL,
                    net_pnl TEXT NOT NULL,
                    exit_reason TEXT NOT NULL,
                    margin_required TEXT NOT NULL,
                    signal_reason TEXT NOT NULL DEFAULT '',
                    signal_indicators_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            self._ensure_column(connection, "trades", "signal_reason", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(
                connection,
                "trades",
                "signal_indicators_json",
                "TEXT NOT NULL DEFAULT '{}'",
            )

    def save_backtest_result(self, result: BacktestResult) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO backtest_runs (
                    run_id, strategy_name, symbol, timeframe, started_at, completed_at,
                    metrics_json, equity_json, drawdown_json, monthly_returns_json,
                    daily_returns_json, stress_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    result.strategy_name,
                    result.symbol,
                    result.timeframe,
                    result.started_at.isoformat(),
                    result.completed_at.isoformat(),
                    _json(result.metrics),
                    _json(result.equity_curve),
                    _json(result.drawdown_curve),
                    _json(result.monthly_returns),
                    _json(result.daily_returns),
                    _json(result.stress_results),
                ),
            )
            connection.execute("DELETE FROM trades WHERE run_id = ?", (result.run_id,))
            connection.executemany(
                """
                INSERT OR REPLACE INTO trades (
                    trade_id, run_id, signal_id, symbol, side, candle_time, entry_time,
                    entry_price, exit_time, exit_price, stop_loss, take_profit, volume,
                    gross_pnl, commission, spread_cost, slippage_cost, net_pnl,
                    exit_reason, margin_required, signal_reason, signal_indicators_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._trade_row(result.run_id, trade) for trade in result.trades],
            )

    def list_backtest_runs(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, strategy_name, symbol, timeframe, started_at, completed_at, metrics_json
                FROM backtest_runs
                ORDER BY started_at DESC
                LIMIT 100
                """
            ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "strategy_name": row["strategy_name"],
                "symbol": row["symbol"],
                "timeframe": row["timeframe"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "metrics": json.loads(row["metrics_json"]),
            }
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _trade_row(run_id: str, trade: Trade) -> tuple[str, ...]:
        return (
            trade.trade_id,
            run_id,
            trade.signal_id,
            trade.symbol,
            trade.side.value,
            trade.candle_time.isoformat(),
            trade.entry_time.isoformat(),
            str(trade.entry_price),
            trade.exit_time.isoformat(),
            str(trade.exit_price),
            str(trade.stop_loss),
            str(trade.take_profit),
            str(trade.volume),
            str(trade.gross_pnl),
            str(trade.commission),
            str(trade.spread_cost),
            str(trade.slippage_cost),
            str(trade.net_pnl),
            trade.exit_reason,
            str(trade.margin_required),
            trade.signal_reason,
            _json(trade.signal_indicators),
        )


def _json(value: Any) -> str:
    return json.dumps(value, default=_json_default, ensure_ascii=False)


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
