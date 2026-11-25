
import pytest

from grid_scanner import backtest_runner


def sample_candles():
    return [
        {
            "open_time": 1000,
            "close_time": 1999,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
        },
        {
            "open_time": 2000,
            "close_time": 2999,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
        },
        {
            "open_time": 3000,
            "close_time": 3999,
            "open": 101.0,
            "high": 103.0,
            "low": 100.0,
            "close": 102.0,
        },
    ]


def test_runner_fetches_completed_candles_and_runs_backtest(monkeypatch):
    calls = []

    monkeypatch.setattr(
        backtest_runner.time,
        "time",
        lambda: 10,
    )

    def fake_fetch(symbol, interval, limit):
        calls.append((symbol, interval, limit))
        return sample_candles()

    monkeypatch.setattr(
        backtest_runner,
        "fetch_binance_klines",
        fake_fetch,
    )

    result = backtest_runner.run_binance_spot_grid_backtest(
        "BTC/USDT",
        interval="1h",
        candle_limit=300,
        initial_capital=500,
        grid_spacing_percent=0.5,
        levels_each_side=5,
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    assert calls == [("BTCUSDT", "1h", 300)]

    assert result["exchange"] == "binance"
    assert result["symbol"] == "BTC/USDT"
    assert result["binance_symbol"] == "BTCUSDT"
    assert result["interval"] == "1h"

    assert result["candle_count"] == 3
    assert result["first_candle_time"] == 1000
    assert result["last_candle_time"] == 3000

    assert result["initial_capital"] == 500
    assert result["grid_spacing_percent"] == 0.5
    assert result["levels_each_side"] == 5


def test_runner_excludes_currently_forming_candle(monkeypatch):
    candles = sample_candles()

    candles.append(
        {
            "open_time": 4000,
            "close_time": 999999,
            "open": 102.0,
            "high": 110.0,
            "low": 101.0,
            "close": 109.0,
        }
    )

    monkeypatch.setattr(
        backtest_runner.time,
        "time",
        lambda: 10,
    )

    monkeypatch.setattr(
        backtest_runner,
        "fetch_binance_klines",
        lambda *args, **kwargs: candles,
    )

    result = backtest_runner.run_binance_spot_grid_backtest(
        "BTC/USDT"
    )

    assert result["candle_count"] == 3
    assert result["final_price"] == 102.0
    assert result["last_candle_time"] == 3000


def test_runner_rejects_insufficient_completed_candles(monkeypatch):
    monkeypatch.setattr(
        backtest_runner.time,
        "time",
        lambda: 10,
    )

    monkeypatch.setattr(
        backtest_runner,
        "fetch_binance_klines",
        lambda *args, **kwargs: sample_candles()[:1],
    )

    with pytest.raises(
        ValueError,
        match="At least two completed",
    ):
        backtest_runner.run_binance_spot_grid_backtest(
            "BTC/USDT"
        )


def test_runner_rejects_invalid_symbol():
    with pytest.raises(ValueError):
        backtest_runner.run_binance_spot_grid_backtest(
            "BTCUSDT"
        )


def test_runner_passes_execution_costs_to_backtest(monkeypatch):
    monkeypatch.setattr(
        backtest_runner.time,
        "time",
        lambda: 10,
    )

    monkeypatch.setattr(
        backtest_runner,
        "fetch_binance_klines",
        lambda *args, **kwargs: sample_candles(),
    )

    captured = {}

    def fake_backtest(candles, **settings):
        captured["candles"] = candles
        captured["settings"] = settings

        return {
            "strategy": "long_only_spot_grid",
            "candle_count": len(candles),
        }

    monkeypatch.setattr(
        backtest_runner,
        "backtest_spot_grid",
        fake_backtest,
    )

    result = backtest_runner.run_binance_spot_grid_backtest(
        "ETH/USDT",
        interval="4h",
        candle_limit=200,
        initial_capital=1000,
        grid_spacing_percent=1.0,
        levels_each_side=8,
        fee_rate=0.002,
        slippage_rate=0.001,
    )

    assert result["strategy"] == "long_only_spot_grid"
    assert result["symbol"] == "ETH/USDT"
    assert result["interval"] == "4h"

    assert captured["settings"] == {
        "initial_capital": 1000,
        "grid_spacing_percent": 1.0,
        "levels_each_side": 8,
        "fee_rate": 0.002,
        "slippage_rate": 0.001,
    }
