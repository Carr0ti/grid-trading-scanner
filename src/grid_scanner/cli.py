
"""Command-line entry point for the liquidity scanner."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from grid_scanner.exchanges import SUPPORTED_EXCHANGES, scan_exchange


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan liquid USDT Spot markets."
    )

    parser.add_argument(
        "--exchanges",
        nargs="+",
        choices=SUPPORTED_EXCHANGES,
        default=list(SUPPORTED_EXCHANGES),
    )

    parser.add_argument("--limit", type=int, default=10)

    parser.add_argument(
        "--min-volume",
        type=float,
        default=5_000_000,
    )

    parser.add_argument(
        "--max-spread",
        type=float,
        default=0.15,
    )

    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional path for a CSV report.",
    )

    args = parser.parse_args()

    all_rows = []

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

        selected_rows = rows[:max(args.limit, 0)]
        all_rows.extend(selected_rows)

        print("Symbol       Last price       24h quote volume      Spread")

        for row in selected_rows:
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

    if args.csv:
        output_path = Path(args.csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "exchange",
            "symbol",
            "last",
            "quote_volume_usdt",
            "bid",
            "ask",
            "spread_percent",
        ]

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"\nCSV report saved to: {output_path}")


if __name__ == "__main__":
    main()
