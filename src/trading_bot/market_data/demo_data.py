from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import sin

from trading_bot.domain import Candle


TIMEFRAME_DELTAS = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
}


def generate_demo_candles(
    count: int = 1200,
    start: datetime | None = None,
    step: timedelta | None = None,
) -> list[Candle]:
    start = start or datetime(2024, 1, 1, tzinfo=UTC)
    step = step or timedelta(hours=1)
    candles: list[Candle] = []
    price = Decimal("1.08000")
    for index in range(count):
        wave = Decimal(str(sin(index / 19) * 0.0012))
        trend = Decimal(index) * Decimal("0.000002")
        impulse = Decimal("0")
        if index % 180 in range(130, 145):
            impulse = Decimal("-0.00055")
        if index % 210 in range(160, 174):
            impulse = Decimal("0.00055")
        open_price = price
        close = Decimal("1.08000") + trend + wave + impulse
        if index % 9 == 0:
            direction = Decimal("1") if index % 18 == 0 else Decimal("-1")
            close = open_price + direction * Decimal("0.00550")
            high = max(open_price, close) + Decimal("0.00050")
            low = min(open_price, close) - Decimal("0.00050")
        else:
            high = max(open_price, close) + Decimal("0.00065")
            low = min(open_price, close) - Decimal("0.00065")
        candles.append(
            Candle(
                time=start + step * index,
                open=open_price.quantize(Decimal("0.00001")),
                high=high.quantize(Decimal("0.00001")),
                low=low.quantize(Decimal("0.00001")),
                close=close.quantize(Decimal("0.00001")),
                tick_volume=1000 + (index % 200),
                spread=12 + (index % 4),
                real_volume=0,
                complete=True,
            )
        )
        price = close
    return candles


def generate_demo_candles_for_range(
    start: datetime,
    end: datetime,
    timeframe: str,
    minimum_count: int = 300,
    warmup_bars: int = 48,
) -> list[Candle]:
    if end < start:
        start, end = end, start
    step = timeframe_delta(timeframe)
    end_exclusive = end + timedelta(days=1)
    count = int((end_exclusive - start).total_seconds() // step.total_seconds()) + warmup_bars
    return generate_demo_candles(count=max(minimum_count, count), start=start, step=step)


def timeframe_delta(timeframe: str) -> timedelta:
    normalized = timeframe.upper()
    if normalized not in TIMEFRAME_DELTAS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return TIMEFRAME_DELTAS[normalized]
