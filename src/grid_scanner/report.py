
"""Prepare Spot Grid research results for CSV reporting."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


TIMEFRAMES = ("1h", "4h", "1d")

REPORT_FIELDS = [
    "exchange",
    "symbol",
    "last",
    "quote_volume_usdt",
    "bid",
    "ask",
    "spread_percent",
    "status",
    "reasons",
    "candle_count_1h",
    "atr_1h_percent",
    "path_efficiency_1h",
    "candle_count_4h",
    "atr_4h_percent",
    "path_efficiency_4h",
    "candle_count_1d",
    "atr_1d_percent",
    "path_efficiency_1d",
]


def build_report_rows(
    research_results: list[dict[str, Any]],
    market_data: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Combine market data and research into flat CSV-ready rows."""
    markets = {
        item["symbol"]: item
        for item in (market_data or [])
        if isinstance(item, dict) and "symbol" in item
    }

    rows = []

    for result in research_results:
        if not isinstance(result, dict):
            continue

        symbol = result.get("symbol", "UNKNOWN")
        market = markets.get(symbol, {})

        row = {
            "exchange": result.get(
                "exchange",
                market.get("exchange", "binance"),
            ),
            "symbol": symbol,
            "last": market.get("last"),
            "quote_volume_usdt": market.get("quote_volume_usdt"),
            "bid": market.get("bid"),
            "ask": market.get("ask"),
            "spread_percent": market.get("spread_percent"),
            "status": result.get("status", "UNKNOWN"),
            "reasons": " | ".join(
                str(reason)
                for reason in result.get("reasons", [])
            ),
        }

        candle_counts = result.get("candle_counts", {})
        timeframe_data = result.get("timeframes", {})

        for timeframe in TIMEFRAMES:
            metrics = timeframe_data.get(timeframe, {})

            row[f"candle_count_{timeframe}"] = (
                candle_counts.get(timeframe)
            )
            row[f"atr_{timeframe}_percent"] = (
                metrics.get("atr_percent")
            )
            row[f"path_efficiency_{timeframe}"] = (
                metrics.get("path_efficiency")
            )

        rows.append(row)

    return rows


def write_csv_report(
    rows: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """Write report rows to a CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=REPORT_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    return path
