
"""Compare multiple Spot Grid configurations on historical candles."""

from __future__ import annotations

import time
from math import isfinite
from typing import Any, Iterable

from grid_scanner.backtest import backtest_spot_grid
from grid_scanner.history import fetch_binance_klines
from grid_scanner.research import to_binance_symbol


DEFAULT_SPACING_OPTIONS = (0.3, 0.5, 0.75, 1.0)
DEFAULT_LEVEL_OPTIONS = (5, 10, 15)


def run_binance_spot_grid_parameter_sweep(
    symbols: Iterable[str],
    interval: str = "1h",
    candle_limit: int = 500,
    initial_capital: float = 500.0,
    spacing_options: Iterable[float] = DEFAULT_SPACING_OPTIONS,
    level_options: Iterable[int] = DEFAULT_LEVEL_OPTIONS,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> dict[str, Any]:
    """Compare grid configurations for multiple Binance pairs.

    Historical candles are fetched once per pair and reused
    across every configuration.
    """
    if isinstance(symbols, str):
        raise ValueError("Symbols must be a list of trading pairs")

    pair_list = list(symbols)
    spacings = list(spacing_options)
    levels = list(level_options)

    if not pair_list:
        raise ValueError("At least one trading pair is required")

    if not spacings or not levels:
        raise ValueError("Spacing and level options cannot be empty")

    for spacing in spacings:
        if (
            isinstance(spacing, bool)
            or not isinstance(spacing, (int, float))
            or not isfinite(spacing)
            or spacing <= 0
        ):
            raise ValueError("Every grid spacing must be positive")

    for level in levels:
        if (
            not isinstance(level, int)
            or isinstance(level, bool)
            or not 1 <= level <= 1000
        ):
            raise ValueError(
                "Every grid level must be between 1 and 1000"
            )

    configurations = [
        {
            "grid_spacing_percent": spacing,
            "levels_each_side": level,
        }
        for spacing in spacings
        for level in levels
    ]

    results = []
    errors = []

    for symbol in pair_list:
        try:
            binance_symbol = to_binance_symbol(symbol)

            candles = fetch_binance_klines(
                binance_symbol,
                interval,
                limit=candle_limit,
            )

            current_time_ms = int(time.time() * 1000)

            completed_candles = [
                candle
                for candle in candles
                if (
                    isinstance(candle.get("close_time"), (int, float))
                    and candle["close_time"] <= current_time_ms
                )
            ]

            if len(completed_candles) < 2:
                raise ValueError(
                    "At least two completed historical candles are required"
                )

        except Exception as error:
            errors.append({
                "symbol": str(symbol),
                "error": str(error),
            })
            continue

        for configuration in configurations:
            try:
                result = backtest_spot_grid(
                    completed_candles,
                    initial_capital=initial_capital,
                    grid_spacing_percent=configuration[
                        "grid_spacing_percent"
                    ],
                    levels_each_side=configuration[
                        "levels_each_side"
                    ],
                    fee_rate=fee_rate,
                    slippage_rate=slippage_rate,
                )

                result.update({
                    "exchange": "binance",
                    "symbol": symbol.upper(),
                    "binance_symbol": binance_symbol,
                    "interval": interval,
                    "first_candle_time": completed_candles[0]["open_time"],
                    "last_candle_time": completed_candles[-1]["open_time"],
                })

                results.append(result)

            except Exception as error:
                errors.append({
                    "symbol": str(symbol),
                    "configuration": configuration.copy(),
                    "error": str(error),
                })

    return {
        "exchange": "binance",
        "interval": interval,
        "requested_pairs": len(pair_list),
        "configurations_per_pair": len(configurations),
        "requested_tests": len(pair_list) * len(configurations),
        "success_count": len(results),
        "failure_count": len(errors),
        "configurations": configurations,
        "results": results,
        "errors": errors,
    }
