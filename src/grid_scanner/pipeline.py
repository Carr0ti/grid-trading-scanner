
"""Connect live market scanning with multi-timeframe research."""

from __future__ import annotations

from typing import Any

from grid_scanner.exchanges import scan_exchange
from grid_scanner.research import research_pairs


def run_binance_pipeline(
    limit: int = 10,
    minimum_quote_volume: float = 5_000_000,
    maximum_spread_percent: float = 0.15,
    candle_limit: int = 500,
) -> list[dict[str, Any]]:
    """Scan Binance markets and combine liquidity with research."""
    if limit < 1:
        raise ValueError("Limit must be at least 1")

    if minimum_quote_volume < 0:
        raise ValueError("Minimum quote volume cannot be negative")

    if maximum_spread_percent < 0:
        raise ValueError("Maximum spread cannot be negative")

    if not 50 <= candle_limit <= 1000:
        raise ValueError("Candle limit must be between 50 and 1000")

    candidates = scan_exchange(
        "binance",
        quote_currency="USDT",
        minimum_quote_volume=minimum_quote_volume,
        maximum_spread_percent=maximum_spread_percent,
    )

    selected = candidates[:limit]

    if not selected:
        return []

    research_results = research_pairs(
        selected,
        candle_limit=candle_limit,
    )

    market_by_symbol = {
        item["symbol"]: item
        for item in selected
    }

    combined_results = []

    for result in research_results:
        symbol = result.get("symbol", "UNKNOWN")
        market = market_by_symbol.get(symbol, {})

        combined = {
            **market,
            **result,
            "exchange": "binance",
        }

        combined_results.append(combined)

    return combined_results
