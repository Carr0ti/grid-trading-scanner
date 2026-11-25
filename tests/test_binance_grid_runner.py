
import pytest

from grid_scanner import binance_grid_runner as runner


def make_candle(open_time, close_time, close=100):
    return {
        "open_time": open_time,
        "close_time": close_time,
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
    }


def test_runner_converts_symbol_and_uses_manual_grid_settings(
    monkeypatch,
):
    candles = [
        make_candle(1000, 1999),
        make_candle(2000, 2999),
        make_candle(3000, 3999),
    ]

    fetched = {}
    simulated = {}

    monkeypatch.setattr(
        runner,
        "fetch_binance_klines",
        lambda symbol, interval, limit: (
            fetched.update(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit,
                }
            )
            or candles
        ),
    )

    monkeypatch.setattr(
        runner.time,
        "time",
        lambda: 4,
    )

    def fake_backtest(received_candles, **settings):
        simulated["candles"] = received_candles
        simulated["settings"] = settings

        return {
            "roi_percent": 2.5,
            "trade_count": 12,
        }

    monkeypatch.setattr(
        runner,
        "backtest_binance_spot_grid",
        fake_backtest,
    )

    result = runner.run_binance_manual_grid_backtest(
        symbol="BTC/USDT",
        lower_price=90000,
        upper_price=110000,
        grid_count=10,
        mode="geometric",
        interval="1h",
        candle_limit=100,
        initial_capital=500,
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    assert fetched == {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "limit": 100,
    }

    # Current time is 4000 ms.
    # All three candles are completed.
    assert len(simulated["candles"]) == 3

    assert simulated["settings"] == {
        "initial_capital": 500,
        "lower_price": 90000,
        "upper_price": 110000,
        "grid_count": 10,
        "mode": "geometric",
        "fee_rate": 0.001,
        "slippage_rate": 0.0005,
    }

    assert result["symbol"] == "BTC/USDT"
    assert result["binance_symbol"] == "BTCUSDT"
    assert result["exchange"] == "binance"
    assert result["interval"] == "1h"
    assert result["completed_candle_count"] == 3
    assert result["roi_percent"] == 2.5


def test_runner_excludes_currently_forming_candle(
    monkeypatch,
):
    candles = [
        make_candle(1000, 1999),
        make_candle(2000, 2999),
        make_candle(3000, 3999),
        make_candle(4000, 4999),
    ]

    monkeypatch.setattr(
        runner,
        "fetch_binance_klines",
        lambda *args, **kwargs: candles,
    )

    monkeypatch.setattr(
        runner.time,
        "time",
        lambda: 4,
    )

    received = {}

    def fake_backtest(received_candles, **settings):
        received["candles"] = received_candles
        return {"roi_percent": 0}

    monkeypatch.setattr(
        runner,
        "backtest_binance_spot_grid",
        fake_backtest,
    )

    runner.run_binance_manual_grid_backtest(
        "BTC/USDT",
        lower_price=90,
        upper_price=110,
    )

    assert len(received["candles"]) == 3
    assert received["candles"][-1]["close_time"] == 3999


def test_runner_rejects_invalid_symbol():
    with pytest.raises(ValueError):
        runner.run_binance_manual_grid_backtest(
            "BTCUSDT",
            lower_price=90,
            upper_price=110,
        )


def test_runner_rejects_invalid_interval():
    with pytest.raises(ValueError):
        runner.run_binance_manual_grid_backtest(
            "BTC/USDT",
            lower_price=90,
            upper_price=110,
            interval="5m",
        )


@pytest.mark.parametrize("limit", [1, 1001, True, 0])
def test_runner_rejects_invalid_candle_limit(limit):
    with pytest.raises(ValueError):
        runner.run_binance_manual_grid_backtest(
            "BTC/USDT",
            lower_price=90,
            upper_price=110,
            candle_limit=limit,
        )


def test_runner_rejects_insufficient_completed_candles(
    monkeypatch,
):
    candles = [
        make_candle(1000, 1999),
        make_candle(2000, 999999),
    ]

    monkeypatch.setattr(
        runner,
        "fetch_binance_klines",
        lambda *args, **kwargs: candles,
    )

    monkeypatch.setattr(
        runner.time,
        "time",
        lambda: 3,
    )

    with pytest.raises(ValueError):
        runner.run_binance_manual_grid_backtest(
            "BTC/USDT",
            lower_price=90,
            upper_price=110,
        )
