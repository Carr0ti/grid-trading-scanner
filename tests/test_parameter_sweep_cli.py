
import csv

import pytest

from grid_scanner import parameter_sweep_cli


def sample_sweep():
    result = {
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
        "levels_each_side": 5,
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

    return {
        "interval": "1h",
        "requested_pairs": 1,
        "configurations_per_pair": 1,
        "requested_tests": 1,
        "success_count": 1,
        "failure_count": 0,
        "results": [result],
        "errors": [],
    }


def test_parser_defaults():
    parser = parameter_sweep_cli.build_parser()

    args = parser.parse_args(["BTC/USDT"])

    assert args.symbols == ["BTC/USDT"]
    assert args.interval == "1h"
    assert args.candles == 500
    assert args.capital == 500.0
    assert args.spacings == [0.3, 0.5, 0.75, 1.0]
    assert args.levels == [5, 10, 15]
    assert args.fee == 0.1
    assert args.slippage == 0.05
    assert args.output == "parameter-sweep.csv"


def test_parser_accepts_custom_options():
    parser = parameter_sweep_cli.build_parser()

    args = parser.parse_args([
        "BTC/USDT",
        "ETH/USDT",
        "--interval",
        "4h",
        "--candles",
        "300",
        "--capital",
        "1000",
        "--spacings",
        "0.25,0.5,1.0",
        "--levels",
        "3,5,10",
        "--fee",
        "0.2",
        "--slippage",
        "0.1",
        "--output",
        "custom.csv",
    ])

    assert args.symbols == ["BTC/USDT", "ETH/USDT"]
    assert args.interval == "4h"
    assert args.candles == 300
    assert args.capital == 1000
    assert args.spacings == [0.25, 0.5, 1.0]
    assert args.levels == [3, 5, 10]
    assert args.fee == 0.2
    assert args.slippage == 0.1
    assert args.output == "custom.csv"


def test_parse_float_options():
    assert parameter_sweep_cli.parse_float_options(
        "0.3, 0.5,1.0"
    ) == [0.3, 0.5, 1.0]


def test_parse_float_options_rejects_invalid_values():
    with pytest.raises(
        Exception,
        match="comma-separated numbers",
    ):
        parameter_sweep_cli.parse_float_options("0.5,abc")


def test_parse_float_options_rejects_empty_values():
    with pytest.raises(
        Exception,
        match="empty values",
    ):
        parameter_sweep_cli.parse_float_options("0.5,,1.0")


def test_parse_integer_options():
    assert parameter_sweep_cli.parse_integer_options(
        "5, 10,15"
    ) == [5, 10, 15]


def test_parse_integer_options_rejects_invalid_values():
    with pytest.raises(
        Exception,
        match="whole numbers",
    ):
        parameter_sweep_cli.parse_integer_options("5,2.5")


def test_main_runs_sweep_and_saves_csv(monkeypatch, tmp_path):
    calls = {}

    def fake_sweep(**kwargs):
        calls["settings"] = kwargs
        return sample_sweep()

    monkeypatch.setattr(
        parameter_sweep_cli,
        "run_binance_spot_grid_parameter_sweep",
        fake_sweep,
    )

    output = tmp_path / "reports" / "sweep.csv"

    parameter_sweep_cli.main([
        "BTC/USDT",
        "--interval",
        "4h",
        "--capital",
        "1000",
        "--spacings",
        "0.5,1.0",
        "--levels",
        "5,10",
        "--fee",
        "0.2",
        "--slippage",
        "0.1",
        "--output",
        str(output),
    ])

    settings = calls["settings"]

    assert settings["symbols"] == ["BTC/USDT"]
    assert settings["interval"] == "4h"
    assert settings["initial_capital"] == 1000
    assert settings["spacing_options"] == [0.5, 1.0]
    assert settings["level_options"] == [5, 10]
    assert settings["fee_rate"] == 0.002
    assert settings["slippage_rate"] == 0.001

    assert output.exists()

    with output.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[0]["roi_percent"] == "2.4"


def test_main_uses_default_arguments(monkeypatch, tmp_path):
    calls = {}

    def fake_sweep(**kwargs):
        calls["settings"] = kwargs
        return sample_sweep()

    monkeypatch.setattr(
        parameter_sweep_cli,
        "run_binance_spot_grid_parameter_sweep",
        fake_sweep,
    )

    monkeypatch.chdir(tmp_path)

    parameter_sweep_cli.main(["BTC/USDT"])

    settings = calls["settings"]

    assert settings["interval"] == "1h"
    assert settings["candle_limit"] == 500
    assert settings["initial_capital"] == 500.0
    assert settings["spacing_options"] == [0.3, 0.5, 0.75, 1.0]
    assert settings["level_options"] == [5, 10, 15]

    assert (tmp_path / "parameter-sweep.csv").exists()


def test_main_reports_sweep_errors(monkeypatch):
    def fake_sweep(**kwargs):
        raise ValueError("Invalid sweep settings")

    monkeypatch.setattr(
        parameter_sweep_cli,
        "run_binance_spot_grid_parameter_sweep",
        fake_sweep,
    )

    with pytest.raises(SystemExit) as error:
        parameter_sweep_cli.main(["BTC/USDT"])

    assert error.value.code == 2


def test_main_prints_failed_pair_errors(monkeypatch, tmp_path, capsys):
    sweep = sample_sweep()
    sweep["failure_count"] = 1
    sweep["errors"] = [
        {
            "symbol": "BAD/USDT",
            "error": "Pair unavailable",
        }
    ]

    monkeypatch.setattr(
        parameter_sweep_cli,
        "run_binance_spot_grid_parameter_sweep",
        lambda **kwargs: sweep,
    )

    parameter_sweep_cli.main([
        "BTC/USDT",
        "--output",
        str(tmp_path / "sweep.csv"),
    ])

    output = capsys.readouterr().out

    assert "BAD/USDT" in output
    assert "Pair unavailable" in output
    assert "No trades were placed." in output
    assert "CSV report saved to:" in output
