
from grid_scanner.exchanges import is_eligible_spot_market


def sample_market(**overrides):
    market = {
        "spot": True,
        "quote": "USDT",
        "active": True,
    }
    market.update(overrides)
    return market


def sample_ticker(**overrides):
    ticker = {
        "quoteVolume": 8_000_000,
        "bid": 100.0,
        "ask": 100.05,
    }
    ticker.update(overrides)
    return ticker


def test_accepts_liquid_tight_spread_spot_market():
    assert is_eligible_spot_market(
        sample_market(),
        sample_ticker(),
    )


def test_rejects_non_spot_market():
    assert not is_eligible_spot_market(
        sample_market(spot=False),
        sample_ticker(),
    )


def test_rejects_wrong_quote_currency():
    assert not is_eligible_spot_market(
        sample_market(quote="BTC"),
        sample_ticker(),
    )


def test_rejects_low_quote_volume():
    assert not is_eligible_spot_market(
        sample_market(),
        sample_ticker(quoteVolume=100_000),
    )


def test_rejects_wide_spread():
    assert not is_eligible_spot_market(
        sample_market(),
        sample_ticker(bid=100.0, ask=100.5),
    )


def test_rejects_missing_bid_or_ask():
    assert not is_eligible_spot_market(
        sample_market(),
        sample_ticker(ask=None),
    )
