from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.config.models import Settings
from trading_bot.execution.mt5_gateway import MT5Gateway


class _FakeMT5:
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440

    def __init__(self) -> None:
        self.selected: tuple[str, bool] | None = None
        self.range_call: tuple[str, int, datetime, datetime] | None = None

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        self.selected = (symbol, enabled)
        return True

    def copy_rates_range(
        self,
        symbol: str,
        timeframe: int,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, object]]:
        self.range_call = (symbol, timeframe, start, end)
        return [
            {
                "time": int(datetime(2026, 6, 8, 9, 15, tzinfo=UTC).timestamp()),
                "open": 4305.25,
                "high": 4310.50,
                "low": 4301.00,
                "close": 4308.75,
                "tick_volume": 1200,
                "spread": 20,
                "real_volume": 0,
            }
        ]

    def last_error(self) -> tuple[int, str]:
        return (0, "")


def test_mt5_gateway_loads_historical_candles_for_date_range() -> None:
    mt5 = _FakeMT5()
    gateway = MT5Gateway(Settings())
    gateway._mt5 = mt5
    start = datetime(2026, 6, 8)
    end = datetime(2026, 6, 9)

    candles = gateway.get_candles_range("XAUUSD", "M15", start, end)

    assert mt5.selected == ("XAUUSD", True)
    assert mt5.range_call == (
        "XAUUSD",
        15,
        datetime(2026, 6, 8, tzinfo=UTC),
        datetime(2026, 6, 9, tzinfo=UTC),
    )
    assert candles[0].time == datetime(2026, 6, 8, 9, 15, tzinfo=UTC)
    assert candles[0].open == Decimal("4305.25")
    assert candles[0].complete is True
