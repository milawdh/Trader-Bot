from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading_bot.common.decimal_utils import ZERO, floor_to_step
from trading_bot.domain import Side, SymbolSnapshot


@dataclass(frozen=True, slots=True)
class PositionSizingResult:
    volume: Decimal
    raw_volume: Decimal
    risk_amount: Decimal
    loss_for_one_lot: Decimal
    margin_required: Decimal
    reason: str = ""


class PositionSizer:
    def size_by_risk(
        self,
        equity: Decimal,
        risk_percent: Decimal,
        side: Side,
        symbol: SymbolSnapshot,
        entry_price: Decimal,
        stop_loss_price: Decimal,
        leverage: int,
    ) -> PositionSizingResult:
        del side
        if equity <= ZERO:
            return self._reject("equity must be positive")
        if risk_percent <= ZERO:
            return self._reject("risk percent must be positive")
        stop_distance = abs(entry_price - stop_loss_price)
        if stop_distance <= ZERO:
            return self._reject("stop distance must be positive")
        loss_for_one_lot = stop_distance * symbol.contract_size
        if loss_for_one_lot <= ZERO:
            return self._reject("loss for one lot is invalid")

        risk_amount = equity * risk_percent / Decimal("100")
        raw_volume = risk_amount / loss_for_one_lot
        normalized = floor_to_step(raw_volume, symbol.volume_step)
        if normalized < symbol.volume_min:
            return self._reject(
                "normalized volume is below broker minimum",
                raw_volume=raw_volume,
                risk_amount=risk_amount,
                loss_for_one_lot=loss_for_one_lot,
            )
        if normalized > symbol.volume_max:
            normalized = symbol.volume_max
        margin_required = self.estimate_margin(symbol, entry_price, normalized, leverage)
        return PositionSizingResult(
            volume=normalized,
            raw_volume=raw_volume,
            risk_amount=risk_amount,
            loss_for_one_lot=loss_for_one_lot,
            margin_required=margin_required,
        )

    @staticmethod
    def estimate_margin(
        symbol: SymbolSnapshot,
        entry_price: Decimal,
        volume: Decimal,
        leverage: int,
    ) -> Decimal:
        if leverage <= 0:
            raise ValueError("leverage must be positive")
        return entry_price * symbol.contract_size * volume / Decimal(leverage)

    @staticmethod
    def _reject(
        reason: str,
        raw_volume: Decimal = ZERO,
        risk_amount: Decimal = ZERO,
        loss_for_one_lot: Decimal = ZERO,
    ) -> PositionSizingResult:
        return PositionSizingResult(
            volume=ZERO,
            raw_volume=raw_volume,
            risk_amount=risk_amount,
            loss_for_one_lot=loss_for_one_lot,
            margin_required=ZERO,
            reason=reason,
        )

