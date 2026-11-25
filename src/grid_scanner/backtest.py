
"""Conservative historical backtesting for a long-only Spot Grid."""

from __future__ import annotations

from math import isfinite
from typing import Any


DEFAULT_INITIAL_CAPITAL = 500.0
DEFAULT_GRID_SPACING_PERCENT = 0.5
DEFAULT_LEVELS_EACH_SIDE = 10
DEFAULT_FEE_RATE = 0.001
DEFAULT_SLIPPAGE_RATE = 0.0005


def _validate_candles(
    candles: list[dict[str, Any]],
) -> None:
    """Validate OHLC candles and chronological order."""
    if len(candles) < 2:
        raise ValueError("At least two candles are required")

    previous_time = None

    for candle in candles:
        if not isinstance(candle, dict):
            raise ValueError("Each candle must be a dictionary")

        values = {}

        for field in ("open", "high", "low", "close"):
            value = candle.get(field)

            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid candle field: {field}")

            if not isfinite(value) or value <= 0:
                raise ValueError(
                    f"Candle {field} must be finite and positive"
                )

            values[field] = float(value)

        if values["high"] < max(
            values["open"],
            values["low"],
            values["close"],
        ):
            raise ValueError("Invalid candle high")

        if values["low"] > min(
            values["open"],
            values["high"],
            values["close"],
        ):
            raise ValueError("Invalid candle low")

        if "open_time" in candle:
            current_time = candle["open_time"]

            if not isinstance(current_time, (int, float)):
                raise ValueError("Invalid candle open_time")

            if previous_time is not None and current_time <= previous_time:
                raise ValueError(
                    "Candles must be in chronological order"
                )

            previous_time = current_time


def _validate_parameters(
    initial_capital: float,
    grid_spacing_percent: float,
    levels_each_side: int,
    fee_rate: float,
    slippage_rate: float,
) -> None:
    """Validate backtest configuration."""
    if not isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("Initial capital must be positive")

    if (
        not isfinite(grid_spacing_percent)
        or grid_spacing_percent <= 0
    ):
        raise ValueError("Grid spacing must be positive")

    if (
        not isinstance(levels_each_side, int)
        or isinstance(levels_each_side, bool)
        or not 1 <= levels_each_side <= 1000
    ):
        raise ValueError(
            "Grid levels must be between 1 and 1000"
        )

    for name, rate in (
        ("Fee", fee_rate),
        ("Slippage", slippage_rate),
    ):
        if not isfinite(rate) or not 0 <= rate < 1:
            raise ValueError(
                f"{name} rate must be between 0 and 1"
            )


def backtest_spot_grid(
    candles: list[dict[str, Any]],
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    grid_spacing_percent: float = DEFAULT_GRID_SPACING_PERCENT,
    levels_each_side: int = DEFAULT_LEVELS_EACH_SIDE,
    fee_rate: float = DEFAULT_FEE_RATE,
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE,
) -> dict[str, Any]:
    """Simulate a conservative long-only Spot Grid.

    The first candle close establishes the grid center.
    Orders are evaluated only on subsequent candles.

    At most one order can fill per candle. If both buy and
    sell orders are touched within a candle, no order fills
    because OHLC data cannot establish the intrabar sequence.

    Initial crypto inventory is assumed to be pre-owned.
    Initial entry costs are excluded from both strategies.

    Fee and slippage rates are decimal fractions:
    0.001 means 0.1 percent.
    """
    _validate_candles(candles)

    _validate_parameters(
        initial_capital,
        grid_spacing_percent,
        levels_each_side,
        fee_rate,
        slippage_rate,
    )

    spacing = grid_spacing_percent / 100
    first_price = float(candles[0]["close"])

    cash = initial_capital / 2
    base_asset = (initial_capital / 2) / first_price

    initial_base = base_asset
    initial_cash = cash

    active_orders: dict[int, dict[str, Any]] = {}

    buy_budget = initial_cash / levels_each_side
    initial_sell_quantity = initial_base / levels_each_side

    def grid_price(index: int) -> float:
        return first_price * ((1 + spacing) ** index)

    def make_buy_order(
        index: int,
        quote_budget: float,
    ) -> dict[str, Any]:
        """Create a buy order with a fixed quote budget."""
        price = grid_price(index)
        effective_unit_cost = (
            price
            * (1 + slippage_rate)
            * (1 + fee_rate)
        )

        quantity = quote_budget / effective_unit_cost

        return {
            "side": "buy",
            "price": price,
            "quantity": quantity,
        }

    for index in range(-levels_each_side, 0):
        active_orders[index] = make_buy_order(
            index,
            buy_budget,
        )

    for index in range(1, levels_each_side + 1):
        active_orders[index] = {
            "side": "sell",
            "price": grid_price(index),
            "quantity": initial_sell_quantity,
        }

    fills = []
    equity_curve = [initial_capital]
    ambiguous_candles = 0
    total_fees = 0.0

    for candle_number, candle in enumerate(candles[1:], start=1):
        candle_low = float(candle["low"])
        candle_high = float(candle["high"])

        buy_candidates = []
        sell_candidates = []

        for index, order in active_orders.items():
            touched = (
                candle_low <= order["price"]
                if order["side"] == "buy"
                else candle_high >= order["price"]
            )

            if not touched:
                continue

            candidate = (index, order)

            if order["side"] == "buy":
                buy_candidates.append(candidate)
            else:
                sell_candidates.append(candidate)

        if buy_candidates and sell_candidates:
            ambiguous_candles += 1

        elif buy_candidates:
            index, order = max(
                buy_candidates,
                key=lambda item: item[0],
            )

            limit_price = order["price"]
            execution_price = (
                limit_price * (1 + slippage_rate)
            )
            quantity = order["quantity"]

            gross_cost = execution_price * quantity
            fee = gross_cost * fee_rate
            total_cost = gross_cost + fee

            if cash + 1e-10 >= total_cost:
                cash -= total_cost
                base_asset += quantity
                total_fees += fee

                del active_orders[index]

                next_index = index + 1

                if next_index not in active_orders:
                    active_orders[next_index] = {
                        "side": "sell",
                        "price": grid_price(next_index),
                        "quantity": quantity,
                    }

                fills.append(
                    {
                        "candle_index": candle_number,
                        "time": candle.get("open_time"),
                        "side": "buy",
                        "grid_price": limit_price,
                        "execution_price": execution_price,
                        "quantity": quantity,
                        "fee": fee,
                    }
                )

        elif sell_candidates:
            index, order = min(
                sell_candidates,
                key=lambda item: item[0],
            )

            limit_price = order["price"]
            execution_price = (
                limit_price * (1 - slippage_rate)
            )
            quantity = order["quantity"]

            if base_asset + 1e-10 >= quantity:
                gross_proceeds = execution_price * quantity
                fee = gross_proceeds * fee_rate
                net_proceeds = gross_proceeds - fee

                base_asset -= quantity
                cash += net_proceeds
                total_fees += fee

                del active_orders[index]

                next_index = index - 1

                if next_index not in active_orders:
                    active_orders[next_index] = make_buy_order(
                        next_index,
                        net_proceeds,
                    )

                fills.append(
                    {
                        "candle_index": candle_number,
                        "time": candle.get("open_time"),
                        "side": "sell",
                        "grid_price": limit_price,
                        "execution_price": execution_price,
                        "quantity": quantity,
                        "fee": fee,
                    }
                )

        close_price = float(candle["close"])
        equity = cash + (base_asset * close_price)
        equity_curve.append(equity)

    final_price = float(candles[-1]["close"])
    final_equity = cash + (base_asset * final_price)

    peak_equity = initial_capital
    maximum_drawdown = 0.0

    for equity in equity_curve:
        peak_equity = max(peak_equity, equity)

        drawdown = (
            (peak_equity - equity) / peak_equity
            if peak_equity > 0
            else 0.0
        )

        maximum_drawdown = max(
            maximum_drawdown,
            drawdown,
        )

    net_profit = final_equity - initial_capital
    roi_percent = (
        net_profit / initial_capital
    ) * 100

    # Buy-and-hold benchmark invests all starting capital
    # at the same initial reference price.
    # Initial entry and final exit costs are excluded for
    # both strategies to keep the comparison consistent.
    hold_quantity = initial_capital / first_price
    hold_final_equity = hold_quantity * final_price

    hold_profit = hold_final_equity - initial_capital
    hold_roi_percent = (
        hold_profit / initial_capital
    ) * 100

    return {
        "strategy": "long_only_spot_grid",
        "initial_capital": initial_capital,
        "grid_center": first_price,
        "grid_spacing_percent": grid_spacing_percent,
        "levels_each_side": levels_each_side,
        "fee_rate": fee_rate,
        "slippage_rate": slippage_rate,
        "candle_count": len(candles),
        "trade_count": len(fills),
        "buy_count": sum(
            fill["side"] == "buy" for fill in fills
        ),
        "sell_count": sum(
            fill["side"] == "sell" for fill in fills
        ),
        "ambiguous_candles_skipped": ambiguous_candles,
        "total_fees": total_fees,
        "final_price": final_price,
        "final_cash": cash,
        "final_base_asset": base_asset,
        "final_equity": final_equity,
        "net_profit": net_profit,
        "roi_percent": roi_percent,
        "maximum_drawdown_percent": maximum_drawdown * 100,
        "buy_and_hold_final_equity": hold_final_equity,
        "buy_and_hold_roi_percent": hold_roi_percent,
        "equity_curve": equity_curve,
        "fills": fills,
    }
