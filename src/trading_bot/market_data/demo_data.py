from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import sin

from trading_bot.domain import Candle
from trading_bot.market_data.symbols import demo_price_profile


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
    symbol: str = "EURUSD",
) -> list[Candle]:
    start = start or datetime(2024, 1, 1, tzinfo=UTC)
    step = step or timedelta(hours=1)
    profile = demo_price_profile(symbol)
    pip_size = profile.pip_size
    price_unit = Decimal("1").scaleb(-profile.symbol.digits)
    candles: list[Candle] = []
    price = profile.base_price
    for index in range(count):
        wave = Decimal(str(sin(index / 19) * 12)) * pip_size
        trend = Decimal(index) * Decimal("0.02") * pip_size
        impulse = Decimal("0")
        if index % 180 in range(130, 145):
            impulse = Decimal("-5.5") * pip_size
        if index % 210 in range(160, 174):
            impulse = Decimal("5.5") * pip_size
        open_price = price
        close = profile.base_price + trend + wave + impulse
        if index % 9 == 0:
            direction = Decimal("1") if index % 18 == 0 else Decimal("-1")
            close = open_price + direction * Decimal("55") * pip_size
            high = max(open_price, close) + Decimal("5") * pip_size
            low = min(open_price, close) - Decimal("5") * pip_size
        else:
            high = max(open_price, close) + Decimal("6.5") * pip_size
            low = min(open_price, close) - Decimal("6.5") * pip_size
        candles.append(
            Candle(
                time=start + step * index,
                open=open_price.quantize(price_unit),
                high=high.quantize(price_unit),
                low=low.quantize(price_unit),
                close=close.quantize(price_unit),
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
    symbol: str = "EURUSD",
) -> list[Candle]:
    if end < start:
        start, end = end, start
    step = timeframe_delta(timeframe)
    end_exclusive = end + timedelta(days=1)
    count = int((end_exclusive - start).total_seconds() // step.total_seconds()) + warmup_bars
    return generate_demo_candles(
        count=max(minimum_count, count),
        start=start,
        step=step,
        symbol=symbol,
    )


def timeframe_delta(timeframe: str) -> timedelta:
    normalized = timeframe.upper()
    if normalized not in TIMEFRAME_DELTAS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return TIMEFRAME_DELTAS[normalized]
