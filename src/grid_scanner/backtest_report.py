
"""Build and save CSV reports for historical Spot Grid backtests."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


BACKTEST_REPORT_FIELDS = [
    "exchange",
    "symbol",
    "binance_symbol",
    "interval",
    "first_candle_time",
    "last_candle_time",
    "candle_count",
    "strategy",
    "initial_capital",
    "grid_center",
    "grid_spacing_percent",
    "levels_each_side",
    "fee_rate",
    "slippage_rate",
    "final_price",
    "final_cash",
    "final_base_asset",
    "final_equity",
    "net_profit",
    "roi_percent",
    "maximum_drawdown_percent",
    "trade_count",
    "buy_count",
    "sell_count",
    "ambiguous_candles_skipped",
    "total_fees",
    "buy_and_hold_final_equity",
    "buy_and_hold_roi_percent",
    "grid_roi_minus_hold_roi_percent",
]


def build_backtest_report_row(
    result: dict[str, Any],
) -> dict[str, Any]:
    """Convert one backtest result into a flat CSV-ready row."""
    if not isinstance(result, dict):
        raise ValueError("Backtest result must be a dictionary")

    row = {
        field: result.get(field)
        for field in BACKTEST_REPORT_FIELDS
    }

    grid_roi = result.get("roi_percent")
    hold_roi = result.get("buy_and_hold_roi_percent")

    if (
        isinstance(grid_roi, (int, float))
        and isinstance(hold_roi, (int, float))
    ):
        row["grid_roi_minus_hold_roi_percent"] = (
            grid_roi - hold_roi
        )

    return row


def write_backtest_csv_report(
    rows: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """Write one or more backtest results to a CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=BACKTEST_REPORT_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    return path
