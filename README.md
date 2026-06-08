# EURUSD Trading Bot

Desktop MVP for a modular EURUSD MetaTrader 5 trading bot. The app defaults to `BACKTEST`;
live trading is disabled unless explicitly configured.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Run

```powershell
python main.py
```

If you only want a quick core check without the UI dependencies:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
python main.py backtest
```

## Current MVP

- PySide6 desktop shell with Settings, Backtest, Paper, Live, and Report Center tabs.
- Reports are shown inside the app: summary cards, equity, drawdown, trade table,
  and stress-test table. Customer-facing file exports are intentionally not exposed.
- Settings includes language selection and a Windows file picker for the MetaTrader terminal path.
- Backtest, Paper, and Live have separate strategy/symbol/timeframe/risk/spread controls.
- Strategy registry supports future strategy files.
- Baseline `TREND_PULLBACK_V1` implements EMA 50/200, RSI pullback/confirmation, ATR SL/TP.
- `STRONG_CANDLE_V1` opens on closed candles with configurable minimum/maximum body size
  and maximum total upper+lower wick. Direction follows candle color, and body / wick /
  TP / SL are configurable in Backtest, Paper, and Live tabs.
- Backtest engine uses next-candle entry, spread, commission, slippage, margin/leverage,
  and conservative same-candle SL/TP handling.
- SQLite stores internal app state and backtest runs. No customer-facing report files are needed.
- MT5 integration is isolated in `execution/mt5_gateway.py`.

## Paper Mode

Paper mode is a safe live-market simulation mode. It reads real candles and ticks from MetaTrader,
generates signals with the selected strategy, and simulates entries/exits without calling
`order_send`. No real order is sent in Paper mode.

## Live Mode

Live mode has its own parameters and Start/Stop controls. It connects to MetaTrader, checks
`LIVE_TRADING_ENABLED=true`, verifies the expected account when configured, processes only closed
candles, validates risk/spread/margin/order_check, and then sends the market order. Use a demo
account before enabling it.

## Safety

- Live mode is never the default.
- Credentials must stay in `.env` or UI memory only; passwords are not logged or persisted.
- This software does not guarantee profit. Historical results can fail in live markets.
