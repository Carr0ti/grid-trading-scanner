
"""Read public Spot market data from supported exchanges using CCXT."""

from __future__ import annotations

from typing import Any

import ccxt


SUPPORTED_EXCHANGES = ("binance", "okx", "bybit", "bitget", "mexc")


def create_exchange(exchange_id: str) -> ccxt.Exchange:
    """Create a rate-limited exchange client without credentials."""
    if exchange_id not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange: {exchange_id}")

    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def is_eligible_spot_market(
    market: dict[str, Any],
    ticker: dict[str, Any],
    quote_currency: str = "USDT",
    minimum_quote_volume: float = 5_000_000,
    maximum_spread_percent: float = 0.15,
) -> bool:
    """Apply initial liquidity and spread filters."""
    if market.get("spot") is not True:
        return False

    if market.get("quote") != quote_currency:
        return False

    if market.get("active") is False:
        return False

    quote_volume = ticker.get("quoteVolume")
    bid = ticker.get("bid")
    ask = ticker.get("ask")

    if not isinstance(quote_volume, (int, float)):
        return False

    if quote_volume < minimum_quote_volume:
        return False

    if not isinstance(bid, (int, float)):
        return False

    if not isinstance(ask, (int, float)):
        return False

    if bid <= 0 or ask <= 0 or ask < bid:
        return False

    midpoint = (bid + ask) / 2
    spread_percent = ((ask - bid) / midpoint) * 100

    return spread_percent <= maximum_spread_percent


def scan_exchange(
    exchange_id: str,
    quote_currency: str = "USDT",
    minimum_quote_volume: float = 5_000_000,
    maximum_spread_percent: float = 0.15,
) -> list[dict[str, Any]]:
    """Fetch public Spot tickers and return eligible markets by volume."""
    exchange = create_exchange(exchange_id)

    try:
        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()

        results: list[dict[str, Any]] = []

        for symbol, market in markets.items():
            ticker = tickers.get(symbol)

            if not ticker:
                continue

            if not is_eligible_spot_market(
                market,
                ticker,
                quote_currency=quote_currency,
                minimum_quote_volume=minimum_quote_volume,
                maximum_spread_percent=maximum_spread_percent,
            ):
                continue

            bid = ticker["bid"]
            ask = ticker["ask"]
            midpoint = (bid + ask) / 2

            results.append(
                {
                    "exchange": exchange_id,
                    "symbol": symbol,
                    "last": ticker.get("last"),
                    "quote_volume_usdt": ticker.get("quoteVolume"),
                    "bid": bid,
                    "ask": ask,
                    "spread_percent": ((ask - bid) / midpoint) * 100,
                }
            )

        return sorted(
            results,
            key=lambda item: item["quote_volume_usdt"],
            reverse=True,
        )

    finally:
        exchange.close()
