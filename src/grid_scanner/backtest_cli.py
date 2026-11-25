
"""Command-line interface for historical Spot Grid backtesting."""

from __future__ import annotations

import argparse

from grid_scanner.backtest_report import (
    build_backtest_report_row,
    write_backtest_csv_report,
)
from grid_scanner.backtest_runner import (
    run_binance_spot_grid_backtest,
)
from grid_scanner.batch_backtest import (
    run_binance_spot_grid_batch_backtest,
)


def add_backtest_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "symbols",
        nargs="+",
        help="One or more trading pairs, for example BTC/USDT ETH/USDT.",
    )
    parser.add_argument(
        "--interval",
        choices=("1h", "4h", "1d"),
        default="1h",
        help="Historical candle interval.",
    )
    parser.add_argument(
        "--candles",
        type=int,
        default=500,
        help="Number of historical candles to request.",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=500.0,
        help="Starting portfolio value in USDT for each pair.",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=0.5,
        help="Grid spacing percentage.",
    )
    parser.add_argument(
        "--levels",
        type=int,
        default=10,
        help="Grid levels on each side.",
    )
    parser.add_argument(
        "--fee",
        type=float,
        default=0.1,
        help="Trading fee percentage per fill.",
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=0.05,
        help="Slippage percentage per fill.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for saving the backtest CSV report.",
    )


def print_single_result(
    result: dict,
    fee_percent: float,
    slippage_percent: float,
) -> None:
    print("=" * 60)
    print("BINANCE SPOT GRID HISTORICAL BACKTEST")
    print("=" * 60)

    print(f"\nPair: {result['symbol']}")
    print(f"Interval: {result['interval']}")
    print(f"Completed candles: {result['candle_count']}")
    print(f"Starting capital: {result['initial_capital']:.2f} USDT")
    print(f"Grid center: {result['grid_center']:.8f}")
    print(f"Grid spacing: {result['grid_spacing_percent']:.3f}%")
    print(f"Levels each side: {result['levels_each_side']}")
    print(f"Trading fee: {fee_percent:.3f}%")
    print(f"Slippage: {slippage_percent:.3f}%")

    print("\n=== GRID STRATEGY RESULTS ===")
    print(f"Final price: {result['final_price']:.8f}")
    print(f"Final equity: {result['final_equity']:.4f} USDT")
    print(f"Net profit: {result['net_profit']:.4f} USDT")
    print(f"ROI: {result['roi_percent']:.3f}%")
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
    print(f"Total fees: {result['total_fees']:.4f} USDT")

    print("\n=== BUY-AND-HOLD BENCHMARK ===")
    print(
        "Final equity: "
        f"{result['buy_and_hold_final_equity']:.4f} USDT"
    )
    print(
        "ROI: "
        f"{result['buy_and_hold_roi_percent']:.3f}%"
    )

    difference = (
        result["roi_percent"]
        - result["buy_and_hold_roi_percent"]
    )

    print(f"\nGrid ROI minus hold ROI: {difference:+.3f} percentage points")


def print_batch_result(batch: dict) -> None:
    print("=" * 70)
    print("BINANCE SPOT GRID BATCH BACKTEST")
    print("=" * 70)

    print(f"\nInterval: {batch['interval']}")
    print(f"Requested pairs: {batch['requested_count']}")
    print(f"Successful: {batch['success_count']}")
    print(f"Failed: {batch['failure_count']}")

    if batch["results"]:
        print("\n=== SUCCESSFUL BACKTESTS ===")
        print(
            f"{'PAIR':<16}"
            f"{'GRID ROI':>12}"
            f"{'HOLD ROI':>12}"
            f"{'DRAWDOWN':>12}"
            f"{'FILLS':>9}"
        )

        for result in batch["results"]:
            print(
                f"{result['symbol']:<16}"
                f"{result['roi_percent']:>11.3f}%"
                f"{result['buy_and_hold_roi_percent']:>11.3f}%"
                f"{result['maximum_drawdown_percent']:>11.3f}%"
                f"{result['trade_count']:>9}"
            )

    if batch["errors"]:
        print("\n=== FAILED PAIRS ===")

        for error in batch["errors"]:
            print(f"{error['symbol']}: {error['error']}")

    print(
        "\nResearch only. Historical results do not guarantee future returns."
    )
    print("No trades were placed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backtest one or more Binance Spot Grid pairs "
            "using historical candles."
        )
    )
    add_backtest_arguments(parser)

    args = parser.parse_args()

    settings = {
        "interval": args.interval,
        "candle_limit": args.candles,
        "initial_capital": args.capital,
        "grid_spacing_percent": args.spacing,
        "levels_each_side": args.levels,
        "fee_rate": args.fee / 100,
        "slippage_rate": args.slippage / 100,
    }

    if len(args.symbols) == 1:
        try:
            result = run_binance_spot_grid_backtest(
                symbol=args.symbols[0],
                **settings,
            )
        except (ValueError, RuntimeError) as error:
            parser.error(str(error))
            return

        print_single_result(
            result,
            args.fee,
            args.slippage,
        )
        report_results = [result]

    else:
        batch = run_binance_spot_grid_batch_backtest(
            symbols=args.symbols,
            **settings,
        )

        print_batch_result(batch)
        report_results = batch["results"]

    if args.output:
        rows = [
            build_backtest_report_row(result)
            for result in report_results
        ]

        saved_path = write_backtest_csv_report(
            rows,
            args.output,
        )
        print(f"\nCSV report saved to: {saved_path}")

    if len(args.symbols) == 1:
        print(
            "\nResearch only. Historical results do not guarantee future returns."
        )
        print("No trades were placed.")


if __name__ == "__main__":
    main()
