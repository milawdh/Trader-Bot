from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.application.live_runner import LiveRunner
from trading_bot.application.paper_runner import PaperRunner
from trading_bot.config.models import Settings
from trading_bot.domain import (
    AccountSnapshot,
    Candle,
    OrderRequest,
    OrderResult,
    OrderValidationResult,
    Position,
    SymbolSnapshot,
    Tick,
)
from trading_bot.risk import RuntimeRiskState


class _StrongCandleGateway:
    def __init__(self) -> None:
        self.sent_order: OrderRequest | None = None

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def get_account(self) -> AccountSnapshot:
        return AccountSnapshot(
            login=123,
            server="TEST",
            currency="USD",
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            free_margin=Decimal("10000"),
            leverage=100,
            trade_allowed=True,
        )

    def get_symbol(self, symbol: str) -> SymbolSnapshot:
        return SymbolSnapshot(
            name=symbol,
            digits=2,
            point=Decimal("0.01"),
            volume_min=Decimal("0.01"),
            volume_max=Decimal("100"),
            volume_step=Decimal("0.01"),
            contract_size=Decimal("100"),
        )

    def get_latest_tick(self, symbol: str) -> Tick:
        return Tick(
            symbol=symbol,
            time=datetime(2026, 6, 10, 8, 35, tzinfo=UTC),
            bid=Decimal("105.90"),
            ask=Decimal("106.00"),
        )

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        del symbol, timeframe, count
        return [
            Candle(
                time=datetime(2026, 6, 10, 8, 30, tzinfo=UTC),
                open=Decimal("100.00"),
                high=Decimal("106.00"),
                low=Decimal("99.50"),
                close=Decimal("105.50"),
                spread=10,
                complete=True,
            )
        ]

    def get_open_positions(self, symbol: str, magic_number: int) -> list[Position]:
        del symbol, magic_number
        return []

    def calculate_profit(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        open_price: Decimal,
        close_price: Decimal,
    ) -> Decimal:
        del side, symbol, volume, open_price, close_price
        return Decimal("0")

    def calculate_margin(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        price: Decimal,
    ) -> Decimal:
        del side, symbol, volume, price
        return Decimal("0")

    def validate_order(self, order: OrderRequest) -> OrderValidationResult:
        self.sent_order = order
        return OrderValidationResult(True, "ok")

    def send_market_order(self, order: OrderRequest) -> OrderResult:
        self.sent_order = order
        return OrderResult(
            success=True,
            client_order_id=order.client_order_id,
            signal_id=order.signal_id,
            order_ticket=1,
            execution_price=order.entry_price,
            volume=order.volume,
        )


def test_paper_runner_strong_candle_uses_adjusted_entry_levels() -> None:
    settings = _strong_candle_settings()
    state = RuntimeRiskState(
        start_of_day_equity=Decimal("10000"),
        equity_peak=Decimal("10000"),
    )

    result = PaperRunner(settings, _StrongCandleGateway()).run_once(state)

    assert result.processed is True
    assert result.volume == Decimal("0.11")
    assert result.entry_price == Decimal("106.00")
    assert result.stop_loss == Decimal("101.50")
    assert result.take_profit == Decimal("114.00")


def test_live_runner_strong_candle_sends_adjusted_order(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    settings = _strong_candle_settings()
    settings.application.mode = "LIVE"
    gateway = _StrongCandleGateway()
    state = RuntimeRiskState(
        start_of_day_equity=Decimal("10000"),
        equity_peak=Decimal("10000"),
    )

    message = LiveRunner(settings, gateway).run_once(state)

    assert "Order executed" in message
    assert gateway.sent_order is not None
    assert gateway.sent_order.volume == Decimal("0.11")
    assert gateway.sent_order.entry_price == Decimal("106.00")
    assert gateway.sent_order.stop_loss == Decimal("101.50")
    assert gateway.sent_order.take_profit == Decimal("114.00")


def _strong_candle_settings() -> Settings:
    settings = Settings()
    settings.strategy.strategy_id = "strong_candle_v1"
    settings.trading.symbol = "XAUUSD"
    settings.trading.broker_symbol = "XAUUSD"
    settings.trading.timeframe = "M5"
    settings.session.enabled = False
    settings.strategy.strong_candle_min_body_pips = Decimal("50")
    settings.strategy.strong_candle_max_body_pips = Decimal("200")
    settings.strategy.strong_candle_max_total_wick_pips = Decimal("15")
    settings.strategy.strong_candle_stop_loss_pips = Decimal("45")
    settings.strategy.strong_candle_take_profit_pips = Decimal("80")
    return settings
