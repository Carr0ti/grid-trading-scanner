
"""Evaluate multi-timeframe Spot Grid market suitability."""

from __future__ import annotations

from math import isfinite
from typing import Any


TIMEFRAMES = ("1h", "4h", "1d")

# Initial research defaults only.
# These values must be calibrated with historical backtests.
DEFAULT_THRESHOLDS = {
    "trend_efficiency": 0.55,
    "range_efficiency": 0.35,
    "minimum_atr_percent": {
        "1h": 0.05,
        "4h": 0.10,
        "1d": 0.25,
    },
    "maximum_atr_percent": {
        "1h": 2.0,
        "4h": 4.0,
        "1d": 8.0,
    },
}


def _validate_metrics(
    metrics_by_timeframe: dict[str, dict[str, Any]],
) -> None:
    """Validate the required metrics for all timeframes."""
    missing = [
        timeframe
        for timeframe in TIMEFRAMES
        if timeframe not in metrics_by_timeframe
    ]

    if missing:
        raise ValueError(
            f"Missing timeframes: {', '.join(missing)}"
        )

    for timeframe in TIMEFRAMES:
        metrics = metrics_by_timeframe[timeframe]

        for field in ("atr_percent", "path_efficiency"):
            value = metrics.get(field)

            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Invalid {field} for {timeframe}"
                )

            if not isfinite(value):
                raise ValueError(
                    f"Non-finite {field} for {timeframe}"
                )

            if value < 0:
                raise ValueError(
                    f"Negative {field} for {timeframe}"
                )

        if metrics["path_efficiency"] > 1:
            raise ValueError(
                f"Path efficiency cannot exceed 1 for {timeframe}"
            )


def evaluate_grid_suitability(
    metrics_by_timeframe: dict[str, dict[str, Any]],
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a market using 1h, 4h, and 1d analysis metrics."""
    _validate_metrics(metrics_by_timeframe)

    rules = DEFAULT_THRESHOLDS if thresholds is None else thresholds

    required_rules = (
        "trend_efficiency",
        "range_efficiency",
        "minimum_atr_percent",
        "maximum_atr_percent",
    )

    for rule in required_rules:
        if rule not in rules:
            raise ValueError(f"Missing threshold: {rule}")

    trend_limit = rules["trend_efficiency"]
    range_limit = rules["range_efficiency"]
    minimum_atr = rules["minimum_atr_percent"]
    maximum_atr = rules["maximum_atr_percent"]

    if not 0 <= range_limit < trend_limit <= 1:
        raise ValueError("Invalid trend or range thresholds")

    for timeframe in TIMEFRAMES:
        if timeframe not in minimum_atr or timeframe not in maximum_atr:
            raise ValueError(
                f"Missing ATR thresholds for {timeframe}"
            )

        if (
            not isfinite(minimum_atr[timeframe])
            or not isfinite(maximum_atr[timeframe])
            or minimum_atr[timeframe] < 0
            or maximum_atr[timeframe] <= minimum_atr[timeframe]
        ):
            raise ValueError(
                f"Invalid ATR thresholds for {timeframe}"
            )

    reasons = []

    too_volatile = [
        timeframe
        for timeframe in TIMEFRAMES
        if metrics_by_timeframe[timeframe]["atr_percent"]
        > maximum_atr[timeframe]
    ]

    too_quiet = [
        timeframe
        for timeframe in TIMEFRAMES
        if metrics_by_timeframe[timeframe]["atr_percent"]
        < minimum_atr[timeframe]
    ]

    strong_trend = (
        metrics_by_timeframe["4h"]["path_efficiency"]
        >= trend_limit
        and metrics_by_timeframe["1d"]["path_efficiency"]
        >= trend_limit
    )

    potential_range = (
        metrics_by_timeframe["4h"]["path_efficiency"]
        <= range_limit
        and metrics_by_timeframe["1d"]["path_efficiency"]
        <= range_limit
    )

    if too_volatile:
        status = "TOO_RISKY"
        reasons.append(
            "ATR volatility exceeds the configured limit: "
            + ", ".join(too_volatile)
        )

    elif strong_trend:
        status = "TREND_TOO_STRONG"
        reasons.append(
            "Both 4h and 1d show strong directional movement."
        )

    elif len(too_quiet) == len(TIMEFRAMES):
        status = "VOLATILITY_TOO_LOW"
        reasons.append(
            "ATR volatility is below the configured minimum "
            "on all timeframes."
        )

    elif potential_range and not too_quiet:
        status = "POTENTIAL_GRID_CANDIDATE"
        reasons.append(
            "Both 4h and 1d show relatively low directional "
            "persistence, with sufficient measured volatility."
        )

    else:
        status = "NO_TRADE"
        reasons.append(
            "Timeframes do not show a sufficiently clear "
            "grid-suitable condition."
        )

    if too_quiet and status != "VOLATILITY_TOO_LOW":
        reasons.append(
            "Low volatility detected on: "
            + ", ".join(too_quiet)
        )

    return {
        "status": status,
        "reasons": reasons,
        "timeframes": {
            timeframe: {
                "atr_percent": metrics_by_timeframe[timeframe][
                    "atr_percent"
                ],
                "path_efficiency": metrics_by_timeframe[timeframe][
                    "path_efficiency"
                ],
            }
            for timeframe in TIMEFRAMES
        },
    }
