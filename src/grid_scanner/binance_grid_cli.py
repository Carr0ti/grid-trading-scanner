
"""Command-line interface for Binance-style Manual Spot Grid backtests."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from grid_scanner.binance_grid_runner import (
    DEFAULT_CANDLE_LIMIT,
    DEFAULT_INTERVAL,
    run_binance_manual_grid_backtest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backtest Binance Manual Spot Grid settings "
            "using historical Binance candles."
        )
    )

    parser.add_argument(
        "symbol",
        help="Trading pair, for example BTC/USDT.",
    )
    parser.add_argument(
        "--lower",
        type=float,
        required=True,
        help="Grid lower price.",
    )
    parser.add_argument(
        "--upper",
        type=float,
        required=True,
        help="Grid upper price.",
    )
    parser.add_argument(
        "--grids",
        type=int,
        default=10,
        help="Number of grid intervals (default: 10).",
    )
    parser.add_argument(
        "--mode",
        choices=("arithmetic", "geometric"),
        default="arithmetic",
        help="Grid mode (default: arithmetic).",
    )
    parser.add_argument(
        "--interval",
        choices=("1h", "4h", "1d"),
        default=DEFAULT_INTERVAL,
        help="Historical candle interval.",
    )
    parser.add_argument(
        "--candles",
        type=int,
        default=DEFAULT_CANDLE_LIMIT,
        help="Number of historical candles (default: 500).",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=500.0,
        help="Starting portfolio value (default: 500).",
    )
    parser.add_argument(
        "--fee",
        type=float,
        default=0.1,
        help="Trading fee percentage per fill (default: 0.1).",
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=0.05,
        help="Slippage percentage per fill (default: 0.05).",
    )
    parser.add_argument(
        "--output",
        help="Optional CSV report output path.",
    )

    return parser


def print_result(
    result: dict[str, Any],
    fee_percent: float,
    slippage_percent: float,
) -> None:
    print("=" * 64)
    print("BINANCE MANUAL SPOT GRID BACKTEST")
    print("=" * 64)

    print(f"\nPair: {result['symbol']}")
    print(f"Mode: {result['mode'].upper()}")
    print(f"Interval: {result['interval']}")
    print(f"Completed candles: {result['completed_candle_count']}")
    print(f"Starting capital: {result['initial_capital']:.4f}")
    print(f"Starting price: {result['starting_price']:.8f}")
    print(f"Grid range: {result['lower_price']:.8f} - "
          f"{result['upper_price']:.8f}")
    print(f"Grid intervals: {result['grid_count']}")
    print(f"Trading fee: {fee_percent:.4f}%")
    print(f"Slippage: {slippage_percent:.4f}%")

    print("\n=== GRID PRICE LEVELS ===")
    for index, price in enumerate(result["grid_prices"]):
        print(f"Level {index:>3}: {price:.10f}")

    print("\n=== GRID RESULTS ===")
    print(f"Final price: {result['final_price']:.8f}")
    print(f"Final equity: {result['final_equity']:.4f}")
    print(f"Net profit/loss: {result['net_profit']:.4f}")
    print(f"Grid ROI: {result['roi_percent']:.3f}%")
    print(
        "Maximum drawdown: "
        f"{result['maximum_drawdown_percent']:.3f}%"
    )
    print(f"Total fills: {result['trade_count']}")
    print(f"Buy fills: {result['buy_count']}")
    print(f"Sell fills: {result['sell_count']}")
    print(
        "Ambiguous candles skipped: "
        f"{result['ambiguous_candles_skipped']}"
    )
    print(f"Total fees: {result['total_fees']:.6f}")

    print("\n=== BUY AND HOLD COMPARISON ===")
    print(
        "Buy-and-hold final equity: "
        f"{result['buy_and_hold_final_equity']:.4f}"
    )
    print(
        "Buy-and-hold ROI: "
        f"{result['buy_and_hold_roi_percent']:.3f}%"
    )

    difference = (
        result["roi_percent"]
        - result["buy_and_hold_roi_percent"]
    )
    print(f"Grid minus hold ROI: {difference:+.3f} percentage points")

    print("\n=== EXECUTION NOTES ===")
    print("This is an OHLC candle-based approximation.")
    print("It does not reproduce Binance's exact order-book fills.")
    print("Research only. No trades were placed.")


def write_csv_report(
    result: dict[str, Any],
    output_path: str,
) -> Path:
    fields = [
        "exchange",
        "symbol",
        "binance_symbol",
        "interval",
        "first_candle_time",
        "last_candle_time",
        "completed_candle_count",
        "mode",
        "initial_capital",
        "starting_price",
        "lower_price",
        "upper_price",
        "grid_count",
        "fee_rate",
        "slippage_rate",
        "final_price",
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
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerow(result)

    return path


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_binance_manual_grid_backtest(
            symbol=args.symbol,
            lower_price=args.lower,
            upper_price=args.upper,
            grid_count=args.grids,
            mode=args.mode,
            interval=args.interval,
            candle_limit=args.candles,
            initial_capital=args.capital,
            fee_rate=args.fee / 100,
            slippage_rate=args.slippage / 100,
        )
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
        return

    print_result(
        result,
        fee_percent=args.fee,
        slippage_percent=args.slippage,
    )

    if args.output:
        saved_path = write_csv_report(result, args.output)
        print(f"\nCSV report saved to: {saved_path}")


if __name__ == "__main__":
    main()
