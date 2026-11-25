
from grid_scanner import backtest_cli


def sample_result():
    return {
        "symbol": "BTC/USDT",
        "interval": "1h",
        "candle_count": 500,
        "initial_capital": 500.0,
        "grid_center": 100000.0,
        "grid_spacing_percent": 0.5,
        "levels_each_side": 10,
        "final_price": 101000.0,
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
