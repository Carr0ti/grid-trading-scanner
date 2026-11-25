
"""Run multi-timeframe Spot Grid research on Binance pairs."""

from __future__ import annotations

from typing import Any

from grid_scanner.analyzer import analyze_candles
from grid_scanner.history import fetch_binance_klines
from grid_scanner.suitability import (
    TIMEFRAMES,
    evaluate_grid_suitability,
)


DEFAULT_CANDLE_LIMIT = 500
MINIMUM_CANDLES = 50


def to_binance_symbol(symbol: str) -> str:
    """Convert a CCXT symbol such as BTC/USDT to BTCUSDT."""
    if not isinstance(symbol, str):
        raise ValueError("Symbol must be a string")

    parts = symbol.split("/")

    if (
        len(parts) != 2
        or not all(parts)
        or any(not part.isalnum() for part in parts)
    ):
        raise ValueError(
            "Expected a Spot symbol such as BTC/USDT"
        )

    return "".join(parts).upper()


def research_pair(
    symbol: str,
    candle_limit: int = DEFAULT_CANDLE_LIMIT,
) -> dict[str, Any]:
    """Analyze one Binance Spot pair across three timeframes."""
    if not MINIMUM_CANDLES <= candle_limit <= 1000:
        raise ValueError(
            f"Candle limit must be between {MINIMUM_CANDLES} and 1000"
        )

    binance_symbol = to_binance_symbol(symbol)

    timeframe_metrics = {}
    candle_counts = {}

    for timeframe in TIMEFRAMES:
        candles = fetch_binance_klines(
            binance_symbol,
            timeframe,
            limit=candle_limit,
        )

        if len(candles) < MINIMUM_CANDLES:
            raise ValueError(
                f"Insufficient {timeframe} candles for {symbol}: "
                f"received {len(candles)}, "
                f"need at least {MINIMUM_CANDLES}"
            )

        timeframe_metrics[timeframe] = analyze_candles(
            candles,
            lookback=50,
        )

        candle_counts[timeframe] = len(candles)

    suitability = evaluate_grid_suitability(
        timeframe_metrics
    )

    return {
        "exchange": "binance",
        "symbol": symbol,
        "status": suitability["status"],
        "reasons": suitability["reasons"],
        "candle_counts": candle_counts,
        "timeframes": suitability["timeframes"],
    }


def research_pairs(
    pairs: list[dict[str, Any]],
    candle_limit: int = DEFAULT_CANDLE_LIMIT,
) -> list[dict[str, Any]]:
    """Research multiple scanner candidates independently."""
    results = []

    for pair in pairs:
        symbol = pair.get("symbol", "UNKNOWN")

        try:
            result = research_pair(
                symbol,
                candle_limit=candle_limit,
            )

        except Exception as exc:
            result = {
                "exchange": "binance",
                "symbol": symbol,
                "status": "ANALYSIS_FAILED",
                "reasons": [
                    f"{type(exc).__name__}: {exc}"
                ],
                "candle_counts": {},
                "timeframes": {},
            }

        results.append(result)

    priority = {
        "POTENTIAL_GRID_CANDIDATE": 0,
        "NO_TRADE": 1,
        "TREND_TOO_STRONG": 2,
        "VOLATILITY_TOO_LOW": 3,
        "TOO_RISKY": 4,
        "ANALYSIS_FAILED": 5,
    }

    return sorted(
        results,
        key=lambda item: (
            priority.get(item["status"], 99),
            item["symbol"],
        ),
    )
