from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class ApplicationSettings:
    mode: str = "BACKTEST"
    log_level: str = "INFO"


@dataclass(slots=True)
class TradingSettings:
    symbol: str = "EURUSD"
    broker_symbol: str = "EURUSD"
    timeframe: str = "H1"
    magic_number: int = 26060801
    comment: str = "EURUSD_TREND_PULLBACK_V1"


@dataclass(slots=True)
class StrategySettings:
    strategy_id: str = "trend_pullback_v1"
    fast_ema_period: int = 50
    slow_ema_period: int = 200
    rsi_period: int = 14
    atr_period: int = 14
    buy_pullback_rsi_level: Decimal = Decimal("45")
    buy_confirmation_rsi_level: Decimal = Decimal("50")
    sell_pullback_rsi_level: Decimal = Decimal("55")
    sell_confirmation_rsi_level: Decimal = Decimal("50")
    stop_loss_atr_multiplier: Decimal = Decimal("1.5")
    take_profit_atr_multiplier: Decimal = Decimal("2.25")
    pullback_lookback_bars: int = 5
    strong_candle_min_body_pips: Decimal = Decimal("50")
    strong_candle_max_body_pips: Decimal = Decimal("200")
    strong_candle_max_total_wick_pips: Decimal = Decimal("10")
    strong_candle_take_profit_pips: Decimal = Decimal("50")
    strong_candle_stop_loss_pips: Decimal = Decimal("20")


@dataclass(slots=True)
class RiskSettings:
    risk_per_trade_percent: Decimal = Decimal("0.5")
    maximum_daily_loss_percent: Decimal = Decimal("2.0")
    maximum_total_drawdown_percent: Decimal = Decimal("10.0")
    maximum_open_positions: int = 1
    maximum_trades_per_day: int = 3
    minimum_stop_loss_points: int = 50
    maximum_stop_loss_points: int = 500
    include_floating_loss_in_daily_limit: bool = True


@dataclass(slots=True)
class ExecutionSettings:
    maximum_spread_points: int = 25
    maximum_deviation_points: int = 10
    allow_buy: bool = True
    allow_sell: bool = True
    evaluate_closed_candles_only: bool = True


@dataclass(slots=True)
class SessionSettings:
    enabled: bool = True
    timezone: str = "UTC"
    start_hour: int = 7
    end_hour: int = 17


@dataclass(slots=True)
class BacktestSettings:
    initial_balance: Decimal = Decimal("10000")
    account_currency: str = "USD"
    leverage: int = 100
    commission_per_lot_round_turn: Decimal = Decimal("7.0")
    slippage_points: int = 2
    default_spread_points: int = 12
    start_date: str = "2022-01-01"
    end_date: str = "2026-06-01"
    stop_first_when_sl_and_tp_hit: bool = True


@dataclass(slots=True)
class UiSettings:
    database_path: str = "data/app/trading_bot.db"


@dataclass(slots=True)
class Settings:
    application: ApplicationSettings = field(default_factory=ApplicationSettings)
    trading: TradingSettings = field(default_factory=TradingSettings)
    strategy: StrategySettings = field(default_factory=StrategySettings)
    risk: RiskSettings = field(default_factory=RiskSettings)
    execution: ExecutionSettings = field(default_factory=ExecutionSettings)
    session: SessionSettings = field(default_factory=SessionSettings)
    backtest: BacktestSettings = field(default_factory=BacktestSettings)
    ui: UiSettings = field(default_factory=UiSettings)
