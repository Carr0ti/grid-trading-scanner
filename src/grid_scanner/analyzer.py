
"""Calculate market conditions for Spot Grid research."""

from __future__ import annotations

from math import isfinite
from typing import Any


DEFAULT_ATR_PERIOD = 14
DEFAULT_LOOKBACK = 50


def _validate_candles(
    candles: list[dict[str, Any]],
    minimum_count: int,
) -> None:
    """Validate candle structure and price values."""
    if len(candles) < minimum_count:
        raise ValueError(
            f"At least {minimum_count} candles are required"
        )

    for candle in candles:
        for field in ("high", "low", "close"):
            value = candle.get(field)

            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid candle field: {field}")

            if not isfinite(value):
                raise ValueError(f"Non-finite candle field: {field}")

        if candle["high"] <= 0 or candle["low"] <= 0:
            raise ValueError("Candle prices must be positive")

        if candle["close"] <= 0:
            raise ValueError("Candle close must be positive")

        if candle["high"] < candle["low"]:
            raise ValueError("Candle high cannot be below its low")


def calculate_true_ranges(
    candles: list[dict[str, Any]],
) -> list[float]:
    """Calculate True Range for each candle."""
    _validate_candles(candles, 1)

    true_ranges = []

    for index, candle in enumerate(candles):
        high = candle["high"]
        low = candle["low"]

        if index == 0:
            true_range = high - low
        else:
            previous_close = candles[index - 1]["close"]

            true_range = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )

        true_ranges.append(true_range)

    return true_ranges


def calculate_atr(
    candles: list[dict[str, Any]],
    period: int = DEFAULT_ATR_PERIOD,
) -> float:
    """Calculate ATR using Wilder's smoothing method."""
    if period < 1:
        raise ValueError("ATR period must be at least 1")

    _validate_candles(candles, period)

    true_ranges = calculate_true_ranges(candles)

    atr = sum(true_ranges[:period]) / period

    for true_range in true_ranges[period:]:
        atr = (
            (atr * (period - 1)) + true_range
        ) / period

    return atr


def analyze_candles(
    candles: list[dict[str, Any]],
    atr_period: int = DEFAULT_ATR_PERIOD,
    lookback: int = DEFAULT_LOOKBACK,
) -> dict[str, float | int]:
    """Calculate volatility, range, and directional movement metrics."""
    if lookback < 2:
        raise ValueError("Lookback must be at least 2")

    required_count = max(atr_period, lookback)
    _validate_candles(candles, required_count)

    recent = candles[-lookback:]

    atr = calculate_atr(candles, atr_period)
    last_close = recent[-1]["close"]

    highest = max(candle["high"] for candle in recent)
    lowest = min(candle["low"] for candle in recent)

    first_close = recent[0]["close"]
    last_close = recent[-1]["close"]

    net_change = last_close - first_close

    total_path = sum(
        abs(recent[index]["close"] - recent[index - 1]["close"])
        for index in range(1, len(recent))
    )

    path_efficiency = (
        abs(net_change) / total_path
        if total_path > 0
        else 0.0
    )

    return {
        "candle_count": len(candles),
        "atr": atr,
        "atr_percent": (atr / last_close) * 100,
        "range_percent": ((highest - lowest) / lowest) * 100,
        "net_change_percent": (net_change / first_close) * 100,
        "path_efficiency": path_efficiency,
    }
