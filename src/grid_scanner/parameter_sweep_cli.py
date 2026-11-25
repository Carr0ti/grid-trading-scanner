
"""Command-line interface for Binance Spot Grid parameter sweeps."""

from __future__ import annotations

import argparse

from grid_scanner.parameter_sweep import (
    DEFAULT_LEVEL_OPTIONS,
    DEFAULT_SPACING_OPTIONS,
    run_binance_spot_grid_parameter_sweep,
)
from grid_scanner.parameter_sweep_report import (
    build_parameter_sweep_report_rows,
    write_parameter_sweep_csv_report,
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


def build_parser() -> argparse.ArgumentParser:
    """Create the parameter-sweep command parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare multiple Binance Spot Grid configurations "
            "using historical market data."
        )
    )

    parser.add_argument(
        "symbols",
        nargs="+",
        help="Trading pairs, for example BTC/USDT ETH/USDT.",
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
        "--spacings",
        type=parse_float_options,
        default=list(DEFAULT_SPACING_OPTIONS),
        help="Comma-separated grid spacing percentages.",
    )

    parser.add_argument(
        "--levels",
        type=parse_integer_options,
        default=list(DEFAULT_LEVEL_OPTIONS),
        help="Comma-separated grid levels on each side.",
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
        default="parameter-sweep.csv",
        help="CSV report path. Default: parameter-sweep.csv.",
    )

    return parser


def print_sweep_results(sweep: dict) -> None:
    """Print a comparison of all successful configurations."""
    print("=" * 100)
    print("BINANCE SPOT GRID PARAMETER SWEEP")
    print("=" * 100)

    print(f"\nInterval: {sweep['interval']}")
    print(f"Requested pairs: {sweep['requested_pairs']}")
    print(
        "Configurations per pair: "
        f"{sweep['configurations_per_pair']}"
    )
    print(f"Total tests: {sweep['requested_tests']}")
    print(f"Successful: {sweep['success_count']}")
    print(f"Failed: {sweep['failure_count']}")

    if sweep["results"]:
        print("\n=== CONFIGURATION COMPARISON ===")
        print(
            f"{'PAIR':<13}"
            f"{'SPACE':>9}"
            f"{'LEVELS':>9}"
            f"{'GRID ROI':>12}"
            f"{'HOLD ROI':>12}"
            f"{'DIFFERENCE':>13}"
            f"{'DRAWDOWN':>12}"
            f"{'FILLS':>8}"
        )

        for result in sweep["results"]:
            difference = (
                result["roi_percent"]
                - result["buy_and_hold_roi_percent"]
            )

            print(
                f"{result['symbol']:<13}"
                f"{result['grid_spacing_percent']:>8.3f}%"
                f"{result['levels_each_side']:>9}"
                f"{result['roi_percent']:>11.3f}%"
                f"{result['buy_and_hold_roi_percent']:>11.3f}%"
                f"{difference:>+12.3f}%"
                f"{result['maximum_drawdown_percent']:>11.3f}%"
                f"{result['trade_count']:>8}"
            )

    if sweep["errors"]:
        print("\n=== FAILED TESTS ===")

        for error in sweep["errors"]:
            configuration = error.get("configuration")

            if configuration:
                print(
                    f"{error['symbol']} "
                    f"({configuration}): {error['error']}"
                )
            else:
                print(f"{error['symbol']}: {error['error']}")

    print(
        "\nResearch only. Historical results do not guarantee future returns."
    )
    print("No trades were placed.")


def main(argv: list[str] | None = None) -> None:
    """Run the parameter-sweep command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        sweep = run_binance_spot_grid_parameter_sweep(
            symbols=args.symbols,
            interval=args.interval,
            candle_limit=args.candles,
            initial_capital=args.capital,
            spacing_options=args.spacings,
            level_options=args.levels,
            fee_rate=args.fee / 100,
            slippage_rate=args.slippage / 100,
        )
    except (ValueError, TypeError) as error:
        parser.error(str(error))
        return

    print_sweep_results(sweep)

    rows = build_parameter_sweep_report_rows(sweep)

    saved_path = write_parameter_sweep_csv_report(
        rows,
        args.output,
    )

    print(f"\nCSV report saved to: {saved_path}")


if __name__ == "__main__":
    main()
