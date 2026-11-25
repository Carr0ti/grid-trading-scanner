
"""Command-line interface for historical Spot Grid backtesting."""

from __future__ import annotations

import argparse

from grid_scanner.backtest_runner import (
    run_binance_spot_grid_backtest,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backtest a Binance Spot Grid using historical candles."
    )

    parser.add_argument(
        "symbol",
        help="Trading pair, for example BTC/USDT.",
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
        help="Starting portfolio value in USDT.",
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

    args = parser.parse_args()

    try:
        result = run_binance_spot_grid_backtest(
            symbol=args.symbol,
            interval=args.interval,
            candle_limit=args.candles,
            initial_capital=args.capital,
            grid_spacing_percent=args.spacing,
            levels_each_side=args.levels,
            fee_rate=args.fee / 100,
            slippage_rate=args.slippage / 100,
        )
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
        return

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
    print(f"Trading fee: {args.fee:.3f}%")
    print(f"Slippage: {args.slippage:.3f}%")

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

    print("\nResearch only. Historical results do not guarantee future returns.")
    print("No trades were placed.")


if __name__ == "__main__":
    main()
