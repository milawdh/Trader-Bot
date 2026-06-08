from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from trading_bot.config.models import Settings
from trading_bot.domain import Candle, TradingSignal


@dataclass(frozen=True, slots=True)
class StrategyContext:
    settings: Settings


class TradingStrategy(Protocol):
    name: str
    version: str
    description: str
    parameters_schema: dict[str, object]

    def generate_signal(
        self,
        candles: list[Candle],
        context: StrategyContext,
    ) -> TradingSignal | None:
        ...

