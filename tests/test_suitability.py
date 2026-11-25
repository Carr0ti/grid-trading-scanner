
import pytest

from grid_scanner.suitability import evaluate_grid_suitability


def sample_metrics():
    return {
        "1h": {
            "atr_percent": 0.5,
            "path_efficiency": 0.4,
        },
        "4h": {
            "atr_percent": 1.0,
            "path_efficiency": 0.2,
        },
        "1d": {
            "atr_percent": 2.0,
            "path_efficiency": 0.25,
        },
    }


def test_identifies_potential_grid_candidate():
    result = evaluate_grid_suitability(sample_metrics())

    assert result["status"] == "POTENTIAL_GRID_CANDIDATE"
    assert result["reasons"]
    assert set(result["timeframes"]) == {"1h", "4h", "1d"}


def test_rejects_strong_directional_trend():
    metrics = sample_metrics()
    metrics["4h"]["path_efficiency"] = 0.7
    metrics["1d"]["path_efficiency"] = 0.8

    result = evaluate_grid_suitability(metrics)

    assert result["status"] == "TREND_TOO_STRONG"


def test_rejects_excessive_volatility():
    metrics = sample_metrics()
    metrics["1h"]["atr_percent"] = 2.5

    result = evaluate_grid_suitability(metrics)

    assert result["status"] == "TOO_RISKY"


def test_rejects_very_low_volatility():
    metrics = sample_metrics()

    metrics["1h"]["atr_percent"] = 0.01
    metrics["4h"]["atr_percent"] = 0.05
    metrics["1d"]["atr_percent"] = 0.1

    result = evaluate_grid_suitability(metrics)

    assert result["status"] == "VOLATILITY_TOO_LOW"


def test_returns_no_trade_for_unclear_conditions():
    metrics = sample_metrics()
    metrics["4h"]["path_efficiency"] = 0.5

    result = evaluate_grid_suitability(metrics)

    assert result["status"] == "NO_TRADE"


def test_returns_no_trade_when_one_timeframe_is_too_quiet():
    metrics = sample_metrics()
    metrics["1h"]["atr_percent"] = 0.01

    result = evaluate_grid_suitability(metrics)

    assert result["status"] == "NO_TRADE"
    assert any("Low volatility" in reason for reason in result["reasons"])


def test_rejects_missing_timeframe():
    metrics = sample_metrics()
    del metrics["1d"]

    with pytest.raises(ValueError):
        evaluate_grid_suitability(metrics)


def test_rejects_invalid_path_efficiency():
    metrics = sample_metrics()
    metrics["4h"]["path_efficiency"] = 1.5

    with pytest.raises(ValueError):
        evaluate_grid_suitability(metrics)


def test_rejects_negative_atr():
    metrics = sample_metrics()
    metrics["1h"]["atr_percent"] = -0.5

    with pytest.raises(ValueError):
        evaluate_grid_suitability(metrics)


def test_rejects_invalid_thresholds():
    metrics = sample_metrics()

    thresholds = {
        "trend_efficiency": 0.2,
        "range_efficiency": 0.5,
        "minimum_atr_percent": {
            "1h": 0.05,
            "4h": 0.1,
            "1d": 0.25,
        },
        "maximum_atr_percent": {
            "1h": 2.0,
            "4h": 4.0,
            "1d": 8.0,
        },
    }

    with pytest.raises(ValueError):
        evaluate_grid_suitability(metrics, thresholds)
