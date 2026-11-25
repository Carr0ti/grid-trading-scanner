
import pytest

from grid_scanner import batch_backtest


def sample_result(symbol):
    return {
        "exchange": "binance",
        "symbol": symbol,
        "interval": "1h",
        "final_equity": 510.0,
        "roi_percent": 2.0,
    }


def test_batch_backtests_multiple_symbols(monkeypatch):
    calls = []

    def fake_backtest(**settings):
        calls.append(settings)
        return sample_result(settings["symbol"])

    monkeypatch.setattr(
        batch_backtest,
        "run_binance_spot_grid_backtest",
        fake_backtest,
    )

    result = batch_backtest.run_binance_spot_grid_batch_backtest(
        ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    )

    assert result["exchange"] == "binance"
    assert result["interval"] == "1h"
    assert result["requested_count"] == 3
    assert result["success_count"] == 3
    assert result["failure_count"] == 0

    assert [
        item["symbol"] for item in result["results"]
    ] == [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
    ]

    assert result["errors"] == []
    assert len(calls) == 3


def test_batch_passes_same_settings_to_every_pair(monkeypatch):
    calls = []

    def fake_backtest(**settings):
        calls.append(settings)
        return sample_result(settings["symbol"])

    monkeypatch.setattr(
        batch_backtest,
        "run_binance_spot_grid_backtest",
        fake_backtest,
    )

    batch_backtest.run_binance_spot_grid_batch_backtest(
        ["BTC/USDT", "ETH/USDT"],
        interval="4h",
        candle_limit=300,
        initial_capital=1000,
        grid_spacing_percent=1.0,
        levels_each_side=8,
        fee_rate=0.002,
        slippage_rate=0.001,
    )

    expected = {
        "interval": "4h",
        "candle_limit": 300,
        "initial_capital": 1000,
        "grid_spacing_percent": 1.0,
        "levels_each_side": 8,
        "fee_rate": 0.002,
        "slippage_rate": 0.001,
    }

    assert len(calls) == 2

    for call, symbol in zip(calls, ["BTC/USDT", "ETH/USDT"]):
        assert call == {
            "symbol": symbol,
            **expected,
        }


def test_batch_continues_after_one_pair_fails(monkeypatch):
    calls = []

    def fake_backtest(**settings):
        symbol = settings["symbol"]
        calls.append(symbol)

        if symbol == "BAD/USDT":
            raise ValueError("Pair unavailable")

        return sample_result(symbol)

    monkeypatch.setattr(
        batch_backtest,
        "run_binance_spot_grid_backtest",
        fake_backtest,
    )

    result = batch_backtest.run_binance_spot_grid_batch_backtest(
        ["BTC/USDT", "BAD/USDT", "ETH/USDT"],
    )

    assert calls == [
        "BTC/USDT",
        "BAD/USDT",
        "ETH/USDT",
    ]

    assert result["requested_count"] == 3
    assert result["success_count"] == 2
    assert result["failure_count"] == 1

    assert [
        item["symbol"] for item in result["results"]
    ] == [
        "BTC/USDT",
        "ETH/USDT",
    ]

    assert result["errors"] == [
        {
            "symbol": "BAD/USDT",
            "error": "Pair unavailable",
        }
    ]


def test_batch_records_all_failures(monkeypatch):
    def fake_backtest(**settings):
        raise ValueError("Historical data unavailable")

    monkeypatch.setattr(
        batch_backtest,
        "run_binance_spot_grid_backtest",
        fake_backtest,
    )

    result = batch_backtest.run_binance_spot_grid_batch_backtest(
        ["BAD1/USDT", "BAD2/USDT"],
    )

    assert result["requested_count"] == 2
    assert result["success_count"] == 0
    assert result["failure_count"] == 2
    assert result["results"] == []

    assert len(result["errors"]) == 2
    assert result["errors"][0]["symbol"] == "BAD1/USDT"
    assert result["errors"][1]["symbol"] == "BAD2/USDT"


def test_batch_rejects_empty_symbol_list():
    with pytest.raises(
        ValueError,
        match="At least one trading pair",
    ):
        batch_backtest.run_binance_spot_grid_batch_backtest([])


def test_batch_rejects_string_instead_of_symbol_list():
    with pytest.raises(
        ValueError,
        match="Symbols must be a list",
    ):
        batch_backtest.run_binance_spot_grid_batch_backtest(
            "BTC/USDT"
        )


def test_batch_accepts_generator_of_symbols(monkeypatch):
    monkeypatch.setattr(
        batch_backtest,
        "run_binance_spot_grid_backtest",
        lambda **settings: sample_result(settings["symbol"]),
    )

    symbols = (
        symbol
        for symbol in ["BTC/USDT", "ETH/USDT"]
    )

    result = batch_backtest.run_binance_spot_grid_batch_backtest(
        symbols,
    )

    assert result["requested_count"] == 2
    assert result["success_count"] == 2
    assert result["failure_count"] == 0
