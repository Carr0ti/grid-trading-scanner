
"""Optimize Binance-style Manual Spot Grid configurations.

This is a historical candle-based research tool. It does not place trades
and does not reproduce Binance's exact matching-engine behavior.
"""

from __future__ import annotations

import time
from math import isfinite
from typing import Any, Iterable

from grid_scanner.binance_grid import backtest_binance_spot_grid
from grid_scanner.history import fetch_binance_klines
from grid_scanner.research import to_binance_symbol


DEFAULT_RANGE_WIDTHS_PERCENT = (10.0, 20.0, 30.0)
DEFAULT_GRID_COUNTS = (5, 10, 15, 20)
DEFAULT_MODES = ("arithmetic", "geometric")


def _validate_options(
    symbols: Iterable[str],
    interval: str,
    candle_limit: int,
    initial_capital: float,
    range_widths_percent: Iterable[float],
    grid_counts: Iterable[int],
    modes: Iterable[str],
    fee_rate: float,
    slippage_rate: float,
) -> tuple[list[str], list[float], list[int], list[str]]:
    """Validate and normalize optimizer settings."""

    if isinstance(symbols, str):
        raise ValueError("Symbols must be a list of USDT trading pairs")

    pair_list = list(symbols)
    widths = list(range_widths_percent)
    counts = list(grid_counts)
    mode_list = list(modes)

    if not pair_list:
        raise ValueError("At least one trading pair is required")

    normalized_pairs = []

    for symbol in pair_list:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Every trading pair must be non-empty")

        normalized = symbol.strip().upper()

        if not normalized.endswith("/USDT"):
            raise ValueError(
                f"{normalized} is not a USDT pair. "
                "This optimizer currently supports USDT pairs only."
            )

        normalized_pairs.append(normalized)

    if len(set(normalized_pairs)) != len(normalized_pairs):
        raise ValueError("Duplicate trading pairs are not allowed")

    if interval not in ("1h", "4h", "1d"):
        raise ValueError("Interval must be 1h, 4h, or 1d")

    if (
        not isinstance(candle_limit, int)
        or isinstance(candle_limit, bool)
        or not 2 <= candle_limit <= 1000
    ):
        raise ValueError("Candle limit must be between 2 and 1000")

    if (
        isinstance(initial_capital, bool)
        or not isinstance(initial_capital, (int, float))
        or not isfinite(initial_capital)
        or initial_capital <= 0
    ):
        raise ValueError("Initial capital must be finite and positive")

    if not widths:
        raise ValueError("At least one range width is required")

    for width in widths:
        if (
            isinstance(width, bool)
            or not isinstance(width, (int, float))
            or not isfinite(width)
            or not 0 < width < 200
        ):
            raise ValueError(
                "Every range width must be greater than 0 and below 200%"
            )

    if len(set(widths)) != len(widths):
        raise ValueError("Duplicate range widths are not allowed")

    if not counts:
        raise ValueError("At least one grid count is required")

    for count in counts:
        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or not 2 <= count <= 1000
        ):
            raise ValueError(
                "Every grid count must be between 2 and 1000"
            )

    if len(set(counts)) != len(counts):
        raise ValueError("Duplicate grid counts are not allowed")

    if not mode_list:
        raise ValueError("At least one grid mode is required")

    if any(mode not in ("arithmetic", "geometric") for mode in mode_list):
        raise ValueError(
            "Grid modes must be arithmetic or geometric"
        )

    if len(set(mode_list)) != len(mode_list):
        raise ValueError("Duplicate grid modes are not allowed")

    for name, rate in (
        ("Fee", fee_rate),
        ("Slippage", slippage_rate),
    ):
        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not isfinite(rate)
            or not 0 <= rate < 1
        ):
            raise ValueError(f"{name} rate must be between 0 and 1")

    return normalized_pairs, widths, counts, mode_list


def run_binance_grid_optimizer(
    symbols: Iterable[str],
    interval: str = "1h",
    candle_limit: int = 500,
    initial_capital: float = 500.0,
    range_widths_percent: Iterable[float] = DEFAULT_RANGE_WIDTHS_PERCENT,
    grid_counts: Iterable[int] = DEFAULT_GRID_COUNTS,
    modes: Iterable[str] = DEFAULT_MODES,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> dict[str, Any]:
    """Test multiple Binance Spot Grid configurations for USDT pairs.

    Each range is centered on the first completed candle's closing price.
    Range width is the total percentage width around that price.

    Example:
        Starting price = 100
        Range width = 20%
        Lower price = 90
        Upper price = 110

    Candles are fetched once per pair and reused across all configurations.
    """

    pair_list, widths, counts, mode_list = _validate_options(
        symbols=symbols,
        interval=interval,
        candle_limit=candle_limit,
        initial_capital=initial_capital,
        range_widths_percent=range_widths_percent,
        grid_counts=grid_counts,
        modes=modes,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
    )

    configurations = [
        {
            "range_width_percent": width,
            "grid_count": count,
            "mode": mode,
        }
        for width in widths
        for count in counts
        for mode in mode_list
    ]

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

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

            starting_price = float(completed_candles[0]["close"])

        except Exception as error:
            errors.append({
                "symbol": symbol,
                "error": str(error),
            })
            continue

        for configuration in configurations:
            width = configuration["range_width_percent"]

            lower_price = starting_price * (1 - width / 200)
            upper_price = starting_price * (1 + width / 200)

            try:
                result = backtest_binance_spot_grid(
                    completed_candles,
                    initial_capital=initial_capital,
                    lower_price=lower_price,
                    upper_price=upper_price,
                    grid_count=configuration["grid_count"],
                    mode=configuration["mode"],
                    fee_rate=fee_rate,
                    slippage_rate=slippage_rate,
                )

                result.update({
                    "exchange": "binance",
                    "symbol": symbol,
                    "binance_symbol": binance_symbol,
                    "interval": interval,
                    "range_width_percent": width,
                    "first_candle_time": completed_candles[0]["open_time"],
                    "last_candle_time": completed_candles[-1]["open_time"],
                    "completed_candle_count": len(completed_candles),
                    "outperformance_vs_hold_percent": (
                        result["roi_percent"]
                        - result["buy_and_hold_roi_percent"]
                    ),
                })

                results.append(result)

            except Exception as error:
                errors.append({
                    "symbol": symbol,
                    "configuration": configuration.copy(),
                    "error": str(error),
                })

    # Rank by historical ROI, highest first.
    results.sort(
        key=lambda item: item["roi_percent"],
        reverse=True,
    )

    for rank, result in enumerate(results, start=1):
        result["rank"] = rank

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
        "ranking_method": "historical ROI descending",
        "research_only": True,
    }
