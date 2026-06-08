from __future__ import annotations

from decimal import Decimal

from trading_bot.domain import Candle


IndicatorSeries = list[Decimal | None]


def ema(values: list[Decimal], period: int) -> IndicatorSeries:
    if period <= 0:
        raise ValueError("period must be positive")
    result: IndicatorSeries = [None] * len(values)
    if len(values) < period:
        return result
    multiplier = Decimal("2") / Decimal(period + 1)
    seed = sum(values[:period]) / Decimal(period)
    result[period - 1] = seed
    previous = seed
    for index in range(period, len(values)):
        previous = (values[index] - previous) * multiplier + previous
        result[index] = previous
    return result


def rsi(values: list[Decimal], period: int) -> IndicatorSeries:
    if period <= 0:
        raise ValueError("period must be positive")
    result: IndicatorSeries = [None] * len(values)
    if len(values) <= period:
        return result

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, Decimal("0")))
        losses.append(abs(min(change, Decimal("0"))))

    avg_gain = sum(gains) / Decimal(period)
    avg_loss = sum(losses) / Decimal(period)
    result[period] = _rsi_from_averages(avg_gain, avg_loss)

    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, Decimal("0"))
        loss = abs(min(change, Decimal("0")))
        avg_gain = ((avg_gain * Decimal(period - 1)) + gain) / Decimal(period)
        avg_loss = ((avg_loss * Decimal(period - 1)) + loss) / Decimal(period)
        result[index] = _rsi_from_averages(avg_gain, avg_loss)
    return result


def atr(candles: list[Candle], period: int) -> IndicatorSeries:
    if period <= 0:
        raise ValueError("period must be positive")
    result: IndicatorSeries = [None] * len(candles)
    if len(candles) < period:
        return result
    true_ranges: list[Decimal] = []
    for index, candle in enumerate(candles):
        if index == 0:
            true_range = candle.high - candle.low
        else:
            previous_close = candles[index - 1].close
            true_range = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        true_ranges.append(true_range)

    seed = sum(true_ranges[:period]) / Decimal(period)
    result[period - 1] = seed
    previous = seed
    for index in range(period, len(candles)):
        previous = ((previous * Decimal(period - 1)) + true_ranges[index]) / Decimal(period)
        result[index] = previous
    return result


def _rsi_from_averages(avg_gain: Decimal, avg_loss: Decimal) -> Decimal:
    if avg_loss == 0:
        return Decimal("100")
    relative_strength = avg_gain / avg_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))

