
import pytest

from grid_scanner.analyzer import (
    analyze_candles,
    calculate_atr,
    calculate_true_ranges,
)


def sample_candles():
    return [
        {"high": 11.0, "low": 9.0, "close": 10.0},
        {"high": 13.0, "low": 10.0, "close": 12.0},
        {"high": 14.0, "low": 11.0, "close": 13.0},
        {"high": 13.0, "low": 9.0, "close": 10.0},
    ]


def test_calculates_true_ranges():
    assert calculate_true_ranges(sample_candles()) == [
        2.0, 3.0, 3.0, 4.0
    ]


def test_calculates_atr():
    atr = calculate_atr(sample_candles(), period=2)

    assert atr == pytest.approx(3.375)


def test_analyzes_market_conditions():
    result = analyze_candles(
        sample_candles(),
        atr_period=2,
        lookback=3,
    )

    assert result["candle_count"] == 4
    assert result["atr"] == pytest.approx(3.375)
    assert result["atr_percent"] == pytest.approx(33.75)
    assert result["range_percent"] == pytest.approx(55.5555556)
    assert result["net_change_percent"] == pytest.approx(-16.6666667)
    assert result["path_efficiency"] == pytest.approx(0.5)


def test_rejects_invalid_atr_period():
    with pytest.raises(ValueError):
        calculate_atr(sample_candles(), period=0)


def test_rejects_insufficient_candles():
    with pytest.raises(ValueError):
        calculate_atr(sample_candles()[:1], period=2)


def test_rejects_invalid_lookback():
    with pytest.raises(ValueError):
        analyze_candles(sample_candles(), lookback=1)


def test_rejects_invalid_price():
    candles = sample_candles()
    candles[0]["close"] = 0

    with pytest.raises(ValueError):
        analyze_candles(candles, atr_period=2, lookback=3)


def test_rejects_high_below_low():
    candles = sample_candles()
    candles[0]["high"] = 5

    with pytest.raises(ValueError):
        calculate_true_ranges(candles)
