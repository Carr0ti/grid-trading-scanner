
"""Build and save CSV reports for Spot Grid parameter sweeps."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from grid_scanner.backtest_report import (
    BACKTEST_REPORT_FIELDS,
    build_backtest_report_row,
)


PARAMETER_SWEEP_REPORT_FIELDS = [
    "configuration_number",
    *BACKTEST_REPORT_FIELDS,
]


def build_parameter_sweep_report_rows(
    sweep_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert parameter-sweep results into CSV-ready rows."""
    if not isinstance(sweep_result, dict):
        raise ValueError("Sweep result must be a dictionary")

    results = sweep_result.get("results")

    if not isinstance(results, list):
        raise ValueError("Sweep results must be a list")

    rows = []

    for index, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            raise ValueError(
                "Every sweep result must be a dictionary"
            )

        row = build_backtest_report_row(result)
        row["configuration_number"] = index

        rows.append(row)

    return rows


def write_parameter_sweep_csv_report(
    rows: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """Write parameter-sweep rows to a CSV file."""
    if not isinstance(rows, list):
        raise ValueError("Report rows must be a list")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(
                "Every report row must be a dictionary"
            )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=PARAMETER_SWEEP_REPORT_FIELDS,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)

    return path
