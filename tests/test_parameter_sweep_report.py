
import csv

import pytest

from grid_scanner.parameter_sweep_report import (
    PARAMETER_SWEEP_REPORT_FIELDS,
    build_parameter_sweep_report_rows,
    write_parameter_sweep_csv_report,
)


def sample_result():
    return {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "binance_symbol": "BTCUSDT",
        "interval": "1h",
        "first_candle_time": 1000,
        "last_candle_time": 5000,
        "candle_count": 5,
        "strategy": "long_only_spot_grid",
        "initial_capital": 500.0,
        "grid_center": 100.0,
        "grid_spacing_percent": 0.5,
        "levels_each_side": 10,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
        "final_price": 105.0,
        "final_cash": 260.0,
        "final_base_asset": 2.4,
        "final_equity": 512.0,
        "net_profit": 12.0,
        "roi_percent": 2.4,
        "maximum_drawdown_percent": 1.5,
        "trade_count": 8,
        "buy_count": 4,
        "sell_count": 4,
        "ambiguous_candles_skipped": 2,
        "total_fees": 1.2,
        "buy_and_hold_final_equity": 525.0,
        "buy_and_hold_roi_percent": 5.0,
    }


def test_build_report_rows_from_sweep_results():
    first = sample_result()
    second = sample_result()

    second["grid_spacing_percent"] = 1.0
    second["levels_each_side"] = 5
    second["roi_percent"] = 3.0

    sweep_result = {
        "results": [first, second],
    }

    rows = build_parameter_sweep_report_rows(sweep_result)

    assert len(rows) == 2
    assert rows[0]["configuration_number"] == 1
    assert rows[1]["configuration_number"] == 2

    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[0]["grid_spacing_percent"] == 0.5
    assert rows[1]["grid_spacing_percent"] == 1.0
    assert rows[1]["levels_each_side"] == 5


def test_report_includes_grid_and_hold_comparison():
    rows = build_parameter_sweep_report_rows({
        "results": [sample_result()],
    })

    row = rows[0]

    assert row["roi_percent"] == 2.4
    assert row["buy_and_hold_roi_percent"] == 5.0
    assert row["grid_roi_minus_hold_roi_percent"] == pytest.approx(
        -2.6
    )


def test_report_includes_risk_and_trade_metrics():
    rows = build_parameter_sweep_report_rows({
        "results": [sample_result()],
    })

    row = rows[0]

    assert row["maximum_drawdown_percent"] == 1.5
    assert row["trade_count"] == 8
    assert row["buy_count"] == 4
    assert row["sell_count"] == 4
    assert row["ambiguous_candles_skipped"] == 2
    assert row["total_fees"] == 1.2


def test_report_uses_expected_fields():
    rows = build_parameter_sweep_report_rows({
        "results": [sample_result()],
    })

    assert set(rows[0]) == set(PARAMETER_SWEEP_REPORT_FIELDS)


def test_report_rejects_non_dictionary_input():
    with pytest.raises(
        ValueError,
        match="Sweep result must be a dictionary",
    ):
        build_parameter_sweep_report_rows([])


def test_report_rejects_missing_results():
    with pytest.raises(
        ValueError,
        match="Sweep results must be a list",
    ):
        build_parameter_sweep_report_rows({})


def test_report_rejects_invalid_result_item():
    with pytest.raises(
        ValueError,
        match="Every sweep result must be a dictionary",
    ):
        build_parameter_sweep_report_rows({
            "results": ["invalid"],
        })


def test_write_csv_report_creates_file(tmp_path):
    rows = build_parameter_sweep_report_rows({
        "results": [sample_result()],
    })

    output = tmp_path / "reports" / "sweep.csv"

    returned_path = write_parameter_sweep_csv_report(
        rows,
        output,
    )

    assert returned_path == output
    assert output.exists()

    with output.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        saved_rows = list(csv.DictReader(csv_file))

    assert len(saved_rows) == 1
    assert saved_rows[0]["symbol"] == "BTC/USDT"
    assert saved_rows[0]["configuration_number"] == "1"
    assert saved_rows[0]["roi_percent"] == "2.4"


def test_write_csv_report_supports_multiple_rows(tmp_path):
    rows = build_parameter_sweep_report_rows({
        "results": [
            sample_result(),
            sample_result(),
        ],
    })

    output = tmp_path / "multiple.csv"

    write_parameter_sweep_csv_report(rows, output)

    with output.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        saved_rows = list(csv.DictReader(csv_file))

    assert len(saved_rows) == 2
    assert saved_rows[0]["configuration_number"] == "1"
    assert saved_rows[1]["configuration_number"] == "2"


def test_write_csv_report_supports_empty_rows(tmp_path):
    output = tmp_path / "empty.csv"

    write_parameter_sweep_csv_report([], output)

    assert output.exists()

    with output.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)

    assert header == PARAMETER_SWEEP_REPORT_FIELDS


def test_write_csv_report_rejects_non_list_rows(tmp_path):
    with pytest.raises(
        ValueError,
        match="Report rows must be a list",
    ):
        write_parameter_sweep_csv_report(
            {},
            tmp_path / "invalid.csv",
        )


def test_write_csv_report_rejects_invalid_row(tmp_path):
    with pytest.raises(
        ValueError,
        match="Every report row must be a dictionary",
    ):
        write_parameter_sweep_csv_report(
            ["invalid"],
            tmp_path / "invalid.csv",
        )
