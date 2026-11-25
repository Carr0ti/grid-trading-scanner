
import pytest

from grid_scanner import parameter_sweep


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


def setup_fake_market_data(monkeypatch):
    calls = []

    monkeypatch.setattr(
        parameter_sweep.time,
        "time",
        lambda: 10,
    )

    def fake_fetch(symbol, interval, limit):
        calls.append((symbol, interval, limit))

        if symbol == "BADUSDT":
            raise ValueError("Pair unavailable")

        return sample_candles()

    monkeypatch.setattr(
        parameter_sweep,
        "fetch_binance_klines",
        fake_fetch,
    )

    return calls


def test_sweep_runs_all_default_configurations(monkeypatch):
    calls = setup_fake_market_data(monkeypatch)

    result = parameter_sweep.run_binance_spot_grid_parameter_sweep(
        ["BTC/USDT"],
    )

    assert calls == [("BTCUSDT", "1h", 500)]

    assert result["exchange"] == "binance"
    assert result["interval"] == "1h"
    assert result["requested_pairs"] == 1
    assert result["configurations_per_pair"] == 12
    assert result["requested_tests"] == 12
    assert result["success_count"] == 12
    assert result["failure_count"] == 0

    assert len(result["configurations"]) == 12
    assert len(result["results"]) == 12
    assert result["errors"] == []


def test_sweep_uses_each_spacing_and_level_combination(monkeypatch):
    setup_fake_market_data(monkeypatch)

    result = parameter_sweep.run_binance_spot_grid_parameter_sweep(
        ["BTC/USDT"],
        spacing_options=[0.25, 0.5],
        level_options=[3, 5],
    )

    combinations = {
        (
            item["grid_spacing_percent"],
            item["levels_each_side"],
        )
        for item in result["results"]
    }

    assert combinations == {
        (0.25, 3),
        (0.25, 5),
        (0.5, 3),
        (0.5, 5),
    }

    assert result["success_count"] == 4


def test_sweep_fetches_market_data_once_per_pair(monkeypatch):
    calls = setup_fake_market_data(monkeypatch)

    result = parameter_sweep.run_binance_spot_grid_parameter_sweep(
        ["BTC/USDT", "ETH/USDT"],
        spacing_options=[0.5, 1.0],
        level_options=[5, 10],
    )

    assert calls == [
        ("BTCUSDT", "1h", 500),
        ("ETHUSDT", "1h", 500),
    ]

    assert result["requested_pairs"] == 2
    assert result["requested_tests"] == 8
    assert result["success_count"] == 8


def test_sweep_passes_custom_settings(monkeypatch):
    calls = setup_fake_market_data(monkeypatch)

    result = parameter_sweep.run_binance_spot_grid_parameter_sweep(
        ["ETH/USDT"],
        interval="4h",
        candle_limit=300,
        initial_capital=1000,
        spacing_options=[0.75],
        level_options=[8],
        fee_rate=0.002,
        slippage_rate=0.001,
    )

    assert calls == [("ETHUSDT", "4h", 300)]

    item = result["results"][0]

    assert item["initial_capital"] == 1000
    assert item["grid_spacing_percent"] == 0.75
    assert item["levels_each_side"] == 8
    assert item["fee_rate"] == 0.002
    assert item["slippage_rate"] == 0.001
    assert item["symbol"] == "ETH/USDT"
    assert item["interval"] == "4h"


def test_sweep_continues_after_one_pair_fails(monkeypatch):
    calls = setup_fake_market_data(monkeypatch)

    result = parameter_sweep.run_binance_spot_grid_parameter_sweep(
        ["BTC/USDT", "BAD/USDT", "ETH/USDT"],
        spacing_options=[0.5],
        level_options=[5],
    )

    assert len(calls) == 3
    assert result["requested_pairs"] == 3
    assert result["requested_tests"] == 3
    assert result["success_count"] == 2
    assert result["failure_count"] == 1

    assert [
        item["symbol"] for item in result["results"]
    ] == [
        "BTC/USDT",
        "ETH/USDT",
    ]

    assert result["errors"][0]["symbol"] == "BAD/USDT"
    assert result["errors"][0]["error"] == "Pair unavailable"


def test_sweep_rejects_empty_symbol_list():
    with pytest.raises(
        ValueError,
        match="At least one trading pair",
    ):
        parameter_sweep.run_binance_spot_grid_parameter_sweep([])


def test_sweep_rejects_string_instead_of_symbol_list():
    with pytest.raises(
        ValueError,
        match="Symbols must be a list",
    ):
        parameter_sweep.run_binance_spot_grid_parameter_sweep(
            "BTC/USDT"
        )


def test_sweep_rejects_empty_spacing_options():
    with pytest.raises(
        ValueError,
        match="Spacing and level options cannot be empty",
    ):
        parameter_sweep.run_binance_spot_grid_parameter_sweep(
            ["BTC/USDT"],
            spacing_options=[],
        )


def test_sweep_rejects_empty_level_options():
    with pytest.raises(
        ValueError,
        match="Spacing and level options cannot be empty",
    ):
        parameter_sweep.run_binance_spot_grid_parameter_sweep(
            ["BTC/USDT"],
            level_options=[],
        )


@pytest.mark.parametrize(
    "spacing",
    [0, -0.5, float("inf"), float("nan"), True],
)
def test_sweep_rejects_invalid_spacing(spacing):
    with pytest.raises(
        ValueError,
        match="Every grid spacing must be positive",
    ):
        parameter_sweep.run_binance_spot_grid_parameter_sweep(
            ["BTC/USDT"],
            spacing_options=[spacing],
        )


@pytest.mark.parametrize(
    "level",
    [0, -1, 1001, True, 2.5],
)
def test_sweep_rejects_invalid_levels(level):
    with pytest.raises(
        ValueError,
        match="Every grid level must be between 1 and 1000",
    ):
        parameter_sweep.run_binance_spot_grid_parameter_sweep(
            ["BTC/USDT"],
            level_options=[level],
        )


def test_sweep_accepts_generators(monkeypatch):
    setup_fake_market_data(monkeypatch)

    symbols = (
        symbol
        for symbol in ["BTC/USDT", "ETH/USDT"]
    )

    spacings = (
        spacing
        for spacing in [0.5, 1.0]
    )

    levels = (
        level
        for level in [5, 10]
    )

    result = parameter_sweep.run_binance_spot_grid_parameter_sweep(
        symbols,
        spacing_options=spacings,
        level_options=levels,
    )

    assert result["requested_pairs"] == 2
    assert result["requested_tests"] == 8
    assert result["success_count"] == 8
