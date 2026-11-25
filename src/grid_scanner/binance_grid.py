
"""Binance-style Manual Spot Grid simulation.

This is a candle-based approximation, not an exact reproduction
of Binance's live matching engine or order-book execution.
"""

from __future__ import annotations

from math import isfinite
from typing import Any

from grid_scanner.backtest import _validate_candles


DEFAULT_INITIAL_CAPITAL = 500.0
DEFAULT_GRID_COUNT = 10
DEFAULT_FEE_RATE = 0.001
DEFAULT_SLIPPAGE_RATE = 0.0005


def _validate_settings(
    initial_capital: float,
    lower_price: float,
    upper_price: float,
    grid_count: int,
    mode: str,
    fee_rate: float,
    slippage_rate: float,
) -> None:
    """Validate Binance-style manual grid settings."""

    for name, value in (
        ("Initial capital", initial_capital),
        ("Lower price", lower_price),
        ("Upper price", upper_price),
    ):
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{name} must be finite and positive")

    if lower_price >= upper_price:
        raise ValueError("Lower price must be below upper price")

    if (
        not isinstance(grid_count, int)
        or isinstance(grid_count, bool)
        or not 2 <= grid_count <= 1000
    ):
        raise ValueError("Grid count must be between 2 and 1000")

    if mode not in ("arithmetic", "geometric"):
        raise ValueError(
            "Mode must be 'arithmetic' or 'geometric'"
        )

    for name, rate in (
        ("Fee", fee_rate),
        ("Slippage", slippage_rate),
    ):
        if (
            not isinstance(rate, (int, float))
            or isinstance(rate, bool)
            or not isfinite(rate)
            or not 0 <= rate < 1
        ):
            raise ValueError(
                f"{name} rate must be between 0 and 1"
            )


def calculate_grid_prices(
    lower_price: float,
    upper_price: float,
    grid_count: int,
    mode: str = "arithmetic",
) -> list[float]:
    """Calculate the price levels for a manual grid.

    Arithmetic:
        Equal absolute price differences.

    Geometric:
        Equal percentage differences.
    """

    _validate_settings(
        initial_capital=1.0,
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=grid_count,
        mode=mode,
        fee_rate=0.0,
        slippage_rate=0.0,
    )

    if mode == "arithmetic":
        step = (upper_price - lower_price) / grid_count

        prices = [
            lower_price + (step * index)
            for index in range(grid_count + 1)
        ]

    else:
        ratio = (upper_price / lower_price) ** (
            1 / grid_count
        )

        prices = [
            lower_price * (ratio ** index)
            for index in range(grid_count + 1)
        ]

    prices[0] = lower_price
    prices[-1] = upper_price

    return prices


def backtest_binance_spot_grid(
    candles: list[dict[str, Any]],
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    lower_price: float = 0.0,
    upper_price: float = 0.0,
    grid_count: int = DEFAULT_GRID_COUNT,
    mode: str = "arithmetic",
    fee_rate: float = DEFAULT_FEE_RATE,
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE,
) -> dict[str, Any]:
    """Simulate a Binance-style Manual Spot Grid.

    The first candle close is the starting market price.

    Initial quote and base inventory are allocated according
    to the number of buy and sell levels around that price.

    Only completed historical candles should be supplied.

    Execution assumptions:
    - Limit orders fill when a candle touches their price.
    - At most one order fills per candle.
    - If both buy and sell orders are touched, the candle is
      considered ambiguous and no order fills.
    - Filled buys create a sell order one level higher.
    - Filled sells create a buy order one level lower.
    - Orders outside the configured grid are not created.

    This is an approximation. It does not reproduce Binance's
    order-book queue, exact allocation, or live fill behavior.
    """

    _validate_candles(candles)

    _validate_settings(
        initial_capital,
        lower_price,
        upper_price,
        grid_count,
        mode,
        fee_rate,
        slippage_rate,
    )

    grid_prices = calculate_grid_prices(
        lower_price,
        upper_price,
        grid_count,
        mode,
    )

    starting_price = float(candles[0]["close"])

    if not lower_price <= starting_price <= upper_price:
        raise ValueError(
            "Starting candle close must be inside the grid range"
        )

    buy_levels = [
        index
        for index, price in enumerate(grid_prices)
        if price < starting_price
    ]

    sell_levels = [
        index
        for index, price in enumerate(grid_prices)
        if price > starting_price
    ]

    initial_order_count = len(buy_levels) + len(sell_levels)

    if initial_order_count == 0:
        raise ValueError(
            "No initial grid orders can be created"
        )

    # Allocate the starting portfolio across the two sides.
    # This is a simplified allocation model, not Binance's
    # proprietary or exact live investment allocation.
    if buy_levels:
        quote_fraction = (
            len(buy_levels) / initial_order_count
        )
    else:
        quote_fraction = 0.0

    quote_cash = initial_capital * quote_fraction
    base_value = initial_capital - quote_cash
    base_asset = base_value / starting_price

    initial_quote_cash = quote_cash
    initial_base_asset = base_asset

    active_orders: dict[int, dict[str, Any]] = {}

    # Distribute initial quote capital across buy orders.
    if buy_levels:
        quote_budget_per_buy = (
            quote_cash / len(buy_levels)
        )

        for index in buy_levels:
            price = grid_prices[index]

            effective_cost_per_unit = (
                price
                * (1 + slippage_rate)
                * (1 + fee_rate)
            )

            quantity = (
                quote_budget_per_buy
                / effective_cost_per_unit
            )

            active_orders[index] = {
                "side": "buy",
                "price": price,
                "quantity": quantity,
            }

    # Distribute initial base inventory across sell orders.
    if sell_levels:
        quantity_per_sell = (
            base_asset / len(sell_levels)
        )

        for index in sell_levels:
            active_orders[index] = {
                "side": "sell",
                "price": grid_prices[index],
                "quantity": quantity_per_sell,
            }

    fills: list[dict[str, Any]] = []
    equity_curve = [initial_capital]
    total_fees = 0.0
    ambiguous_candles = 0

    for candle_number, candle in enumerate(
        candles[1:],
        start=1,
    ):
        candle_low = float(candle["low"])
        candle_high = float(candle["high"])

        buy_candidates = []
        sell_candidates = []

        for index, order in active_orders.items():
            price = order["price"]

            if order["side"] == "buy":
                if candle_low <= price:
                    buy_candidates.append((index, order))
            else:
                if candle_high >= price:
                    sell_candidates.append((index, order))

        # OHLC candles cannot tell us which side traded first.
        if buy_candidates and sell_candidates:
            ambiguous_candles += 1

        elif buy_candidates:
            # Select the buy level closest to the market.
            index, order = max(
                buy_candidates,
                key=lambda item: item[0],
            )

            limit_price = order["price"]
            quantity = order["quantity"]

            execution_price = (
                limit_price * (1 + slippage_rate)
            )

            gross_cost = execution_price * quantity
            fee = gross_cost * fee_rate
            total_cost = gross_cost + fee

            if quote_cash + 1e-10 >= total_cost:
                quote_cash -= total_cost
                base_asset += quantity
                total_fees += fee

                del active_orders[index]

                # A buy is followed by a sell one level higher.
                next_index = index + 1

                if (
                    next_index <= grid_count
                    and next_index not in active_orders
                ):
                    active_orders[next_index] = {
                        "side": "sell",
                        "price": grid_prices[next_index],
                        "quantity": quantity,
                    }

                fills.append({
                    "candle_index": candle_number,
                    "time": candle.get("open_time"),
                    "side": "buy",
                    "grid_index": index,
                    "grid_price": limit_price,
                    "execution_price": execution_price,
                    "quantity": quantity,
                    "fee": fee,
                })

        elif sell_candidates:
            # Select the sell level closest to the market.
            index, order = min(
                sell_candidates,
                key=lambda item: item[0],
            )

            limit_price = order["price"]
            quantity = order["quantity"]

            execution_price = (
                limit_price * (1 - slippage_rate)
            )

            if base_asset + 1e-10 >= quantity:
                gross_proceeds = execution_price * quantity
                fee = gross_proceeds * fee_rate
                net_proceeds = gross_proceeds - fee

                base_asset -= quantity
                quote_cash += net_proceeds
                total_fees += fee

                del active_orders[index]

                # A sell is followed by a buy one level lower.
                next_index = index - 1

                if (
                    next_index >= 0
                    and next_index not in active_orders
                ):
                    active_orders[next_index] = {
                        "side": "buy",
                        "price": grid_prices[next_index],
                        "quantity": quantity,
                    }

                fills.append({
                    "candle_index": candle_number,
                    "time": candle.get("open_time"),
                    "side": "sell",
                    "grid_index": index,
                    "grid_price": limit_price,
                    "execution_price": execution_price,
                    "quantity": quantity,
                    "fee": fee,
                })

        close_price = float(candle["close"])
        equity = quote_cash + (base_asset * close_price)
        equity_curve.append(equity)

    final_price = float(candles[-1]["close"])
    final_equity = quote_cash + (base_asset * final_price)

    peak_equity = initial_capital
    maximum_drawdown = 0.0

    for equity in equity_curve:
        peak_equity = max(peak_equity, equity)

        if peak_equity > 0:
            drawdown = (
                (peak_equity - equity) / peak_equity
            )
            maximum_drawdown = max(
                maximum_drawdown,
                drawdown,
            )

    net_profit = final_equity - initial_capital
    roi_percent = (
        net_profit / initial_capital
    ) * 100

    # Buy-and-hold uses the same starting portfolio value.
    hold_quantity = initial_capital / starting_price
    hold_final_equity = hold_quantity * final_price

    hold_roi_percent = (
        (hold_final_equity - initial_capital)
        / initial_capital
    ) * 100

    return {
        "strategy": "binance_manual_spot_grid_approximation",
        "mode": mode,
        "initial_capital": initial_capital,
        "initial_quote_cash": initial_quote_cash,
        "initial_base_asset": initial_base_asset,
        "starting_price": starting_price,
        "lower_price": lower_price,
        "upper_price": upper_price,
        "grid_count": grid_count,
        "grid_prices": grid_prices,
        "grid_step_percent": (
            (grid_prices[1] / grid_prices[0] - 1) * 100
            if mode == "geometric"
            else None
        ),
        "fee_rate": fee_rate,
        "slippage_rate": slippage_rate,
        "candle_count": len(candles),
        "initial_buy_order_count": len(buy_levels),
        "initial_sell_order_count": len(sell_levels),
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
        "final_quote_cash": quote_cash,
        "final_base_asset": base_asset,
        "final_equity": final_equity,
        "net_profit": net_profit,
        "roi_percent": roi_percent,
        "maximum_drawdown_percent": (
            maximum_drawdown * 100
        ),
        "buy_and_hold_final_equity": hold_final_equity,
        "buy_and_hold_roi_percent": hold_roi_percent,
        "equity_curve": equity_curve,
        "fills": fills,
    }
