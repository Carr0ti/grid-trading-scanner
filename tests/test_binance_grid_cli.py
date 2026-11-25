
import csv

import pytest

from grid_scanner import binance_grid_cli as cli


def sample_result():
    return {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "binance_symbol": "BTCUSDT",
        "interval": "1h",
        "first_candle_time": 1000,
        "last_candle_time": 2000,
        "completed_candle_count": 500,
        "mode": "arithmetic",
        "initial_capital": 500.0,
        "starting_price": 100000.0,
        "lower_price": 90000.0,
        "upper_price": 110000.0,
        "grid_count": 10,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
        "grid_prices": [90000.0, 100000.0, 110000.0],
        "final_price": 102000.0,
        "final_equity": 510.0,
        "net_profit": 10.0,
        "roi_percent": 2.0,
        "maximum_drawdown_percent": 1.5,
        "trade_count": 12,
        "buy_count": 6,
        "sell_count": 6,
        "ambiguous_candles_skipped": 2,
        "total_fees": 1.25,
        "buy_and_hold_final_equity": 505.0,
        "buy_and_hold_roi_percent": 1.0,
    }


def test_parser_accepts_manual_grid_settings():
    parser = cli.build_parser()

    args = parser.parse_args([
        "BTC/USDT",
        "--lower", "90000",
        "--upper", "110000",
        "--grids", "20",
        "--mode", "geometric",
        "--interval", "4h",
        "--candles", "700",
        "--capital", "1000",
        "--fee", "0.1",
        "--slippage", "0.05",
    ])

    assert args.symbol == "BTC/USDT"
    assert args.lower == 90000
    assert args.upper == 110000
    assert args.grids == 20
    assert args.mode == "geometric"
    assert args.interval == "4h"
    assert args.candles == 700
    assert args.capital == 1000
    assert args.fee == 0.1
    assert args.slippage == 0.05


def test_parser_rejects_invalid_grid_mode():
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([
            "BTC/USDT",
            "--lower", "90000",
            "--upper", "110000",
            "--mode", "invalid",
        ])


def test_main_passes_settings_to_runner(monkeypatch):
    received = {}

    def fake_runner(**settings):
        received.update(settings)
        return sample_result()

    monkeypatch.setattr(
        cli,
        "run_binance_manual_grid_backtest",
        fake_runner,
    )

    cli.main([
        "BTC/USDT",
        "--lower", "90000",
        "--upper", "110000",
        "--grids", "20",
        "--mode", "geometric",
        "--interval", "4h",
        "--candles", "700",
        "--capital", "1000",
        "--fee", "0.1",
        "--slippage", "0.05",
    ])

    assert received == {
        "symbol": "BTC/USDT",
        "lower_price": 90000.0,
        "upper_price": 110000.0,
        "grid_count": 20,
        "mode": "geometric",
        "interval": "4h",
        "candle_limit": 700,
        "initial_capital": 1000.0,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
    }


def test_main_prints_backtest_results(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "run_binance_manual_grid_backtest",
        lambda **kwargs: sample_result(),
    )

    cli.main([
        "BTC/USDT",
        "--lower", "90000",
        "--upper", "110000",
    ])

    output = capsys.readouterr().out

    assert "BINANCE MANUAL SPOT GRID BACKTEST" in output
    assert "BTC/USDT" in output
    assert "GRID RESULTS" in output
    assert "BUY AND HOLD COMPARISON" in output
    assert "Research only. No trades were placed." in output


def test_main_reports_runner_validation_error(monkeypatch):
    def fail_runner(**kwargs):
        raise ValueError("Starting price must be inside grid range")

    monkeypatch.setattr(
        cli,
        "run_binance_manual_grid_backtest",
        fail_runner,
    )

    with pytest.raises(SystemExit) as error:
        cli.main([
            "BTC/USDT",
            "--lower", "90000",
            "--upper", "110000",
        ])

    assert error.value.code == 2


def test_csv_report_contains_backtest_summary(tmp_path):
    result = sample_result()
    output = tmp_path / "reports" / "manual-grid.csv"

    saved_path = cli.write_csv_report(
        result,
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
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[0]["mode"] == "arithmetic"
    assert rows[0]["roi_percent"] == "2.0"
    assert rows[0]["trade_count"] == "12"


def test_print_result_shows_grid_levels(capsys):
    cli.print_result(
        sample_result(),
        fee_percent=0.1,
        slippage_percent=0.05,
    )

    output = capsys.readouterr().out

    assert "Level" in output
    assert "90000.0000000000" in output
    assert "110000.0000000000" in output
