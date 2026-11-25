
import csv

from grid_scanner import backtest_cli


def sample_result():
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
        return sample_result()

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
