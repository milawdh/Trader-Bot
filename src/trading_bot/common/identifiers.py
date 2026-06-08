from __future__ import annotations

from datetime import datetime, timezone


def normalize_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def signal_id(
    symbol: str,
    timeframe: str,
    candle_time: datetime,
    side: str,
    strategy_name: str,
) -> str:
    return f"{symbol}:{timeframe}:{normalize_utc_iso(candle_time)}:{side}:{strategy_name}"

