
import pytest

from grid_scanner import history


def sample_candle():
    return [
        1700000000000,
        "100.0",
        "105.0",
        "98.0",
        "103.0",
        "500.0",
        1700003599999,
        "51000.0",
        250,
        "200.0",
        "20500.0",
        "0",
    ]


def test_fetches_and_converts_candles(monkeypatch):
    def fake_fetch(endpoint):
        assert endpoint == (
            "/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=500"
        )
        return [sample_candle()]

    monkeypatch.setattr(history, "fetch_binance_json", fake_fetch)

    candles = history.fetch_binance_klines("BTCUSDT", "1h")

    assert len(candles) == 1
    assert candles[0]["open"] == 100.0
    assert candles[0]["high"] == 105.0
    assert candles[0]["low"] == 98.0
    assert candles[0]["close"] == 103.0
    assert candles[0]["volume"] == 500.0
    assert candles[0]["quote_volume"] == 51000.0
    assert candles[0]["trades"] == 250


def test_accepts_supported_intervals(monkeypatch):
    monkeypatch.setattr(
        history,
        "fetch_binance_json",
        lambda endpoint: [],
    )

    for interval in ("1h", "4h", "1d"):
        assert history.fetch_binance_klines(
            "BTCUSDT",
            interval,
        ) == []


def test_rejects_unsupported_interval():
    with pytest.raises(ValueError):
        history.fetch_binance_klines("BTCUSDT", "15m")


def test_rejects_invalid_symbol():
    with pytest.raises(ValueError):
        history.fetch_binance_klines("BTC/USDT", "1h")


@pytest.mark.parametrize("limit", [0, 1001, -1])
def test_rejects_invalid_candle_limit(limit):
    with pytest.raises(ValueError):
        history.fetch_binance_klines(
            "BTCUSDT",
            "1h",
            limit=limit,
        )


def test_skips_malformed_candles(monkeypatch):
    monkeypatch.setattr(
        history,
        "fetch_binance_json",
        lambda endpoint: [
            ["bad"],
            sample_candle(),
        ],
    )

    candles = history.fetch_binance_klines("BTCUSDT", "1h")

    assert len(candles) == 1
    assert candles[0]["close"] == 103.0


def test_rejects_unexpected_response(monkeypatch):
    monkeypatch.setattr(
        history,
        "fetch_binance_json",
        lambda endpoint: {"error": "unexpected"},
    )

    with pytest.raises(ValueError):
        history.fetch_binance_klines("BTCUSDT", "1h")
