from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading_bot.domain import SymbolSnapshot


@dataclass(frozen=True, slots=True)
class DemoPriceProfile:
    symbol: SymbolSnapshot
    base_price: Decimal

    @property
    def pip_size(self) -> Decimal:
        return pip_size_for_symbol(self.symbol.name)


def default_symbol_snapshot(symbol: str) -> SymbolSnapshot:
    name = symbol.strip() or "EURUSD"
    normalized = _normalized_symbol(name)
    if normalized.startswith("XAU"):
        return SymbolSnapshot(
            name=name,
            digits=2,
            point=Decimal("0.01"),
            volume_min=Decimal("0.01"),
            volume_max=Decimal("100"),
            volume_step=Decimal("0.01"),
            contract_size=Decimal("100"),
            trade_stops_level=0,
        )
    if normalized.startswith("XAG"):
        return SymbolSnapshot(
            name=name,
            digits=3,
            point=Decimal("0.001"),
            volume_min=Decimal("0.01"),
            volume_max=Decimal("100"),
            volume_step=Decimal("0.01"),
            contract_size=Decimal("5000"),
            trade_stops_level=0,
        )
    if normalized[:6].endswith("JPY"):
        return SymbolSnapshot(
            name=name,
            digits=3,
            point=Decimal("0.001"),
            volume_min=Decimal("0.01"),
            volume_max=Decimal("100"),
            volume_step=Decimal("0.01"),
            contract_size=Decimal("100000"),
            trade_stops_level=0,
        )
    return SymbolSnapshot(
        name=name,
        digits=5,
        point=Decimal("0.00001"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100"),
        volume_step=Decimal("0.01"),
        contract_size=Decimal("100000"),
        trade_stops_level=0,
    )


def demo_price_profile(symbol: str) -> DemoPriceProfile:
    snapshot = default_symbol_snapshot(symbol)
    normalized = _normalized_symbol(symbol)
    if normalized.startswith("XAU"):
        base = Decimal("2300.00")
    elif normalized.startswith("XAG"):
        base = Decimal("30.000")
    elif normalized[:6].endswith("JPY"):
        base = Decimal("150.000")
    elif normalized.startswith("GBP"):
        base = Decimal("1.27000")
    else:
        base = Decimal("1.08000")
    return DemoPriceProfile(symbol=snapshot, base_price=base)


def pip_size_for_symbol(symbol: str) -> Decimal:
    snapshot = default_symbol_snapshot(symbol)
    return snapshot.point * Decimal("10")


def price_digits_for_symbol(symbol: str) -> int:
    return default_symbol_snapshot(symbol).digits


def _normalized_symbol(symbol: str) -> str:
    return "".join(char for char in symbol.upper() if char.isalnum())
