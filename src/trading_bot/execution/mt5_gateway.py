from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_bot.common.exceptions import ExecutionError
from trading_bot.config.models import Settings
from trading_bot.domain import (
    AccountSnapshot,
    Candle,
    OrderRequest,
    OrderResult,
    OrderValidationResult,
    Position,
    Side,
    SymbolSnapshot,
    Tick,
)


class MT5Gateway:
    def __init__(
        self,
        settings: Settings,
        terminal_path: str = "",
        login: int | None = None,
        password: str = "",
        server: str = "",
    ) -> None:
        self.settings = settings
        self.terminal_path = terminal_path
        self.login = login
        self.password = password
        self.server = server
        self._mt5: Any | None = None

    def connect(self) -> None:
        import MetaTrader5 as mt5  # type: ignore

        self._mt5 = mt5
        kwargs: dict[str, Any] = {}
        if self.terminal_path:
            kwargs["path"] = str(Path(self.terminal_path))
        if self.login:
            kwargs["login"] = int(self.login)
        if self.password:
            kwargs["password"] = self.password
        if self.server:
            kwargs["server"] = self.server
        if not mt5.initialize(**kwargs):
            raise ExecutionError(f"MT5 initialize failed: {mt5.last_error()}")
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            last_error = mt5.last_error()
            mt5.shutdown()
            raise ExecutionError(f"MT5 terminal/account unavailable: {last_error}")

    def disconnect(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()

    def get_account(self) -> AccountSnapshot:
        mt5 = self._require_mt5()
        account = mt5.account_info()
        if account is None:
            raise ExecutionError(f"MT5 account_info failed: {mt5.last_error()}")
        return AccountSnapshot(
            login=int(account.login),
            server=str(account.server),
            currency=str(account.currency),
            balance=Decimal(str(account.balance)),
            equity=Decimal(str(account.equity)),
            margin=Decimal(str(account.margin)),
            free_margin=Decimal(str(account.margin_free)),
            leverage=int(account.leverage),
            trade_allowed=bool(account.trade_allowed),
        )

    def get_symbol(self, symbol: str) -> SymbolSnapshot:
        mt5 = self._require_mt5()
        if not mt5.symbol_select(symbol, True):
            raise ExecutionError(f"MT5 symbol_select failed for {symbol}: {mt5.last_error()}")
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ExecutionError(f"MT5 symbol_info failed for {symbol}: {mt5.last_error()}")
        return SymbolSnapshot(
            name=symbol,
            digits=int(info.digits),
            point=Decimal(str(info.point)),
            volume_min=Decimal(str(info.volume_min)),
            volume_max=Decimal(str(info.volume_max)),
            volume_step=Decimal(str(info.volume_step)),
            contract_size=Decimal(str(info.trade_contract_size)),
            trade_stops_level=int(info.trade_stops_level),
            trade_freeze_level=int(info.trade_freeze_level),
            filling_modes=(str(getattr(info, "filling_mode", "")),),
        )

    def get_latest_tick(self, symbol: str) -> Tick:
        mt5 = self._require_mt5()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ExecutionError(f"MT5 symbol_info_tick failed for {symbol}: {mt5.last_error()}")
        return Tick(
            symbol=symbol,
            time=datetime.fromtimestamp(int(tick.time), tz=UTC),
            bid=Decimal(str(tick.bid)),
            ask=Decimal(str(tick.ask)),
        )

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        mt5 = self._require_mt5()
        mt5_timeframe = self._timeframe(timeframe)
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
        if rates is None:
            raise ExecutionError(f"MT5 copy_rates_from_pos failed: {mt5.last_error()}")
        candles: list[Candle] = []
        for row in rates:
            candles.append(
                Candle(
                    time=datetime.fromtimestamp(int(row["time"]), tz=UTC),
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    tick_volume=int(row["tick_volume"]),
                    spread=int(row["spread"]),
                    real_volume=int(row["real_volume"]),
                    complete=True,
                )
            )
        if candles:
            candles[-1] = Candle(
                time=candles[-1].time,
                open=candles[-1].open,
                high=candles[-1].high,
                low=candles[-1].low,
                close=candles[-1].close,
                tick_volume=candles[-1].tick_volume,
                spread=candles[-1].spread,
                real_volume=candles[-1].real_volume,
                complete=False,
            )
        return candles

    def get_open_positions(self, symbol: str, magic_number: int) -> list[Position]:
        mt5 = self._require_mt5()
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return []
        result: list[Position] = []
        for position in positions:
            if int(position.magic) != magic_number:
                continue
            side = Side.BUY if int(position.type) == mt5.POSITION_TYPE_BUY else Side.SELL
            result.append(
                Position(
                    position_id=str(position.ticket),
                    symbol=str(position.symbol),
                    side=side,
                    volume=Decimal(str(position.volume)),
                    entry_price=Decimal(str(position.price_open)),
                    stop_loss=Decimal(str(position.sl)),
                    take_profit=Decimal(str(position.tp)),
                    open_time=datetime.fromtimestamp(int(position.time), tz=UTC),
                    magic_number=int(position.magic),
                    comment=str(position.comment),
                    unrealized_pnl=Decimal(str(position.profit)),
                )
            )
        return result

    def calculate_profit(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        open_price: Decimal,
        close_price: Decimal,
    ) -> Decimal:
        mt5 = self._require_mt5()
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        value = mt5.order_calc_profit(
            order_type,
            symbol,
            float(volume),
            float(open_price),
            float(close_price),
        )
        if value is None:
            raise ExecutionError(f"MT5 order_calc_profit failed: {mt5.last_error()}")
        return Decimal(str(value))

    def calculate_margin(
        self,
        side: str,
        symbol: str,
        volume: Decimal,
        price: Decimal,
    ) -> Decimal:
        mt5 = self._require_mt5()
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        value = mt5.order_calc_margin(order_type, symbol, float(volume), float(price))
        if value is None:
            raise ExecutionError(f"MT5 order_calc_margin failed: {mt5.last_error()}")
        return Decimal(str(value))

    def validate_order(self, order: OrderRequest) -> OrderValidationResult:
        mt5 = self._require_mt5()
        request = self._request(order)
        response = mt5.order_check(request)
        if response is None:
            return OrderValidationResult(False, f"order_check failed: {mt5.last_error()}")
        result_code = int(response.retcode)
        success = result_code in {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}
        return OrderValidationResult(success, str(getattr(response, "comment", "")), response._asdict())

    def send_market_order(self, order: OrderRequest) -> OrderResult:
        mt5 = self._require_mt5()
        request = self._request(order)
        response = mt5.order_send(request)
        if response is None:
            return OrderResult(
                success=False,
                client_order_id=order.client_order_id,
                signal_id=order.signal_id,
                reason=f"order_send failed: {mt5.last_error()}",
            )
        result_code = int(response.retcode)
        success = result_code in {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}
        return OrderResult(
            success=success,
            client_order_id=order.client_order_id,
            signal_id=order.signal_id,
            order_ticket=int(getattr(response, "order", 0) or 0),
            deal_ticket=int(getattr(response, "deal", 0) or 0),
            result_code=result_code,
            execution_price=Decimal(str(getattr(response, "price", order.entry_price))),
            volume=Decimal(str(getattr(response, "volume", order.volume))),
            reason=str(getattr(response, "comment", "")),
            raw=response._asdict(),
        )

    def _request(self, order: OrderRequest) -> dict[str, Any]:
        mt5 = self._require_mt5()
        order_type = mt5.ORDER_TYPE_BUY if order.side is Side.BUY else mt5.ORDER_TYPE_SELL
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": order.symbol,
            "volume": float(order.volume),
            "type": order_type,
            "price": float(order.entry_price),
            "sl": float(order.stop_loss),
            "tp": float(order.take_profit),
            "deviation": order.deviation_points,
            "magic": order.magic_number,
            "comment": order.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

    def _require_mt5(self) -> Any:
        if self._mt5 is None:
            raise ExecutionError("MT5 gateway is not connected")
        return self._mt5

    def _timeframe(self, timeframe: str) -> int:
        mt5 = self._require_mt5()
        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        if timeframe not in mapping:
            raise ExecutionError(f"Unsupported MT5 timeframe: {timeframe}")
        return mapping[timeframe]

