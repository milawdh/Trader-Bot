from __future__ import annotations

from dataclasses import dataclass

from trading_bot.strategies.base import TradingStrategy
from trading_bot.strategies.strong_candle import StrongCandleStrategy
from trading_bot.strategies.trend_pullback import TrendPullbackStrategy


@dataclass(frozen=True, slots=True)
class StrategyDescriptor:
    strategy_id: str
    name: str
    version: str
    description: str
    parameters_schema: dict[str, object]
    strategy: TradingStrategy


class StrategyRegistry:
    def __init__(self) -> None:
        self._items: dict[str, StrategyDescriptor] = {}

    def register(self, strategy_id: str, strategy: TradingStrategy) -> None:
        self._items[strategy_id] = StrategyDescriptor(
            strategy_id=strategy_id,
            name=strategy.name,
            version=strategy.version,
            description=strategy.description,
            parameters_schema=strategy.parameters_schema,
            strategy=strategy,
        )

    def get(self, strategy_id: str) -> StrategyDescriptor:
        if strategy_id not in self._items:
            raise KeyError(f"Unknown strategy: {strategy_id}")
        return self._items[strategy_id]

    def all(self) -> list[StrategyDescriptor]:
        return list(self._items.values())


def default_strategy_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register("trend_pullback_v1", TrendPullbackStrategy())
    registry.register("strong_candle_v1", StrongCandleStrategy())
    return registry
