from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.config.models import Settings
from trading_bot.domain import AccountSnapshot, Side, SymbolSnapshot, TradingSignal
from trading_bot.risk import PositionSizer, RiskManager, RuntimeRiskState


class RiskTests(unittest.TestCase):
    def test_position_sizing_respects_risk_and_step(self) -> None:
        symbol = _symbol()
        result = PositionSizer().size_by_risk(
            equity=Decimal("10000"),
            risk_percent=Decimal("0.5"),
            side=Side.BUY,
            symbol=symbol,
            entry_price=Decimal("1.10000"),
            stop_loss_price=Decimal("1.09500"),
            leverage=100,
        )
        self.assertEqual(result.volume, Decimal("0.10"))
        self.assertGreater(result.margin_required, Decimal("0"))

    def test_spread_rejection(self) -> None:
        settings = Settings()
        settings.risk.minimum_stop_loss_points = 1
        manager = RiskManager(settings)
        decision = manager.validate_entry(
            signal=_signal(),
            account=AccountSnapshot(
                login=None,
                server="TEST",
                currency="USD",
                balance=Decimal("10000"),
                equity=Decimal("10000"),
                free_margin=Decimal("10000"),
                trade_allowed=True,
            ),
            symbol=_symbol(),
            positions=[],
            state=RuntimeRiskState(
                start_of_day_equity=Decimal("10000"),
                equity_peak=Decimal("10000"),
            ),
            spread_points=999,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("spread", decision.reason)


def _symbol() -> SymbolSnapshot:
    return SymbolSnapshot(
        name="EURUSD",
        digits=5,
        point=Decimal("0.00001"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100"),
        volume_step=Decimal("0.01"),
    )


def _signal() -> TradingSignal:
    return TradingSignal(
        signal_id="test",
        symbol="EURUSD",
        timeframe="H1",
        side=Side.BUY,
        candle_time=datetime(2024, 1, 1, 8, tzinfo=UTC),
        entry_reference_price=Decimal("1.10000"),
        stop_loss_price=Decimal("1.09900"),
        take_profit_price=Decimal("1.10150"),
        atr=Decimal("0.001"),
        reason="test",
        strategy_name="TEST",
    )


if __name__ == "__main__":
    unittest.main()

