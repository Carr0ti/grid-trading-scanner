
"""Command-line entry point for Spot Grid research."""

from __future__ import annotations

import argparse

from grid_scanner.pipeline import run_binance_pipeline
from grid_scanner.report import build_report_rows, write_csv_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Binance Spot Grid market research."
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
        "--candle-limit",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="reports/binance-grid-research.csv",
        help="Output CSV report path.",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("BINANCE SPOT GRID RESEARCH")
    print("=" * 60)

    print("\nScanning liquid Binance Spot markets...")

    results = run_binance_pipeline(
        limit=args.limit,
        minimum_quote_volume=args.min_volume,
        maximum_spread_percent=args.max_spread,
        candle_limit=args.candle_limit,
    )

    if not results:
        raise SystemExit(
            "\nNo markets passed the initial liquidity filters."
        )

    report_rows = build_report_rows(results)

    print(f"\nResearch completed: {len(results)} pairs")
    print("\n=== RESEARCH RESULTS ===")

    for result in results:
        symbol = result.get("symbol", "UNKNOWN")
        status = result.get("status", "UNKNOWN")
        volume = result.get("quote_volume_usdt")

        volume_text = (
            f"{volume:,.0f} USDT"
            if isinstance(volume, (int, float))
            else "n/a"
        )

        print(
            f"\n{symbol} | {status}"
            f"\n24h volume: {volume_text}"
        )

        for reason in result.get("reasons", []):
            print(f"Reason: {reason}")

    counts = {}

    for result in results:
        status = result.get("status", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1

    print("\n=== STATUS SUMMARY ===")

    for status, count in sorted(counts.items()):
        print(f"{status}: {count}")

    output_path = write_csv_report(
        report_rows,
        args.csv,
    )

    print(f"\nCSV report saved to: {output_path}")
    print("\nResearch finished. No trades were placed.")


if __name__ == "__main__":
    main()
