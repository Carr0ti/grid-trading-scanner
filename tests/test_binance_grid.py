
import math

import pytest

from grid_scanner.binance_grid import (
    backtest_binance_spot_grid,
    calculate_grid_prices,
)


def make_candle(close, low=None, high=None):
    low = close if low is None else low
    high = close if high is None else high

    return {
        "open": close,
        "high": max(high, close),
        "low": min(low, close),
        "close": close,
    }


def make_candles(*candles):
    return [make_candle(*candle) for candle in candles]


def run_grid(candles, **overrides):
    settings = {
        "initial_capital": 500,
        "lower_price": 90,
        "upper_price": 110,
        "grid_count": 4,
        "mode": "arithmetic",
        "fee_rate": 0,
        "slippage_rate": 0,
    }
    settings.update(overrides)

    return backtest_binance_spot_grid(
        candles,
        **settings,
    )


def test_arithmetic_grid_prices():
    prices = calculate_grid_prices(
        90, 110, 4, "arithmetic"
    )

    assert prices == pytest.approx(
        [90, 95, 100, 105, 110]
    )


def test_geometric_grid_prices():
    prices = calculate_grid_prices(
        100, 200, 4, "geometric"
    )

    assert prices[0] == pytest.approx(100)
    assert prices[-1] == pytest.approx(200)

    ratios = [
        prices[i + 1] / prices[i]
        for i in range(len(prices) - 1)
    ]

    assert ratios == pytest.approx(
        [ratios[0]] * 4
    )


def test_arithmetic_grid_has_equal_absolute_spacing():
    prices = calculate_grid_prices(
        10, 30, 5, "arithmetic"
    )

    differences = [
        prices[i + 1] - prices[i]
        for i in range(len(prices) - 1)
    ]

    assert differences == pytest.approx(
        [4, 4, 4, 4, 4]
    )


def test_grid_has_exact_requested_number_of_intervals():
    prices = calculate_grid_prices(
        90, 110, 10, "arithmetic"
    )

    assert len(prices) == 11


@pytest.mark.parametrize(
    "lower, upper, count, mode",
    [
        (0, 100, 5, "arithmetic"),
        (-1, 100, 5, "arithmetic"),
        (100, 100, 5, "arithmetic"),
        (110, 100, 5, "arithmetic"),
        (90, 110, 1, "arithmetic"),
        (90, 110, 1001, "arithmetic"),
        (90, 110, True, "arithmetic"),
        (90, 110, 5, "unknown"),
        (math.inf, 110, 5, "arithmetic"),
    ],
)
def test_grid_price_calculation_rejects_invalid_settings(
    lower, upper, count, mode
):
    with pytest.raises(ValueError):
        calculate_grid_prices(
            lower, upper, count, mode
        )


def test_backtest_starts_with_balanced_portfolio_allocation():
    candles = make_candles(
        (100,),
        (100,),
    )

    result = run_grid(candles)

    assert result["initial_capital"] == 500
    assert result["initial_quote_cash"] == pytest.approx(250)
    assert result["initial_base_asset"] == pytest.approx(2.5)


def test_backtest_places_initial_buy_and_sell_orders():
    candles = make_candles(
        (100,),
        (100,),
    )

    result = run_grid(candles)

    assert result["initial_buy_order_count"] == 2
    assert result["initial_sell_order_count"] == 2
    assert result["trade_count"] == 0


def test_buy_order_fills_when_price_touches_level():
    candles = make_candles(
        (100,),
        (99, 94, 100),
    )

    result = run_grid(candles)

    assert result["buy_count"] == 1
    assert result["fills"][0]["side"] == "buy"
    assert result["fills"][0]["grid_price"] == 95


def test_sell_order_fills_when_price_touches_level():
    candles = make_candles(
        (100,),
        (106, 100, 106),
    )

    result = run_grid(candles)

    assert result["sell_count"] == 1
    assert result["fills"][0]["side"] == "sell"
    assert result["fills"][0]["grid_price"] == 105


def test_buy_then_sell_completes_a_grid_cycle():
    candles = make_candles(
        (100,),
        (94, 94, 100),
        (100, 99, 101),
    )

    result = run_grid(candles)

    assert result["buy_count"] == 1
    assert result["sell_count"] == 1
    assert result["trade_count"] == 2

    assert result["fills"][0]["side"] == "buy"
    assert result["fills"][1]["side"] == "sell"


def test_ambiguous_candle_skips_fills():
    candles = make_candles(
        (100,),
        (100, 94, 106),
    )

    result = run_grid(candles)

    assert result["trade_count"] == 0
    assert result["ambiguous_candles_skipped"] == 1


def test_first_candle_does_not_trigger_orders():
    candles = make_candles(
        (100, 80, 120),
        (100,),
    )

    result = run_grid(candles)

    assert result["trade_count"] == 0


def test_starting_price_must_be_inside_grid():
    candles = make_candles(
        (120,),
        (120,),
    )

    with pytest.raises(ValueError):
        run_grid(candles)


def test_fees_reduce_final_equity():
    candles = make_candles(
        (100,),
        (94, 94, 100),
    )

    free = run_grid(candles)

    with_fees = run_grid(
        candles,
        fee_rate=0.001,
    )

    assert with_fees["total_fees"] > 0
    assert (
        with_fees["final_equity"]
        < free["final_equity"]
    )


def test_slippage_is_recorded_in_execution_price():
    candles = make_candles(
        (100,),
        (94, 94, 100),
    )

    result = run_grid(
        candles,
        slippage_rate=0.001,
    )

    fill = result["fills"][0]

    assert fill["execution_price"] > fill["grid_price"]


def test_flat_market_has_zero_return_without_fees():
    candles = make_candles(
        (100,),
        (100,),
        (100,),
    )

    result = run_grid(candles)

    assert result["final_equity"] == pytest.approx(500)
    assert result["roi_percent"] == pytest.approx(0)
    assert result["buy_and_hold_roi_percent"] == pytest.approx(0)


def test_backtest_returns_risk_and_benchmark_metrics():
    candles = make_candles(
        (100,),
        (99,),
        (101,),
    )

    result = run_grid(candles)

    assert "net_profit" in result
    assert "roi_percent" in result
    assert "maximum_drawdown_percent" in result
    assert "buy_and_hold_roi_percent" in result
    assert len(result["equity_curve"]) == len(candles)


def test_invalid_backtest_settings_are_rejected():
    candles = make_candles(
        (100,),
        (100,),
    )

    invalid_settings = [
        {"initial_capital": 0},
        {"lower_price": 0},
        {"upper_price": 0},
        {"grid_count": 1},
        {"grid_count": True},
        {"mode": "invalid"},
        {"fee_rate": -0.1},
        {"fee_rate": 1},
        {"slippage_rate": -0.1},
        {"slippage_rate": 1},
    ]

    for settings in invalid_settings:
        with pytest.raises(ValueError):
            run_grid(candles, **settings)


def test_backtest_requires_at_least_two_candles():
    with pytest.raises(ValueError):
        run_grid([make_candle(100)])
