
import pytest

from grid_scanner import research


def sample_candles(count=60):
    candles = []

    prices = [100.0, 100.2, 100.0, 99.8]

    for index in range(count):
        close = prices[index % len(prices)]

        candles.append(
            {
                "open": close,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 1000.0,
                "quote_volume": 100000.0,
                "trades": 100,
            }
        )

    return candles


def test_converts_ccxt_symbol_to_binance_symbol():
    assert research.to_binance_symbol("BTC/USDT") == "BTCUSDT"
    assert research.to_binance_symbol("eth/usdt") == "ETHUSDT"


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "BTCUSDT",
        "BTC/USDT/EXTRA",
        "/USDT",
        "BTC/",
        "BTC/USDT:USDT",
    ],
)
def test_rejects_invalid_symbols(symbol):
    with pytest.raises(ValueError):
        research.to_binance_symbol(symbol)


def test_research_pair_analyzes_all_timeframes(monkeypatch):
    calls = []

    def fake_fetch(symbol, interval, limit):
        calls.append((symbol, interval, limit))
        return sample_candles(limit)

    monkeypatch.setattr(
        research,
        "fetch_binance_klines",
        fake_fetch,
    )

    result = research.research_pair(
        "BTC/USDT",
        candle_limit=60,
    )

    assert calls == [
        ("BTCUSDT", "1h", 60),
        ("BTCUSDT", "4h", 60),
        ("BTCUSDT", "1d", 60),
    ]

    assert result["exchange"] == "binance"
    assert result["symbol"] == "BTC/USDT"
    assert result["status"] == "POTENTIAL_GRID_CANDIDATE"
    assert set(result["candle_counts"]) == {"1h", "4h", "1d"}
    assert set(result["timeframes"]) == {"1h", "4h", "1d"}


def test_research_pair_rejects_insufficient_candles(monkeypatch):
    monkeypatch.setattr(
        research,
        "fetch_binance_klines",
        lambda symbol, interval, limit: sample_candles(20),
    )

    with pytest.raises(ValueError, match="Insufficient"):
        research.research_pair("BTC/USDT")


@pytest.mark.parametrize("limit", [0, 49, 1001, -1])
def test_research_pair_rejects_invalid_candle_limit(limit):
    with pytest.raises(ValueError):
        research.research_pair(
            "BTC/USDT",
            candle_limit=limit,
        )


def test_research_pairs_continues_after_pair_failure(monkeypatch):
    def fake_research_pair(symbol, candle_limit):
        if symbol == "BAD/USDT":
            raise ValueError("Test failure")

        return {
            "exchange": "binance",
            "symbol": symbol,
            "status": (
                "POTENTIAL_GRID_CANDIDATE"
                if symbol == "BTC/USDT"
                else "NO_TRADE"
            ),
            "reasons": [],
            "candle_counts": {},
            "timeframes": {},
        }

    monkeypatch.setattr(
        research,
        "research_pair",
        fake_research_pair,
    )

    results = research.research_pairs(
        [
            {"symbol": "ETH/USDT"},
            {"symbol": "BAD/USDT"},
            {"symbol": "BTC/USDT"},
        ]
    )

    assert len(results) == 3
    assert results[0]["symbol"] == "BTC/USDT"
    assert results[0]["status"] == "POTENTIAL_GRID_CANDIDATE"

    failed = next(
        item for item in results
        if item["symbol"] == "BAD/USDT"
    )

    assert failed["status"] == "ANALYSIS_FAILED"
    assert "Test failure" in failed["reasons"][0]
