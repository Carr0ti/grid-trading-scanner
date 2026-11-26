
import csv

import pytest

from grid_scanner import binance_grid_optimizer_cli as cli


def sample_result():
    return {
        "rank": 1,
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "binance_symbol": "BTCUSDT",
        "interval": "1h",
        "mode": "geometric",
        "range_width_percent": 20.0,
        "lower_price": 90000.0,
        "upper_price": 110000.0,
        "grid_count": 10,
        "first_candle_time": 1000,
        "last_candle_time": 2000,
        "completed_candle_count": 500,
        "initial_capital": 500.0,
        "starting_price": 100000.0,
        "final_price": 102000.0,
        "final_equity": 510.0,
        "net_profit": 10.0,
        "roi_percent": 2.0,
        "buy_and_hold_final_equity": 505.0,
        "buy_and_hold_roi_percent": 1.0,
        "outperformance_vs_hold_percent": 1.0,
        "maximum_drawdown_percent": 1.5,
        "trade_count": 12,
        "buy_count": 6,
        "sell_count": 6,
        "ambiguous_candles_skipped": 2,
        "total_fees": 1.25,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
    }


def sample_optimizer_result():
    return {
        "exchange": "binance",
        "interval": "1h",
        "requested_pairs": 1,
        "configurations_per_pair": 24,
        "requested_tests": 24,
        "success_count": 24,
        "failure_count": 0,
        "configurations": [],
        "results": [sample_result()],
        "errors": [],
        "ranking_method": "historical ROI descending",
        "research_only": True,
    }


def test_parser_accepts_multiple_pairs_and_options():
    parser = cli.build_parser()

    args = parser.parse_args([
        "BTC/USDT",
        "ETH/USDT",
        "--interval", "4h",
        "--candles", "700",
        "--capital", "1000",
        "--widths", "10,20,30",
        "--grids", "5,10,15",
        "--modes", "arithmetic,geometric",
        "--fee", "0.1",
        "--slippage", "0.05",
        "--output", "reports/optimizer.csv",
    ])

    assert args.symbols == ["BTC/USDT", "ETH/USDT"]
    assert args.interval == "4h"
    assert args.candles == 700
    assert args.capital == 1000
    assert args.widths == [10.0, 20.0, 30.0]
    assert args.grids == [5, 10, 15]
    assert args.modes == ["arithmetic", "geometric"]
    assert args.fee == 0.1
    assert args.slippage == 0.05
    assert args.output == "reports/optimizer.csv"


def test_parser_uses_default_optimizer_options():
    args = cli.build_parser().parse_args(["BTC/USDT"])

    assert args.interval == "1h"
    assert args.candles == 500
    assert args.capital == 500.0
    assert args.widths == [10.0, 20.0, 30.0]
    assert args.grids == [5, 10, 15, 20]
    assert args.modes == ["arithmetic", "geometric"]


@pytest.mark.parametrize(
    "arguments",
    [
        ["BTC/USDT", "--widths", "10,,20"],
        ["BTC/USDT", "--widths", "abc"],
        ["BTC/USDT", "--grids", "5,,10"],
        ["BTC/USDT", "--grids", "5.5,10"],
        ["BTC/USDT", "--modes", "arithmetic,unknown"],
        ["BTC/USDT", "--modes", "arithmetic,"],
    ],
)
def test_parser_rejects_invalid_option_lists(arguments):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(arguments)


def test_parse_mode_options_normalizes_case():
    assert cli.parse_mode_options(
        "ARITHMETIC,Geometric"
    ) == ["arithmetic", "geometric"]


def test_main_passes_settings_to_optimizer(monkeypatch, capsys):
    received = {}

    def fake_optimizer(**settings):
        received.update(settings)
        return sample_optimizer_result()

    monkeypatch.setattr(
        cli,
        "run_binance_grid_optimizer",
        fake_optimizer,
    )

    monkeypatch.setattr(
        cli,
        "write_optimizer_csv_report",
        lambda optimizer, output: "optimizer.csv",
    )

    cli.main([
        "BTC/USDT",
        "ETH/USDT",
        "--interval", "4h",
        "--candles", "700",
        "--capital", "1000",
        "--widths", "10,20",
        "--grids", "5,10",
        "--modes", "geometric",
        "--fee", "0.1",
        "--slippage", "0.05",
        "--output", "optimizer.csv",
    ])

    assert received == {
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "interval": "4h",
        "candle_limit": 700,
        "initial_capital": 1000.0,
        "range_widths_percent": [10.0, 20.0],
        "grid_counts": [5, 10],
        "modes": ["geometric"],
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
    }

    output = capsys.readouterr().out
    assert "BINANCE SPOT GRID PARAMETER OPTIMIZER" in output
    assert "CSV report saved to: optimizer.csv" in output


def test_main_prints_ranked_results(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "run_binance_grid_optimizer",
        lambda **kwargs: sample_optimizer_result(),
    )

    monkeypatch.setattr(
        cli,
        "write_optimizer_csv_report",
        lambda optimizer, output: output,
    )

    cli.main(["BTC/USDT"])

    output = capsys.readouterr().out

    assert "RANKED CONFIGURATIONS" in output
    assert "BTC/USDT" in output
    assert "geometric" in output
    assert "2.000%" in output
    assert "DRAWDOWN" in output
    assert "Research only. No trades were placed." in output


def test_main_reports_optimizer_validation_error(monkeypatch):
    def fail_optimizer(**kwargs):
        raise ValueError("Only USDT pairs are supported")

    monkeypatch.setattr(
        cli,
        "run_binance_grid_optimizer",
        fail_optimizer,
    )

    with pytest.raises(SystemExit) as error:
        cli.main(["BTC/BTC"])

    assert error.value.code == 2


def test_csv_report_contains_ranked_results(tmp_path):
    optimizer = sample_optimizer_result()
    output = tmp_path / "reports" / "optimizer.csv"

    saved_path = cli.write_optimizer_csv_report(
        optimizer,
        str(output),
    )

    assert saved_path == output
    assert output.exists()

    with output.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["rank"] == "1"
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[0]["mode"] == "geometric"
    assert rows[0]["range_width_percent"] == "20.0"
    assert rows[0]["grid_count"] == "10"
    assert rows[0]["roi_percent"] == "2.0"
    assert rows[0]["maximum_drawdown_percent"] == "1.5"


def test_csv_report_writes_header_when_no_results(tmp_path):
    optimizer = sample_optimizer_result()
    optimizer["results"] = []

    output = tmp_path / "empty.csv"

    cli.write_optimizer_csv_report(
        optimizer,
        str(output),
    )

    with output.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows == []
