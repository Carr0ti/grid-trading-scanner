
import pytest

from grid_scanner import binance_grid_optimizer as optimizer


def make_candles():
    return [
        {
            "open_time": 1000,
            "close_time": 1999,
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
        },
        {
            "open_time": 2000,
            "close_time": 2999,
            "open": 100,
            "high": 102,
            "low": 98,
            "close": 101,
        },
        {
            "open_time": 3000,
            "close_time": 3999,
            "open": 101,
            "high": 103,
            "low": 99,
            "close": 102,
        },
    ]


def test_optimizer_fetches_candles_once_and_tests_all_configurations(
    monkeypatch,
):
    candles = make_candles()
    fetch_calls = []
    backtest_calls = []

    def fake_fetch(symbol, interval, limit):
        fetch_calls.append((symbol, interval, limit))
        return candles

    def fake_backtest(received_candles, **settings):
        backtest_calls.append(settings)

        return {
            "roi_percent": (
                2 if settings["mode"] == "geometric" else 1
            ),
            "buy_and_hold_roi_percent": 0.5,
            "final_equity": 500,
            "maximum_drawdown_percent": 2,
            "trade_count": 10,
        }

    monkeypatch.setattr(
        optimizer,
        "fetch_binance_klines",
        fake_fetch,
    )
    monkeypatch.setattr(
        optimizer,
        "backtest_binance_spot_grid",
        fake_backtest,
    )
    monkeypatch.setattr(
        optimizer.time,
        "time",
        lambda: 4,
    )

    result = optimizer.run_binance_grid_optimizer(
        symbols=["BTC/USDT"],
        interval="1h",
        candle_limit=100,
        initial_capital=500,
        range_widths_percent=[10, 20],
        grid_counts=[5, 10],
        modes=["arithmetic", "geometric"],
    )

    assert fetch_calls == [
        ("BTCUSDT", "1h", 100)
    ]

    # 2 widths x 2 grid counts x 2 modes = 8 tests.
    assert len(backtest_calls) == 8
    assert result["requested_tests"] == 8
    assert result["success_count"] == 8
    assert result["failure_count"] == 0

    # The first range is 10% total width around price 100.
    assert backtest_calls[0]["lower_price"] == pytest.approx(95)
    assert backtest_calls[0]["upper_price"] == pytest.approx(105)

    assert result["results"][0]["mode"] == "geometric"
    assert result["results"][0]["rank"] == 1


def test_optimizer_excludes_forming_candle(monkeypatch):
    candles = make_candles()
    received = {}

    monkeypatch.setattr(
        optimizer,
        "fetch_binance_klines",
        lambda *args, **kwargs: candles,
    )
    monkeypatch.setattr(
        optimizer.time,
        "time",
        lambda: 3,
    )

    def fake_backtest(received_candles, **settings):
        received["candles"] = received_candles

        return {
            "roi_percent": 1,
            "buy_and_hold_roi_percent": 0,
        }

    monkeypatch.setattr(
        optimizer,
        "backtest_binance_spot_grid",
        fake_backtest,
    )

    result = optimizer.run_binance_grid_optimizer(
        symbols=["BTC/USDT"],
        range_widths_percent=[10],
        grid_counts=[5],
        modes=["arithmetic"],
    )

    assert len(received["candles"]) == 2
    assert received["candles"][-1]["close_time"] == 2999
    assert result["success_count"] == 1


def test_optimizer_sorts_results_by_roi(monkeypatch):
    monkeypatch.setattr(
        optimizer,
        "fetch_binance_klines",
        lambda *args, **kwargs: make_candles(),
    )
    monkeypatch.setattr(
        optimizer.time,
        "time",
        lambda: 4,
    )

    def fake_backtest(candles, **settings):
        roi = (
            5
            if settings["mode"] == "geometric"
            else -2
        )

        return {
            "roi_percent": roi,
            "buy_and_hold_roi_percent": 1,
        }

    monkeypatch.setattr(
        optimizer,
        "backtest_binance_spot_grid",
        fake_backtest,
    )

    result = optimizer.run_binance_grid_optimizer(
        symbols=["BTC/USDT"],
        range_widths_percent=[10],
        grid_counts=[5],
        modes=["arithmetic", "geometric"],
    )

    ranked = result["results"]

    assert ranked[0]["roi_percent"] == 5
    assert ranked[0]["rank"] == 1
    assert ranked[1]["roi_percent"] == -2
    assert ranked[1]["rank"] == 2


def test_optimizer_records_configuration_failures(monkeypatch):
    monkeypatch.setattr(
        optimizer,
        "fetch_binance_klines",
        lambda *args, **kwargs: make_candles(),
    )
    monkeypatch.setattr(
        optimizer.time,
        "time",
        lambda: 4,
    )

    def fake_backtest(candles, **settings):
        if settings["mode"] == "geometric":
            raise ValueError("Simulated configuration failure")

        return {
            "roi_percent": 1,
            "buy_and_hold_roi_percent": 0,
        }

    monkeypatch.setattr(
        optimizer,
        "backtest_binance_spot_grid",
        fake_backtest,
    )

    result = optimizer.run_binance_grid_optimizer(
        symbols=["BTC/USDT"],
        range_widths_percent=[10],
        grid_counts=[5],
        modes=["arithmetic", "geometric"],
    )

    assert result["success_count"] == 1
    assert result["failure_count"] == 1
    assert "Simulated configuration failure" in (
        result["errors"][0]["error"]
    )


def test_optimizer_records_pair_fetch_failures(monkeypatch):
    def fake_fetch(*args, **kwargs):
        raise RuntimeError("Binance unavailable")

    monkeypatch.setattr(
        optimizer,
        "fetch_binance_klines",
        fake_fetch,
    )

    result = optimizer.run_binance_grid_optimizer(
        symbols=["BTC/USDT"],
        range_widths_percent=[10],
        grid_counts=[5],
        modes=["arithmetic"],
    )

    assert result["success_count"] == 0
    assert result["failure_count"] == 1
    assert result["errors"][0]["symbol"] == "BTC/USDT"


@pytest.mark.parametrize(
    "settings",
    [
        {"symbols": []},
        {"symbols": ["BTC/BTC"]},
        {"symbols": ["BTC/USDT", "BTC/USDT"]},
        {"symbols": ["BTC/USDT"], "interval": "5m"},
        {"symbols": ["BTC/USDT"], "candle_limit": 1},
        {"symbols": ["BTC/USDT"], "candle_limit": 1001},
        {"symbols": ["BTC/USDT"], "candle_limit": True},
        {"symbols": ["BTC/USDT"], "initial_capital": 0},
        {"symbols": ["BTC/USDT"], "range_widths_percent": []},
        {"symbols": ["BTC/USDT"], "range_widths_percent": [0]},
        {"symbols": ["BTC/USDT"], "range_widths_percent": [200]},
        {"symbols": ["BTC/USDT"], "range_widths_percent": [True]},
        {"symbols": ["BTC/USDT"], "grid_counts": []},
        {"symbols": ["BTC/USDT"], "grid_counts": [1]},
        {"symbols": ["BTC/USDT"], "grid_counts": [1001]},
        {"symbols": ["BTC/USDT"], "grid_counts": [True]},
        {"symbols": ["BTC/USDT"], "modes": []},
        {"symbols": ["BTC/USDT"], "modes": ["unknown"]},
        {"symbols": ["BTC/USDT"], "fee_rate": -0.1},
        {"symbols": ["BTC/USDT"], "fee_rate": 1},
        {"symbols": ["BTC/USDT"], "slippage_rate": -0.1},
        {"symbols": ["BTC/USDT"], "slippage_rate": 1},
    ],
)
def test_optimizer_rejects_invalid_settings(settings):
    with pytest.raises(ValueError):
        optimizer.run_binance_grid_optimizer(**settings)


def test_optimizer_rejects_string_instead_of_symbol_list():
    with pytest.raises(ValueError):
        optimizer.run_binance_grid_optimizer(
            symbols="BTC/USDT"
        )


def test_optimizer_reports_insufficient_completed_candles(
    monkeypatch,
):
    candles = make_candles()[:1]

    monkeypatch.setattr(
        optimizer,
        "fetch_binance_klines",
        lambda *args, **kwargs: candles,
    )
    monkeypatch.setattr(
        optimizer.time,
        "time",
        lambda: 4,
    )

    result = optimizer.run_binance_grid_optimizer(
        symbols=["BTC/USDT"],
        range_widths_percent=[10],
        grid_counts=[5],
        modes=["arithmetic"],
    )

    assert result["success_count"] == 0
    assert result["failure_count"] == 1
    assert "completed historical candles" in (
        result["errors"][0]["error"]
    )
