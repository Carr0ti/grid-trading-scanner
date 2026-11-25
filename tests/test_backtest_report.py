
import csv

import pytest

from grid_scanner.backtest_report import (
    BACKTEST_REPORT_FIELDS,
    build_backtest_report_row,
    write_backtest_csv_report,
)


def sample_backtest_result():
    return {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "binance_symbol": "BTCUSDT",
        "interval": "1h",
        "first_candle_time": 1700000000000,
        "last_candle_time": 1701800000000,
        "candle_count": 500,
        "strategy": "long_only_spot_grid",
        "initial_capital": 500.0,
        "grid_center": 60000.0,
        "grid_spacing_percent": 0.5,
        "levels_each_side": 10,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
        "final_price": 61000.0,
        "final_cash": 260.0,
        "final_base_asset": 0.004,
        "final_equity": 504.0,
        "net_profit": 4.0,
        "roi_percent": 0.8,
        "maximum_drawdown_percent": 2.5,
        "trade_count": 20,
        "buy_count": 10,
        "sell_count": 10,
        "ambiguous_candles_skipped": 2,
        "total_fees": 1.25,
        "buy_and_hold_final_equity": 508.33,
        "buy_and_hold_roi_percent": 1.666,
    }


def test_build_backtest_report_row_includes_results():
    row = build_backtest_report_row(
        sample_backtest_result()
    )

    assert row["exchange"] == "binance"
    assert row["symbol"] == "BTC/USDT"
    assert row["interval"] == "1h"
    assert row["candle_count"] == 500
    assert row["final_equity"] == 504.0
    assert row["net_profit"] == 4.0
    assert row["trade_count"] == 20
    assert row["total_fees"] == 1.25


def test_build_backtest_report_row_calculates_roi_difference():
    row = build_backtest_report_row(
        sample_backtest_result()
    )

    assert row["grid_roi_minus_hold_roi_percent"] == pytest.approx(
        -0.866
    )


def test_build_backtest_report_row_handles_missing_benchmark():
    result = sample_backtest_result()
    result.pop("buy_and_hold_roi_percent")

    row = build_backtest_report_row(result)

    assert row["grid_roi_minus_hold_roi_percent"] is None


def test_build_backtest_report_row_rejects_invalid_result():
    with pytest.raises(
        ValueError,
        match="Backtest result must be a dictionary",
    ):
        build_backtest_report_row("invalid")


def test_write_backtest_csv_report_creates_file(tmp_path):
    row = build_backtest_report_row(
        sample_backtest_result()
    )

    output_path = tmp_path / "reports" / "backtests.csv"

    saved_path = write_backtest_csv_report(
        [row],
        output_path,
    )

    assert saved_path == output_path
    assert output_path.exists()

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.DictReader(csv_file)
        saved_rows = list(reader)

    assert reader.fieldnames == BACKTEST_REPORT_FIELDS
    assert len(saved_rows) == 1
    assert saved_rows[0]["symbol"] == "BTC/USDT"
    assert saved_rows[0]["interval"] == "1h"
    assert float(saved_rows[0]["final_equity"]) == 504.0


def test_write_backtest_csv_report_supports_multiple_results(
    tmp_path,
):
    first = build_backtest_report_row(
        sample_backtest_result()
    )

    second_result = sample_backtest_result()
    second_result["symbol"] = "ETH/USDT"
    second_result["binance_symbol"] = "ETHUSDT"

    second = build_backtest_report_row(second_result)

    output_path = tmp_path / "comparison.csv"

    write_backtest_csv_report(
        [first, second],
        output_path,
    )

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[1]["symbol"] == "ETH/USDT"


def test_write_backtest_csv_report_creates_header_when_empty(
    tmp_path,
):
    output_path = tmp_path / "empty.csv"

    write_backtest_csv_report([], output_path)

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)

    assert header == BACKTEST_REPORT_FIELDS
