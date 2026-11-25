
import pytest

from grid_scanner.backtest import backtest_spot_grid


def make_candle(
    close,
    low=None,
    high=None,
    open_price=None,
    timestamp=None,
):
    """Create a valid synthetic OHLC candle."""
    low = close if low is None else low
    high = close if high is None else high
    open_price = close if open_price is None else open_price

    candle = {
        "open": open_price,
        "high": max(high, open_price, close),
        "low": min(low, open_price, close),
        "close": close,
    }

    if timestamp is not None:
        candle["open_time"] = timestamp

    return candle


def simple_grid_backtest(candles, **overrides):
    settings = {
        "initial_capital": 500,
        "grid_spacing_percent": 1,
        "levels_each_side": 2,
        "fee_rate": 0,
        "slippage_rate": 0,
    }
    settings.update(overrides)

    return backtest_spot_grid(candles, **settings)


def test_backtest_requires_at_least_two_candles():
    with pytest.raises(ValueError):
        simple_grid_backtest([make_candle(100)])


def test_backtest_rejects_invalid_candle_prices():
    candles = [
        make_candle(100),
        {
            "open": 100,
            "high": 90,
            "low": 95,
            "close": 98,
        },
    ]

    with pytest.raises(ValueError):
        simple_grid_backtest(candles)


def test_backtest_rejects_out_of_order_timestamps():
    candles = [
        make_candle(100, timestamp=200),
        make_candle(101, timestamp=100),
    ]

    with pytest.raises(ValueError):
        simple_grid_backtest(candles)


def test_first_candle_does_not_trigger_new_grid_orders():
    candles = [
        make_candle(100, low=80, high=120),
        make_candle(100),
    ]

    result = simple_grid_backtest(candles)

    assert result["trade_count"] == 0
    assert result["buy_count"] == 0
    assert result["sell_count"] == 0


def test_buy_then_sell_completes_a_grid_cycle():
    candles = [
        make_candle(100),
        make_candle(99, low=98.5, high=99.5),
        make_candle(100, low=99.5, high=100.5),
    ]

    result = simple_grid_backtest(candles)

    assert result["buy_count"] == 1
    assert result["sell_count"] == 1
    assert result["trade_count"] == 2

    assert result["fills"][0]["side"] == "buy"
    assert result["fills"][1]["side"] == "sell"

    assert result["final_cash"] > 250
    assert result["final_base_asset"] == pytest.approx(2.5)


def test_only_one_order_can_fill_per_candle():
    candles = [
        make_candle(100),
        make_candle(95, low=90, high=100),
    ]

    result = simple_grid_backtest(candles)

    assert result["buy_count"] == 1
    assert result["trade_count"] == 1


def test_ambiguous_candle_skips_all_fills():
    candles = [
        make_candle(100),
        make_candle(100, low=90, high=110),
    ]

    result = simple_grid_backtest(candles)

    assert result["trade_count"] == 0
    assert result["ambiguous_candles_skipped"] == 1


def test_fees_and_slippage_reduce_grid_results():
    candles = [
        make_candle(100),
        make_candle(99, low=98.5, high=99.5),
        make_candle(100, low=99.5, high=100.5),
    ]

    free_execution = simple_grid_backtest(candles)

    costly_execution = simple_grid_backtest(
        candles,
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    assert costly_execution["total_fees"] > 0
    assert (
        costly_execution["final_equity"]
        < free_execution["final_equity"]
    )


def test_backtest_returns_benchmark_and_risk_metrics():
    candles = [
        make_candle(100),
        make_candle(99),
        make_candle(101),
    ]

    result = simple_grid_backtest(candles)

    assert "net_profit" in result
    assert "roi_percent" in result
    assert "maximum_drawdown_percent" in result
    assert "buy_and_hold_final_equity" in result
    assert "buy_and_hold_roi_percent" in result

    assert result["maximum_drawdown_percent"] >= 0
    assert len(result["equity_curve"]) == len(candles)


def test_buy_and_hold_benchmark_uses_same_initial_reference_price():
    candles = [
        make_candle(100),
        make_candle(110),
    ]

    result = simple_grid_backtest(candles)

    assert result["buy_and_hold_final_equity"] == pytest.approx(550)
    assert result["buy_and_hold_roi_percent"] == pytest.approx(10)


def test_flat_market_gives_both_strategies_zero_return():
    candles = [
        make_candle(100),
        make_candle(100),
        make_candle(100),
    ]

    result = simple_grid_backtest(candles)

    assert result["final_equity"] == pytest.approx(500)
    assert result["buy_and_hold_final_equity"] == pytest.approx(500)
    assert result["roi_percent"] == pytest.approx(0)
    assert result["buy_and_hold_roi_percent"] == pytest.approx(0)


@pytest.mark.parametrize(
    "settings",
    [
        {"initial_capital": 0},
        {"initial_capital": -100},
        {"grid_spacing_percent": 0},
        {"grid_spacing_percent": -1},
        {"levels_each_side": 0},
        {"levels_each_side": 1001},
        {"fee_rate": -0.1},
        {"fee_rate": 1},
        {"slippage_rate": -0.1},
        {"slippage_rate": 1},
    ],
)
def test_backtest_rejects_invalid_settings(settings):
    candles = [
        make_candle(100),
        make_candle(101),
    ]

    with pytest.raises(ValueError):
        simple_grid_backtest(candles, **settings)
