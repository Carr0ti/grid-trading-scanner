
import csv

from grid_scanner import backtest_cli


def sample_result(symbol="BTC/USDT"):
    return {
        "exchange": "binance",
        "symbol": symbol,
        "binance_symbol": symbol.replace("/", ""),
        "interval": "1h",
        "first_candle_time": 1700000000000,
        "last_candle_time": 1701800000000,
        "candle_count": 500,
        "strategy": "long_only_spot_grid",
        "initial_capital": 500.0,
        "grid_center": 100000.0,
        "grid_spacing_percent": 0.5,
        "levels_each_side": 10,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
        "final_price": 101000.0,
        "final_cash": 260.0,
        "final_base_asset": 0.002475,
        "final_equity": 510.0,
        "net_profit": 10.0,
        "roi_percent": 2.0,
        "maximum_drawdown_percent": 1.5,
        "trade_count": 20,
        "buy_count": 10,
        "sell_count": 10,
        "ambiguous_candles_skipped": 2,
        "total_fees": 1.25,
        "buy_and_hold_final_equity": 505.0,
        "buy_and_hold_roi_percent": 1.0,
    }


def sample_batch(symbols):
    results = [sample_result(symbol) for symbol in symbols]

    return {
        "exchange": "binance",
        "interval": "1h",
        "requested_count": len(symbols),
        "success_count": len(results),
        "failure_count": 0,
        "results": results,
        "errors": [],
    }


def test_cli_runs_backtest_and_displays_results(monkeypatch, capsys):
    captured = {}

    def fake_backtest(**settings):
        captured.update(settings)
        return sample_result()

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_backtest",
        fake_backtest,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-backtest",
            "BTC/USDT",
            "--interval",
            "4h",
            "--candles",
            "300",
            "--capital",
            "1000",
            "--spacing",
            "1.0",
            "--levels",
            "8",
            "--fee",
            "0.2",
            "--slippage",
            "0.1",
        ],
    )

    backtest_cli.main()

    output = capsys.readouterr().out

    assert captured == {
        "symbol": "BTC/USDT",
        "interval": "4h",
        "candle_limit": 300,
        "initial_capital": 1000.0,
        "grid_spacing_percent": 1.0,
        "levels_each_side": 8,
        "fee_rate": 0.002,
        "slippage_rate": 0.001,
    }

    assert "BINANCE SPOT GRID HISTORICAL BACKTEST" in output
    assert "GRID STRATEGY RESULTS" in output
    assert "BUY-AND-HOLD BENCHMARK" in output
    assert "Final equity: 510.0000 USDT" in output
    assert "Grid ROI minus hold ROI: +1.000 percentage points" in output
    assert "No trades were placed." in output


def test_cli_uses_default_settings(monkeypatch):
    captured = {}

    def fake_backtest(**settings):
        captured.update(settings)
        return sample_result("ETH/USDT")

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_backtest",
        fake_backtest,
    )

    monkeypatch.setattr(
        "sys.argv",
        ["grid-backtest", "ETH/USDT"],
    )

    backtest_cli.main()

    assert captured == {
        "symbol": "ETH/USDT",
        "interval": "1h",
        "candle_limit": 500,
        "initial_capital": 500.0,
        "grid_spacing_percent": 0.5,
        "levels_each_side": 10,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
    }


def test_cli_reports_backtest_errors(monkeypatch):
    def fake_backtest(**settings):
        raise ValueError("Not enough historical candles")

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_backtest",
        fake_backtest,
    )

    monkeypatch.setattr(
        "sys.argv",
        ["grid-backtest", "BTC/USDT"],
    )

    try:
        backtest_cli.main()
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("Expected CLI to exit with an error")


def test_cli_saves_csv_report(monkeypatch, capsys, tmp_path):
    output_path = tmp_path / "reports" / "btc-backtest.csv"

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_backtest",
        lambda **settings: sample_result(),
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-backtest",
            "BTC/USDT",
            "--output",
            str(output_path),
        ],
    )

    backtest_cli.main()

    output = capsys.readouterr().out

    assert output_path.exists()
    assert "CSV report saved to:" in output

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[0]["interval"] == "1h"
    assert float(rows[0]["roi_percent"]) == 2.0
    assert float(rows[0]["buy_and_hold_roi_percent"]) == 1.0


def test_cli_does_not_create_csv_without_output_option(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_backtest",
        lambda **settings: sample_result(),
    )

    monkeypatch.setattr(
        "sys.argv",
        ["grid-backtest", "BTC/USDT"],
    )

    backtest_cli.main()

    output = capsys.readouterr().out

    assert "CSV report saved to:" not in output


def test_cli_runs_batch_for_multiple_pairs(monkeypatch, capsys):
    captured = {}

    def fake_batch(**settings):
        captured.update(settings)
        return sample_batch(["BTC/USDT", "ETH/USDT", "SOL/USDT"])

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_batch_backtest",
        fake_batch,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-backtest",
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "--interval",
            "4h",
            "--candles",
            "300",
            "--capital",
            "1000",
        ],
    )

    backtest_cli.main()

    output = capsys.readouterr().out

    assert captured == {
        "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        "interval": "4h",
        "candle_limit": 300,
        "initial_capital": 1000.0,
        "grid_spacing_percent": 0.5,
        "levels_each_side": 10,
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
    }

    assert "BINANCE SPOT GRID BATCH BACKTEST" in output
    assert "Requested pairs: 3" in output
    assert "Successful: 3" in output
    assert "BTC/USDT" in output
    assert "ETH/USDT" in output
    assert "SOL/USDT" in output


def test_cli_saves_all_successful_batch_results_to_csv(
    monkeypatch,
    capsys,
    tmp_path,
):
    output_path = tmp_path / "reports" / "batch-results.csv"

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_batch_backtest",
        lambda **settings: sample_batch(
            ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        ),
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-backtest",
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "--output",
            str(output_path),
        ],
    )

    backtest_cli.main()

    output = capsys.readouterr().out

    assert output_path.exists()
    assert "CSV report saved to:" in output

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 3
    assert [row["symbol"] for row in rows] == [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
    ]


def test_cli_displays_failed_batch_pairs(monkeypatch, capsys):
    batch = sample_batch(["BTC/USDT"])
    batch["requested_count"] = 2
    batch["failure_count"] = 1
    batch["errors"] = [
        {
            "symbol": "BAD/USDT",
            "error": "Pair unavailable",
        }
    ]

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_batch_backtest",
        lambda **settings: batch,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-backtest",
            "BTC/USDT",
            "BAD/USDT",
        ],
    )

    backtest_cli.main()

    output = capsys.readouterr().out

    assert "Requested pairs: 2" in output
    assert "Successful: 1" in output
    assert "Failed: 1" in output
    assert "BAD/USDT: Pair unavailable" in output


def test_cli_saves_empty_batch_csv_when_all_pairs_fail(
    monkeypatch,
    capsys,
    tmp_path,
):
    output_path = tmp_path / "all-failed.csv"

    batch = {
        "exchange": "binance",
        "interval": "1h",
        "requested_count": 2,
        "success_count": 0,
        "failure_count": 2,
        "results": [],
        "errors": [
            {"symbol": "BAD1/USDT", "error": "Unavailable"},
            {"symbol": "BAD2/USDT", "error": "Unavailable"},
        ],
    }

    monkeypatch.setattr(
        backtest_cli,
        "run_binance_spot_grid_batch_backtest",
        lambda **settings: batch,
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "grid-backtest",
            "BAD1/USDT",
            "BAD2/USDT",
            "--output",
            str(output_path),
        ],
    )

    backtest_cli.main()

    assert output_path.exists()

    with output_path.open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows == []
