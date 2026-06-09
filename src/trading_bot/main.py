from __future__ import annotations

import argparse
import sys

from trading_bot.application.backtest_runner import BacktestRunner
from trading_bot.config.loader import load_settings
from trading_bot.market_data import generate_demo_candles_for_range, load_candles_from_csv
from trading_bot.ui.app import launch_ui


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eurusd-bot")
    parser.add_argument("--config", default="configs/default.yaml")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("ui")
    backtest_parser = subparsers.add_parser("backtest")
    backtest_parser.add_argument("--csv", default="")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    if args.command in {None, "ui"}:
        return launch_ui(settings)
    if args.command == "backtest":
        candles = (
            load_candles_from_csv(args.csv)
            if args.csv
            else generate_demo_candles_for_range(
                _date_start(settings.backtest.start_date),
                _date_start(settings.backtest.end_date),
                settings.trading.timeframe,
                symbol=settings.trading.broker_symbol or settings.trading.symbol,
            )
        )
        result = BacktestRunner(settings).run(candles, persist=True)
        print(f"run_id={result.run_id}")
        print(f"trades={len(result.trades)}")
        print(f"net_profit={result.metrics.get('net_profit')}")
        print(f"profit_factor={result.metrics.get('profit_factor')}")
        return 0
    return 2


def _date_start(value: str):
    from datetime import UTC, datetime

    parsed = datetime.fromisoformat(str(value))
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
