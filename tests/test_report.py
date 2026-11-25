
import csv

from grid_scanner.report import (
    REPORT_FIELDS,
    build_report_rows,
    write_csv_report,
)


def sample_research_result():
    return {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "status": "POTENTIAL_GRID_CANDIDATE",
        "reasons": ["4h and 1d show low directional persistence."],
        "candle_counts": {
            "1h": 500,
            "4h": 500,
            "1d": 500,
        },
        "timeframes": {
            "1h": {
                "atr_percent": 0.45,
                "path_efficiency": 0.20,
            },
            "4h": {
                "atr_percent": 1.20,
                "path_efficiency": 0.15,
            },
            "1d": {
                "atr_percent": 3.50,
                "path_efficiency": 0.25,
            },
        },
    }


def sample_market_data():
    return [
        {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "last": 60000.0,
            "quote_volume_usdt": 100000000.0,
            "bid": 59990.0,
            "ask": 60010.0,
            "spread_percent": 0.0333,
        }
    ]


def test_build_report_rows_combines_market_and_research_data():
    rows = build_report_rows(
        [sample_research_result()],
        sample_market_data(),
    )

    assert len(rows) == 1

    row = rows[0]

    assert row["symbol"] == "BTC/USDT"
    assert row["last"] == 60000.0
    assert row["quote_volume_usdt"] == 100000000.0
    assert row["status"] == "POTENTIAL_GRID_CANDIDATE"
    assert row["atr_1h_percent"] == 0.45
    assert row["atr_4h_percent"] == 1.20
    assert row["atr_1d_percent"] == 3.50
    assert row["candle_count_1h"] == 500
    assert row["path_efficiency_1d"] == 0.25


def test_build_report_rows_handles_missing_market_data():
    rows = build_report_rows([sample_research_result()])

    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[0]["last"] is None
    assert rows[0]["quote_volume_usdt"] is None


def test_build_report_rows_handles_multiple_results():
    second = sample_research_result()
    second["symbol"] = "ETH/USDT"
    second["status"] = "NO_TRADE"

    rows = build_report_rows(
        [sample_research_result(), second],
        sample_market_data(),
    )

    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[1]["symbol"] == "ETH/USDT"
    assert rows[1]["status"] == "NO_TRADE"


def test_build_report_rows_formats_reasons():
    result = sample_research_result()
    result["reasons"] = ["Reason one", "Reason two"]

    rows = build_report_rows([result])

    assert rows[0]["reasons"] == "Reason one | Reason two"


def test_build_report_rows_skips_invalid_results():
    rows = build_report_rows(
        [None, "invalid", sample_research_result()]
    )

    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTC/USDT"


def test_write_csv_report_creates_file(tmp_path):
    rows = build_report_rows(
        [sample_research_result()],
        sample_market_data(),
    )

    output_path = tmp_path / "reports" / "research.csv"

    saved_path = write_csv_report(rows, output_path)

    assert saved_path == output_path
    assert output_path.exists()

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.DictReader(csv_file)
        saved_rows = list(reader)

    assert reader.fieldnames == REPORT_FIELDS
    assert len(saved_rows) == 1
    assert saved_rows[0]["symbol"] == "BTC/USDT"
    assert saved_rows[0]["status"] == "POTENTIAL_GRID_CANDIDATE"


def test_write_csv_report_creates_header_for_empty_results(tmp_path):
    output_path = tmp_path / "empty.csv"

    write_csv_report([], output_path)

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)

    assert header == REPORT_FIELDS
