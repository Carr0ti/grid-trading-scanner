
import pytest

from grid_scanner import pipeline


def sample_candidates():
    return [
        {"exchange": "binance", "symbol": "BTC/USDT"},
        {"exchange": "binance", "symbol": "ETH/USDT"},
        {"exchange": "binance", "symbol": "SOL/USDT"},
    ]


def sample_result(symbol, status="NO_TRADE"):
    return {
        "exchange": "binance",
        "symbol": symbol,
        "status": status,
        "reasons": [],
        "candle_counts": {},
        "timeframes": {},
    }


def test_pipeline_scans_and_researches_selected_pairs(monkeypatch):
    scan_calls = []
    research_calls = []

    def fake_scan(
        exchange_id,
        quote_currency,
        minimum_quote_volume,
        maximum_spread_percent,
    ):
        scan_calls.append(
            (
                exchange_id,
                quote_currency,
                minimum_quote_volume,
                maximum_spread_percent,
            )
        )
        return sample_candidates()

    def fake_research(pairs, candle_limit):
        research_calls.append((pairs, candle_limit))

        return [
            sample_result("BTC/USDT", "POTENTIAL_GRID_CANDIDATE"),
            sample_result("ETH/USDT"),
        ]

    monkeypatch.setattr(pipeline, "scan_exchange", fake_scan)
    monkeypatch.setattr(pipeline, "research_pairs", fake_research)

    results = pipeline.run_binance_pipeline(
        limit=2,
        minimum_quote_volume=6_000_000,
        maximum_spread_percent=0.10,
        candle_limit=300,
    )

    assert scan_calls == [
        ("binance", "USDT", 6_000_000, 0.10)
    ]

    assert len(research_calls) == 1
    assert [
        pair["symbol"] for pair in research_calls[0][0]
    ] == ["BTC/USDT", "ETH/USDT"]

    assert research_calls[0][1] == 300
    assert len(results) == 2
    assert results[0]["status"] == "POTENTIAL_GRID_CANDIDATE"


def test_pipeline_returns_empty_when_no_candidates(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "scan_exchange",
        lambda exchange_id, **kwargs: [],
    )

    def unexpected_research(*args, **kwargs):
        pytest.fail("Research should not run without candidates")

    monkeypatch.setattr(
        pipeline,
        "research_pairs",
        unexpected_research,
    )

    assert pipeline.run_binance_pipeline() == []


@pytest.mark.parametrize(
    "options",
    [
        {"limit": 0},
        {"limit": -1},
        {"minimum_quote_volume": -1},
        {"maximum_spread_percent": -0.1},
        {"candle_limit": 49},
        {"candle_limit": 1001},
    ],
)
def test_pipeline_rejects_invalid_options(options):
    with pytest.raises(ValueError):
        pipeline.run_binance_pipeline(**options)


def test_pipeline_keeps_results_when_research_returns_failures(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "scan_exchange",
        lambda exchange_id, **kwargs: sample_candidates()[:2],
    )

    monkeypatch.setattr(
        pipeline,
        "research_pairs",
        lambda pairs, candle_limit: [
            sample_result("BTC/USDT", "ANALYSIS_FAILED"),
            sample_result("ETH/USDT", "POTENTIAL_GRID_CANDIDATE"),
        ],
    )

    results = pipeline.run_binance_pipeline(limit=2)

    assert len(results) == 2
    assert results[0]["status"] == "ANALYSIS_FAILED"
    assert results[1]["status"] == "POTENTIAL_GRID_CANDIDATE"
