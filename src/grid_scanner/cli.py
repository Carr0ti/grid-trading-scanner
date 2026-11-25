
"""Command-line entry point for the initial liquidity scanner."""

from __future__ import annotations

import argparse

from grid_scanner.exchanges import SUPPORTED_EXCHANGES, scan_exchange


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan liquid USDT Spot markets across supported exchanges."
    )

    parser.add_argument(
        "--exchanges",
        nargs="+",
        choices=SUPPORTED_EXCHANGES,
        default=list(SUPPORTED_EXCHANGES),
        help="Exchanges to scan (default: all supported exchanges).",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Rows to show per exchange.",
    )

    parser.add_argument(
        "--min-volume",
        type=float,
        default=5_000_000,
        help="Minimum 24-hour quote volume in USDT.",
    )

    parser.add_argument(
        "--max-spread",
        type=float,
        default=0.15,
        help="Maximum bid/ask spread in percent.",
    )

    args = parser.parse_args()

    for exchange_id in args.exchanges:
        print(f"\n=== {exchange_id.upper()} ===")

        try:
            rows = scan_exchange(
                exchange_id,
                minimum_quote_volume=args.min_volume,
                maximum_spread_percent=args.max_spread,
            )

        except Exception as exc:
            print(
                f"Could not scan {exchange_id}: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        if not rows:
            print("No markets passed the current filters.")
            continue

        print("Symbol       Last price       24h quote volume      Spread")

        for row in rows[: max(args.limit, 0)]:
            last = row["last"]

            last_text = (
                f"{last:.8g}"
                if isinstance(last, (int, float))
                else "n/a"
            )

            volume_text = f"{row['quote_volume_usdt']:,.0f}"

            print(
                f"{row['symbol']:<12} {last_text:>14} "
                f"{volume_text:>20} "
                f"{row['spread_percent']:>9.4f}%"
            )


if __name__ == "__main__":
    main()
