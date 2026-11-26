
"""Command-line interface for Binance Spot Grid optimization."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from grid_scanner.binance_grid_optimizer import (
    DEFAULT_GRID_COUNTS,
    DEFAULT_MODES,
    DEFAULT_RANGE_WIDTHS_PERCENT,
    run_binance_grid_optimizer,
)


def parse_float_options(value: str) -> list[float]:
    """Parse comma-separated floating-point options."""
    parts = value.split(",")

    if not parts or any(not item.strip() for item in parts):
        raise argparse.ArgumentTypeError(
            "Options cannot contain empty values."
        )

    try:
        return [float(item.strip()) for item in parts]
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Options must be comma-separated numbers."
        ) from error


def parse_integer_options(value: str) -> list[int]:
    """Parse comma-separated integer options."""
    parts = value.split(",")

    if not parts or any(not item.strip() for item in parts):
        raise argparse.ArgumentTypeError(
            "Options cannot contain empty values."
        )

    try:
        return [int(item.strip()) for item in parts]
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Options must be comma-separated whole numbers."
        ) from error


def parse_mode_options(value: str) -> list[str]:
    """Parse comma-separated grid modes."""
    parts = [
        item.strip().lower()
        for item in value.split(",")
    ]

    if not parts or any(not item for item in parts):
        raise argparse.ArgumentTypeError(
            "Modes cannot contain empty values."
        )

    if any(
        mode not in ("arithmetic", "geometric")
        for mode in parts
    ):
        raise argparse.ArgumentTypeError(
            "Modes must be arithmetic or geometric."
        )

    return parts


def build_parser() -> argparse.ArgumentParser:
    """Create the optimizer command parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Optimize Binance Spot Grid configurations "
            "using historical market data."
        )
    )

    parser.add_argument(
        "symbols",
        nargs="+",
        help="USDT pairs, for example BTC/USDT ETH/USDT.",
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
        help="Number of historical candles (default: 500).",
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=500.0,
        help="Starting capital in USDT for each pair.",
    )

    parser.add_argument(
        "--widths",
        type=parse_float_options,
        default=list(DEFAULT_RANGE_WIDTHS_PERCENT),
        help="Comma-separated total grid range widths in percent.",
    )

    parser.add_argument(
        "--grids",
        type=parse_integer_options,
        default=list(DEFAULT_GRID_COUNTS),
        help="Comma-separated grid interval counts.",
    )

    parser.add_argument(
        "--modes",
        type=parse_mode_options,
        default=list(DEFAULT_MODES),
        help="Comma-separated modes: arithmetic,geometric.",
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
        default="binance-grid-optimizer.csv",
        help="CSV report path.",
    )

    return parser


def print_optimizer_results(optimizer: dict) -> None:
    """Print ranked optimizer results."""
    print("=" * 110)
    print("BINANCE SPOT GRID PARAMETER OPTIMIZER")
    print("=" * 110)

    print(f"\nInterval: {optimizer['interval']}")
    print(f"Requested pairs: {optimizer['requested_pairs']}")
    print(
        "Configurations per pair: "
        f"{optimizer['configurations_per_pair']}"
    )
    print(f"Total requested tests: {optimizer['requested_tests']}")
    print(f"Successful tests: {optimizer['success_count']}")
    print(f"Failed tests: {optimizer['failure_count']}")

    if optimizer["results"]:
        print("\n=== RANKED CONFIGURATIONS ===")
        print(
            f"{'RANK':>5}"
            f"{'PAIR':<13}"
            f"{'MODE':<12}"
            f"{'WIDTH':>9}"
            f"{'GRIDS':>8}"
            f"{'GRID ROI':>12}"
            f"{'HOLD ROI':>12}"
            f"{'DIFFERENCE':>13}"
            f"{'DRAWDOWN':>12}"
            f"{'FILLS':>8}"
        )

        for result in optimizer["results"]:
            print(
                f"{result['rank']:>5}"
                f"{result['symbol']:<13}"
                f"{result['mode']:<12}"
                f"{result['range_width_percent']:>8.2f}%"
                f"{result['grid_count']:>8}"
                f"{result['roi_percent']:>11.3f}%"
                f"{result['buy_and_hold_roi_percent']:>11.3f}%"
                f"{result['outperformance_vs_hold_percent']:>+12.3f}%"
                f"{result['maximum_drawdown_percent']:>11.3f}%"
                f"{result['trade_count']:>8}"
            )

    if optimizer["errors"]:
        print("\n=== FAILED TESTS ===")

        for error in optimizer["errors"]:
            configuration = error.get("configuration")

            if configuration:
                print(
                    f"{error['symbol']} "
                    f"({configuration}): {error['error']}"
                )
            else:
                print(
                    f"{error['symbol']}: {error['error']}"
                )

    print("\n=== IMPORTANT NOTES ===")
    print("Ranking is based on historical ROI, not risk-adjusted returns.")
    print("A high historical ROI does not guarantee future profitability.")
    print("The backtest uses OHLC candle approximations.")
    print("It does not reproduce Binance's exact order-book execution.")
    print("Research only. No trades were placed.")


def write_optimizer_csv_report(
    optimizer: dict,
    output_path: str,
) -> Path:
    """Write ranked optimizer results to CSV."""
    fields = [
        "rank",
        "exchange",
        "symbol",
        "binance_symbol",
        "interval",
        "mode",
        "range_width_percent",
        "lower_price",
        "upper_price",
        "grid_count",
        "first_candle_time",
        "last_candle_time",
        "completed_candle_count",
        "initial_capital",
        "starting_price",
        "final_price",
        "final_equity",
        "net_profit",
        "roi_percent",
        "buy_and_hold_final_equity",
        "buy_and_hold_roi_percent",
        "outperformance_vs_hold_percent",
        "maximum_drawdown_percent",
        "trade_count",
        "buy_count",
        "sell_count",
        "ambiguous_candles_skipped",
        "total_fees",
        "fee_rate",
        "slippage_rate",
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
        writer.writerows(optimizer["results"])

    return path


def main(argv: list[str] | None = None) -> None:
    """Run the Binance Grid optimizer."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        optimizer = run_binance_grid_optimizer(
            symbols=args.symbols,
            interval=args.interval,
            candle_limit=args.candles,
            initial_capital=args.capital,
            range_widths_percent=args.widths,
            grid_counts=args.grids,
            modes=args.modes,
            fee_rate=args.fee / 100,
            slippage_rate=args.slippage / 100,
        )
    except (ValueError, TypeError) as error:
        parser.error(str(error))
        return

    print_optimizer_results(optimizer)

    saved_path = write_optimizer_csv_report(
        optimizer,
        args.output,
    )

    print(f"\nCSV report saved to: {saved_path}")


if __name__ == "__main__":
    main()
